import gradio as gr
from pathlib import Path
from loguru import logger
from fastapi import UploadFile
import asyncio

import config
from backend.qa_chain import get_qa_system
from ingest.extract_text import extract_text
from process.chunk_text import chunk_text
from process.embed_chunks import embed_chunks
from index.vector_store_text import build_index, save_vector_store
from services.watch_folder import get_watch_service


class DocumentAssistantUI:
    """Gradio interface for the Document Assistant."""

    def __init__(self):
        self.qa_system = get_qa_system()
        self.watch_service = get_watch_service()

    def answer_question(self, question: str) -> str:
        """Answer a question using the QA system."""
        if not question.strip():
            return "⚠️ Please enter a question."

        try:
            return self.qa_system.run(question)
        except Exception as e:
            logger.error(f"Error in answer_question: {e}")
            return f"❌ Error processing question: {str(e)}"

    def upload_pdf(self, file) -> str:
        """Handle PDF upload and processing."""
        if file is None:
            return "⚠️ Please select a PDF file to upload."

        try:
            # Save uploaded file
            file_path = config.DOCS_DIR / file.name

            # Copy file content
            import shutil

            shutil.copy2(file.name, file_path)

            # Process the document
            status = self.process_document(str(file_path))
            return status

        except Exception as e:
            error_msg = f"❌ Error uploading file: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def process_document(self, file_path: str) -> str:
        """Process a document through the full pipeline."""
        try:
            logger.info(f"Processing document: {file_path}")

            # Extract text
            logger.info("Extracting text...")
            pages = extract_text(file_path)

            if not pages:
                return "❌ No text could be extracted from the document."

            # Chunk text
            logger.info("Chunking text...")
            all_chunks = []
            all_metadata = []

            for page in pages:
                chunks = chunk_text(page["text"])
                for i, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    all_metadata.append(
                        {"file": page["file"], "page": page["page"], "chunk_id": i}
                    )

            # Generate embeddings
            logger.info("Generating embeddings...")
            embeddings = embed_chunks(all_chunks)

            # Update vector store
            logger.info("Updating vector store...")
            success = save_vector_store(embeddings, all_chunks, all_metadata)

            if success:
                # Reload QA system
                self.qa_system._load_vector_store()
                return f"✅ Document processed successfully! Extracted {len(all_chunks)} chunks from {len(pages)} pages."
            else:
                return "❌ Failed to update vector store."

        except Exception as e:
            error_msg = f"❌ Error processing document: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def get_system_status(self) -> str:
        """Get current system status."""
        try:
            stats = self.qa_system.get_stats()
            watch_status = self.watch_service.get_status()

            status_text = f"**System Status:** {stats['status']}\n"
            status_text += f"**Documents:** {stats.get('documents', 'Unknown')}\n"
            status_text += f"**Model:** {stats.get('model', 'Unknown')}\n\n"

            status_text += f"**Watch Folder:** {'🟢 Active' if watch_status['active'] else '🔴 Inactive'}\n"
            status_text += (
                f"**Watch Dir:** {Path(watch_status['watch_directory']).name}"
            )

            return status_text
        except Exception as e:
            return f"Error getting status: {str(e)}"

    def toggle_watch_folder(self) -> str:
        """Toggle the watch folder service on/off."""
        try:
            if self.watch_service.is_active():
                success = self.watch_service.stop()
                return (
                    "✅ Watch folder stopped"
                    if success
                    else "❌ Failed to stop watch folder"
                )
            else:
                success = self.watch_service.start()
                return (
                    "✅ Watch folder started"
                    if success
                    else "❌ Failed to start watch folder"
                )
        except Exception as e:
            return f"❌ Error toggling watch folder: {str(e)}"

    def process_existing_in_watch_folder(self) -> str:
        """Process existing files in the watch folder."""
        try:
            results = self.watch_service.process_existing_files()
            return f"✅ Processed {results['processed']} files, {results['failed']} failed, {results['skipped']} skipped"
        except Exception as e:
            return f"❌ Error processing existing files: {str(e)}"

    def get_watch_folder_path(self) -> str:
        """Get the watch folder path for display."""
        return str(config.WATCH_DIR)

    def create_interface(self):
        """Create and return the Gradio interface."""
        with gr.Blocks(
            title="AI Document Assistant", theme=gr.themes.Soft()
        ) as interface:
            gr.Markdown("# 📚 AI Document Assistant")
            gr.Markdown(
                "Upload PDF documents and ask questions about their content using drag-and-drop or the watch folder."
            )

            with gr.Tab("💬 Ask Questions"):
                with gr.Row():
                    with gr.Column(scale=3):
                        question_input = gr.Textbox(
                            label="Your Question",
                            placeholder="What would you like to know about your documents?",
                            lines=3,
                        )
                        submit_btn = gr.Button(
                            "🔍 Ask Question", variant="primary", size="lg"
                        )

                    with gr.Column(scale=1):
                        status_display = gr.Textbox(
                            label="System Status",
                            value=self.get_system_status(),
                            interactive=False,
                            lines=6,
                        )
                        refresh_status_btn = gr.Button("🔄 Refresh Status", size="sm")

                answer_output = gr.Textbox(
                    label="Answer", lines=12, interactive=False, show_copy_button=True
                )

            with gr.Tab("📤 Upload Documents"):
                gr.Markdown("### Drag and Drop PDF Upload")
                gr.Markdown(
                    "Drag your PDF files into the area below, or click to browse."
                )

                upload_input = gr.File(
                    label="📎 Drop PDF files here or click to browse",
                    file_types=[".pdf"],
                    file_count="multiple",
                    height=200,
                )

                with gr.Row():
                    upload_btn = gr.Button(
                        "🚀 Process Documents", variant="primary", size="lg"
                    )
                    clear_btn = gr.Button("🗑️ Clear", variant="secondary")

                upload_output = gr.Textbox(
                    label="Processing Status",
                    lines=5,
                    interactive=False,
                    show_copy_button=True,
                )

            with gr.Tab("📁 Watch Folder"):
                gr.Markdown("### Automatic Document Processing")
                gr.Markdown(f"**Watch Folder:** `{self.get_watch_folder_path()}`")
                gr.Markdown(
                    "Files placed in this folder will be automatically processed."
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        watch_status_display = gr.Textbox(
                            label="Watch Folder Status",
                            value=self.get_system_status(),
                            interactive=False,
                            lines=3,
                        )

                    with gr.Column(scale=1):
                        with gr.Row():
                            toggle_watch_btn = gr.Button(
                                "🔄 Toggle Watch Folder", variant="primary"
                            )
                            process_existing_btn = gr.Button(
                                "📂 Process Existing Files", variant="secondary"
                            )

                        open_folder_btn = gr.Button(
                            "📁 Open Watch Folder", variant="secondary"
                        )

                watch_output = gr.Textbox(
                    label="Watch Folder Messages", lines=4, interactive=False
                )

            with gr.Tab("ℹ️ Help"):
                gr.Markdown(
                    """
                ### How to Use the AI Document Assistant
                
                #### 1. Upload Documents
                - **Drag & Drop**: Drag PDF files directly into the upload area
                - **Browse**: Click the upload area to select files from your computer
                - **Watch Folder**: Place files in the watch folder for automatic processing
                
                #### 2. Ask Questions
                - Type your question in natural language
                - The AI will search through your uploaded documents
                - Answers include source citations showing which documents and pages were used
                
                #### 3. Watch Folder
                - Automatically monitors a designated folder for new PDF files
                - New files are processed immediately when detected
                - Processed files can be moved to a "processed" folder
                
                #### 4. Tips for Best Results
                - Use clear, specific questions
                - Upload documents with good text quality (not scanned images)
                - Check the system status to see how many documents are loaded
                
                #### 5. Watch Folder Location
                The watch folder is located at: `{}`
                
                You can:
                - Copy files directly into this folder
                - Set up automated workflows to place files here
                - Use cloud sync services to automatically add documents
                """.format(
                        self.get_watch_folder_path()
                    )
                )

            # Event handlers
            submit_btn.click(
                fn=self.answer_question,
                inputs=[question_input],
                outputs=[answer_output],
            )

            upload_btn.click(
                fn=self.upload_pdf, inputs=[upload_input], outputs=[upload_output]
            )

            clear_btn.click(
                fn=lambda: (None, ""), outputs=[upload_input, upload_output]
            )

            refresh_status_btn.click(
                fn=self.get_system_status, outputs=[status_display]
            )

            toggle_watch_btn.click(fn=self.toggle_watch_folder, outputs=[watch_output])

            process_existing_btn.click(
                fn=self.process_existing_in_watch_folder, outputs=[watch_output]
            )

            # Update watch status when toggling
            toggle_watch_btn.click(
                fn=self.get_system_status, outputs=[watch_status_display]
            )

            # Open watch folder (platform specific)
            def open_watch_folder():
                import subprocess
                import platform

                folder_path = self.get_watch_folder_path()
                try:
                    if platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", folder_path])
                    elif platform.system() == "Windows":
                        subprocess.run(["explorer", folder_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", folder_path])
                    return "📁 Watch folder opened in file manager"
                except Exception as e:
                    return f"❌ Could not open folder: {str(e)}"

            open_folder_btn.click(fn=open_watch_folder, outputs=[watch_output])

        return interface


def launch_ui(host: str = None, port: int = None, share: bool = False):
    """Launch the Gradio interface."""
    host = host or config.UI_HOST
    port = port or config.UI_PORT

    ui = DocumentAssistantUI()
    interface = ui.create_interface()

    logger.info(f"Starting Gradio interface on {host}:{port}")

    interface.launch(server_name=host, server_port=port, share=share, show_error=True)


if __name__ == "__main__":
    launch_ui()
