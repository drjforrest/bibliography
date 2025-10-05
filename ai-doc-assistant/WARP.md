# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is an AI-powered document assistant that processes PDF documents to enable question-answering through multiple interfaces. The system uses RAG (Retrieval Augmented Generation) architecture with vector embeddings for document retrieval and LLM-powered responses.

## Architecture

### Core Components

- **Document Ingestion Pipeline**: `ingest/` - Extracts text and images from PDFs using PyMuPDF
- **Text Processing**: `process/` - Chunks text and creates embeddings using sentence-transformers  
- **Vector Storage**: `index/` - FAISS-based vector store for text and CLIP-based embeddings for images
- **QA Engine**: `backend/qa_chain.py` - LangChain RetrievalQA chain with Ollama LLM integration
- **User Interfaces**: 
  - Gradio web interface (`interface/ui.py`)
  - FastAPI REST API (`backend/server.py`)
- **Memory System**: `long_term_memory.py` - SQLite-based interaction logging

### Data Flow

1. PDF upload → text/image extraction (`ingest/`)
2. Text chunking → embedding generation (`process/`)
3. Vector index creation/update (`index/`)
4. Query → vector similarity search → LLM response generation (`backend/`)
5. Response delivery through Gradio UI or REST API

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies  
pip install -r requirements.txt
```

### Running the Application
```bash
# Setup (first time only)
python setup.py

# Start Gradio interface
python main.py ui

# Start FastAPI server
python main.py api

# Start watch folder service
python main.py watch start

# Quick start with defaults (recommended)
curl -X POST http://localhost:8000/watch-folder/quick-start

# Process a single document
python main.py process path/to/document.pdf

# Interactive question-answering
python main.py interactive
```

### Working with Components
```bash
# Test text extraction
python -c "from ingest.extract_text import extract_text; print(extract_text('path/to/doc.pdf'))"

# Test embedding generation
python -c "from process.embed_chunks import embed_chunks; print(embed_chunks(['sample text']))"

# Test vector store operations
python -c "from index.vector_store_text import build_index; import numpy as np; print(build_index(np.random.random((10, 384))))"
```

### Watch Folder System
- **Automatic Processing**: Monitors `data/watch/` directory for new PDF files using `watchdog` library
- **File Stability**: Waits for files to stabilize before processing to handle large uploads
- **Processed Files**: Optionally moves completed files to `data/processed/` directory
- **Multi-threading**: Processes files asynchronously to avoid blocking the file system watcher
- **API Integration**: Full REST API for starting/stopping service and processing existing files
- **CLI Management**: Complete command-line controls via `python main.py watch` subcommands

## Key Implementation Details

### LLM Integration
- Uses Ollama with Mistral model for question answering
- LangChain RetrievalQA chain orchestrates retrieval and generation
- Response formatting includes source citations with page references

### Vector Store Strategy
- **Text**: sentence-transformers 'all-MiniLM-L6-v2' model with FAISS IndexFlatL2
- **Images**: OpenAI CLIP ViT-Base-Patch32 for multimodal search capabilities
- Metadata preservation for document/page source attribution

### Memory and Logging
- SQLite database (`history.db`) stores question-answer pairs
- Simple schema: `log` table with `q` (question) and `a` (answer) columns

### Interface Architecture
- **Gradio**: Enhanced web interface with drag-and-drop upload, watch folder controls, and multi-tab layout
- **FastAPI**: Comprehensive REST API with document upload, QA endpoints, and watch folder management
- **Watch Folder**: Automated document processing service that monitors a directory for new PDFs
- **CLI**: Complete command-line interface for all operations including watch folder management

## File Structure Patterns

- Each major component is in its own directory with focused responsibilities
- Import dependencies suggest inter-component communication (e.g., `qa` object used in interfaces)
- Missing imports in some files indicate incomplete integration between components

## Development Notes

### Missing Dependencies
Several files have unresolved imports that need attention:
- `interface/ui.py`: Missing `qa` import and `app` reference
- `backend/qa_chain.py`: Missing `model` and `embeddings` definitions
- Various files need proper import statements for cross-component usage

### Extension Points
- Document type support beyond PDFs
- Advanced chunking strategies for better context preservation
- Multi-modal query capabilities leveraging image embeddings
- Enhanced memory system with conversation context

### Testing Strategy
No existing test files found. Consider implementing:
- Unit tests for each extraction/processing component
- Integration tests for the full pipeline
- API endpoint testing for FastAPI routes
- UI component testing for Gradio interface