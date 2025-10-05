#!/usr/bin/env python3
"""
Quick start example for the AI Document Assistant.

This script demonstrates how to:
1. Set up the system
2. Process a document
3. Ask questions
4. Use the watch folder
"""

import sys
import time
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

import config
from setup import main as setup_main
from backend.qa_chain import get_qa_system
from services.watch_folder import get_watch_service


def main():
    """Run the quick start example."""
    print("🚀 AI Document Assistant - Quick Start Example")
    print("=" * 60)

    # Step 1: Setup
    print("\\n1️⃣ Setting up the system...")
    success = setup_main()
    if not success:
        print("❌ Setup failed")
        return

    # Step 2: Initialize systems
    print("\\n2️⃣ Initializing QA system...")
    try:
        qa_system = get_qa_system()
        watch_service = get_watch_service()
        print("✅ Systems initialized")
    except Exception as e:
        print(f"❌ Failed to initialize systems: {e}")
        return

    # Step 3: Start watch folder
    print("\\n3️⃣ Starting watch folder service...")
    try:
        success = watch_service.start()
        if success:
            status = watch_service.get_status()
            print(f"✅ Watch folder active: {status['watch_directory']}")
            print(f"📋 Monitoring patterns: {', '.join(status['patterns'])}")
        else:
            print("⚠️ Watch folder failed to start (continuing anyway)")
    except Exception as e:
        print(f"⚠️ Watch folder error: {e}")

    # Step 4: Show current status
    print("\\n4️⃣ System Status:")
    try:
        stats = qa_system.get_stats()
        print(f"📊 Status: {stats['status']}")
        print(f"📚 Documents: {stats.get('documents', 0)}")
        print(f"🤖 LLM: {stats.get('llm', 'Unknown')}")
        print(f"🧠 Embeddings: {stats.get('model', 'Unknown')}")
    except Exception as e:
        print(f"❌ Error getting status: {e}")

    # Step 5: Show next steps
    print("\\n5️⃣ Next Steps:")
    print(f"📁 Watch folder: {config.WATCH_DIR}")
    print(f"📂 Processed files: {config.PROCESSED_DIR}")
    print()
    print("To use the system:")
    print("• Drop PDF files in the watch folder for automatic processing")
    print("• Use the web interface: python main.py ui")
    print("• Use the API server: python main.py api")
    print("• Ask questions via CLI: python main.py ask 'your question here'")
    print("• Interactive mode: python main.py interactive")

    # Step 6: Example with watch folder
    print("\\n6️⃣ Watch Folder Example:")
    print(f"Try copying a PDF file to: {config.WATCH_DIR}")
    print("The system will automatically:")
    print("• Detect the new file")
    print("• Extract text and create embeddings")
    print("• Add it to the searchable knowledge base")
    print("• Move the file to the processed folder")

    print("\\n✨ Quick start complete! The system is ready to use.")
    print("=" * 60)


if __name__ == "__main__":
    main()
