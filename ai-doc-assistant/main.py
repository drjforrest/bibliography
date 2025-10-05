#!/usr/bin/env python3
"""
Main entry point for the AI Document Assistant.

This script provides a command-line interface to run different components
of the application.
"""

import click
import sys
from pathlib import Path
from loguru import logger

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

import config
from setup import main as setup_main


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose):
    """AI Document Assistant - Command Line Interface"""
    if verbose:
        config.LOG_LEVEL = "DEBUG"

    # Initialize configuration
    config.init_config()


@cli.command()
@click.option("--host", default=None, help="Host to bind to")
@click.option("--port", default=None, type=int, help="Port to bind to")
@click.option("--share", is_flag=True, help="Create a public shareable link")
def ui(host, port, share):
    """Launch the Gradio web interface"""
    try:
        from interface.ui import launch_ui

        launch_ui(host=host, port=port, share=share)
    except Exception as e:
        logger.error(f"Failed to start UI: {e}")
        sys.exit(1)


@cli.command()
@click.option("--host", default=None, help="Host to bind to")
@click.option("--port", default=None, type=int, help="Port to bind to")
def api(host, port):
    """Launch the FastAPI server"""
    try:
        from backend.server import start_server

        start_server(host=host, port=port)
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        sys.exit(1)


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
def process(pdf_path):
    """Process a single PDF document"""
    try:
        from ingest.extract_text import extract_text
        from process.chunk_text import chunk_text
        from process.embed_chunks import embed_chunks
        from index.vector_store_text import save_vector_store

        logger.info(f"Processing document: {pdf_path}")

        # Extract text
        logger.info("Extracting text...")
        pages = extract_text(pdf_path)

        if not pages:
            logger.error("No text could be extracted from the document")
            sys.exit(1)

        # Chunk text
        logger.info("Chunking text...")
        all_chunks = []
        all_metadata = []

        for page in pages:
            chunks = chunk_text(page["text"], config.CHUNK_SIZE, config.CHUNK_OVERLAP)
            for i, chunk in enumerate(chunks):
                if chunk.strip():
                    all_chunks.append(chunk)
                    all_metadata.append(
                        {"file": page["file"], "page": page["page"], "chunk_id": i}
                    )

        if not all_chunks:
            logger.error("No valid text chunks could be created")
            sys.exit(1)

        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = embed_chunks(all_chunks)

        # Save vector store
        logger.info("Saving to vector store...")
        success = save_vector_store(embeddings, all_chunks, all_metadata)

        if success:
            logger.info(
                f"Successfully processed {len(all_chunks)} chunks from {len(pages)} pages"
            )
        else:
            logger.error("Failed to save vector store")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        sys.exit(1)


@cli.command()
@click.argument("question")
def ask(question):
    """Ask a question about processed documents"""
    try:
        from backend.qa_chain import get_qa_system

        qa_system = get_qa_system()
        answer = qa_system.run(question)

        print("\\n" + "=" * 60)
        print(f"Question: {question}")
        print("=" * 60)
        print(answer)
        print("=" * 60)

    except Exception as e:
        logger.error(f"Error asking question: {e}")
        sys.exit(1)


@cli.command()
def setup():
    """Run the initial setup process"""
    try:
        success = setup_main()
        if not success:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


@cli.command()
def status():
    """Show system status"""
    try:
        from backend.qa_chain import get_qa_system

        qa_system = get_qa_system()
        stats = qa_system.get_stats()

        print("\\n" + "=" * 40)
        print("AI Document Assistant Status")
        print("=" * 40)
        print(f"Status: {stats.get('status', 'Unknown')}")
        print(f"Documents: {stats.get('documents', 'Unknown')}")
        print(f"Embedding Model: {stats.get('model', 'Unknown')}")
        print(f"LLM: {stats.get('llm', 'Unknown')}")
        print(f"Database: {config.DATABASE_PATH}")
        print(f"Vector Store: {config.INDEX_DIR}")
        print("=" * 40)

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        sys.exit(1)


@cli.command()
def interactive():
    """Start interactive question-answering session"""
    try:
        from backend.qa_chain import get_qa_system

        qa_system = get_qa_system()

        print("\\n" + "=" * 60)
        print("AI Document Assistant - Interactive Mode")
        print("Type 'quit' or 'exit' to stop")
        print("=" * 60)

        while True:
            try:
                question = input("\\n❓ Your question: ").strip()

                if question.lower() in ["quit", "exit", "q"]:
                    print("Goodbye! 👋")
                    break

                if not question:
                    continue

                print("\\n🤔 Thinking...")
                answer = qa_system.run(question)

                print("\\n💡 Answer:")
                print("-" * 40)
                print(answer)
                print("-" * 40)

            except KeyboardInterrupt:
                print("\\n\\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    except Exception as e:
        logger.error(f"Error in interactive mode: {e}")
        sys.exit(1)


@cli.group()
def watch():
    """Watch folder management commands"""
    pass


@watch.command()
def start():
    """Start the watch folder service"""
    try:
        from services.watch_folder import get_watch_service

        service = get_watch_service()
        success = service.start()

        if success:
            status = service.get_status()
            print("✅ Watch folder service started successfully!")
            print(f"📁 Monitoring: {status['watch_directory']}")
            print(f"📋 Patterns: {', '.join(status['patterns'])}")
            print(f"🔄 Recursive: {status['recursive']}")
        else:
            print("❌ Failed to start watch folder service")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error starting watch folder: {e}")
        sys.exit(1)


@watch.command()
def stop():
    """Stop the watch folder service"""
    try:
        from services.watch_folder import get_watch_service

        service = get_watch_service()
        success = service.stop()

        if success:
            print("✅ Watch folder service stopped")
        else:
            print("❌ Failed to stop watch folder service")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error stopping watch folder: {e}")
        sys.exit(1)


@watch.command(name="status")
def watch_status():
    """Show watch folder status"""
    try:
        from services.watch_folder import get_watch_service

        service = get_watch_service()
        status = service.get_status()

        print("\n" + "=" * 40)
        print("Watch Folder Status")
        print("=" * 40)
        print(f"Status: {'🟢 Active' if status['active'] else '🔴 Inactive'}")
        print(f"Watch Directory: {status['watch_directory']}")
        print(f"Processed Directory: {status['processed_directory']}")
        print(f"File Patterns: {', '.join(status['patterns'])}")
        print(f"Recursive: {status['recursive']}")
        print(f"Auto-move Processed: {status['auto_move_processed']}")
        print("=" * 40)

    except Exception as e:
        logger.error(f"Error getting watch status: {e}")
        sys.exit(1)


@watch.command(name="process-existing")
def process_existing():
    """Process existing files in the watch folder"""
    try:
        from services.watch_folder import get_watch_service

        service = get_watch_service()
        print("🔄 Processing existing files in watch folder...")

        results = service.process_existing_files()

        print("\n📊 Processing Results:")
        print(f"✅ Processed: {results['processed']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"⏭️ Skipped: {results['skipped']}")

        if results["files"]:
            print("\n📄 File Details:")
            for file_info in results["files"]:
                status_icon = "✅" if file_info["status"] == "success" else "❌"
                print(
                    f"  {status_icon} {Path(file_info['file']).name} - {file_info['status']}"
                )

    except Exception as e:
        logger.error(f"Error processing existing files: {e}")
        sys.exit(1)


@watch.command(name="open")
def open_folder():
    """Open the watch folder in file manager"""
    try:
        import subprocess
        import platform

        folder_path = str(config.WATCH_DIR)

        if platform.system() == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        elif platform.system() == "Windows":
            subprocess.run(["explorer", folder_path])
        else:  # Linux
            subprocess.run(["xdg-open", folder_path])

        print(f"📁 Opened watch folder: {folder_path}")

    except Exception as e:
        logger.error(f"Error opening folder: {e}")
        print(f"❌ Could not open folder: {e}")
        print(f"📁 Watch folder location: {config.WATCH_DIR}")


if __name__ == "__main__":
    cli()
