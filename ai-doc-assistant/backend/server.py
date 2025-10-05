from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from pathlib import Path
from loguru import logger
import shutil

import config
from backend.qa_chain import get_qa_system
from ingest.extract_text import extract_text
from process.chunk_text import chunk_text
from process.embed_chunks import embed_chunks
from index.vector_store_text import save_vector_store
from services.watch_folder import get_watch_service


class Query(BaseModel):
    question: str


class UploadResponse(BaseModel):
    message: str
    filename: str
    chunks_processed: int = 0
    pages_processed: int = 0


class AnswerResponse(BaseModel):
    answer: str
    question: str
    sources: list = []


class StatusResponse(BaseModel):
    status: str
    documents: int
    model: str
    llm: str


class WatchFolderStatusResponse(BaseModel):
    active: bool
    watch_directory: str
    processed_directory: str
    patterns: list
    recursive: bool
    auto_move_processed: bool


class WatchFolderActionResponse(BaseModel):
    success: bool
    message: str
    status: dict = {}


class ProcessExistingResponse(BaseModel):
    success: bool
    message: str
    processed: int
    failed: int
    skipped: int
    files: list


# Initialize FastAPI app
app = FastAPI(
    title="AI Document Assistant API",
    description="REST API for the AI Document Assistant RAG system",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize QA system and watch service
qa_system = get_qa_system()
watch_service = get_watch_service()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Document Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "/ask": "POST - Ask a question about uploaded documents",
            "/upload": "POST - Upload and process a PDF document",
            "/status": "GET - Get system status and statistics",
            "/watch-folder/status": "GET - Get watch folder status",
            "/watch-folder/start": "POST - Start watch folder service",
            "/watch-folder/stop": "POST - Stop watch folder service",
            "/watch-folder/process-existing": "POST - Process existing files in watch folder",
            "/watch-folder/quick-start": "POST - Quick start watch folder with existing files",
            "/docs": "GET - Interactive API documentation",
        },
    }


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(query: Query) -> AnswerResponse:
    """Ask a question about the uploaded documents."""
    try:
        if not query.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        logger.info(f"Received question: {query.question[:100]}...")

        # Get answer from QA system
        response = qa_system.run(query.question)

        return AnswerResponse(
            answer=response,
            question=query.question,
            sources=[],  # Sources are embedded in the response text
        )

    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing question: {str(e)}"
        )


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """Upload and process a PDF document."""
    try:
        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        logger.info(f"Uploading file: {file.filename}")

        # Save uploaded file
        file_path = config.DOCS_DIR / file.filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File saved to: {file_path}")

        # Process the document
        chunks_processed, pages_processed = await process_document(str(file_path))

        return UploadResponse(
            message="Document processed successfully",
            filename=file.filename,
            chunks_processed=chunks_processed,
            pages_processed=pages_processed,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error uploading document: {str(e)}"
        )


async def process_document(file_path: str) -> tuple[int, int]:
    """Process a document through the full pipeline."""
    try:
        logger.info(f"Processing document: {file_path}")

        # Extract text
        logger.info("Extracting text...")
        pages = extract_text(file_path)

        if not pages:
            raise HTTPException(
                status_code=400, detail="No text could be extracted from the document"
            )

        # Chunk text
        logger.info("Chunking text...")
        all_chunks = []
        all_metadata = []

        for page in pages:
            chunks = chunk_text(page["text"], config.CHUNK_SIZE, config.CHUNK_OVERLAP)
            for i, chunk in enumerate(chunks):
                if chunk.strip():  # Only add non-empty chunks
                    all_chunks.append(chunk)
                    all_metadata.append(
                        {"file": page["file"], "page": page["page"], "chunk_id": i}
                    )

        if not all_chunks:
            raise HTTPException(
                status_code=400,
                detail="No valid text chunks could be created from the document",
            )

        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = embed_chunks(all_chunks)

        # Update vector store
        logger.info("Updating vector store...")
        success = save_vector_store(embeddings, all_chunks, all_metadata)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update vector store")

        # Reload QA system
        qa_system._load_vector_store()

        logger.info(
            f"Document processed successfully: {len(all_chunks)} chunks from {len(pages)} pages"
        )
        return len(all_chunks), len(pages)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing document: {str(e)}"
        )


@app.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Get current system status and statistics."""
    try:
        stats = qa_system.get_stats()
        return StatusResponse(
            status=stats.get("status", "Unknown"),
            documents=stats.get("documents", 0),
            model=stats.get("model", "Unknown"),
            llm=stats.get("llm", "Unknown"),
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "message": "API is running"}


# Watch Folder Endpoints


@app.get("/watch-folder/status", response_model=WatchFolderStatusResponse)
async def get_watch_folder_status() -> WatchFolderStatusResponse:
    """Get the current status of the watch folder service."""
    try:
        status = watch_service.get_status()
        return WatchFolderStatusResponse(**status)
    except Exception as e:
        logger.error(f"Error getting watch folder status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting watch folder status: {str(e)}"
        )


@app.post("/watch-folder/start", response_model=WatchFolderActionResponse)
async def start_watch_folder() -> WatchFolderActionResponse:
    """Start the watch folder service."""
    try:
        success = watch_service.start()
        status = watch_service.get_status()

        return WatchFolderActionResponse(
            success=success,
            message=(
                "Watch folder service started successfully"
                if success
                else "Failed to start watch folder service"
            ),
            status=status,
        )
    except Exception as e:
        logger.error(f"Error starting watch folder service: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error starting watch folder service: {str(e)}"
        )


@app.post("/watch-folder/stop", response_model=WatchFolderActionResponse)
async def stop_watch_folder() -> WatchFolderActionResponse:
    """Stop the watch folder service."""
    try:
        success = watch_service.stop()
        status = watch_service.get_status()

        return WatchFolderActionResponse(
            success=success,
            message=(
                "Watch folder service stopped successfully"
                if success
                else "Failed to stop watch folder service"
            ),
            status=status,
        )
    except Exception as e:
        logger.error(f"Error stopping watch folder service: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error stopping watch folder service: {str(e)}"
        )


@app.post("/watch-folder/process-existing", response_model=ProcessExistingResponse)
async def process_existing_files() -> ProcessExistingResponse:
    """Process any existing PDF files in the watch directory."""
    try:
        results = watch_service.process_existing_files()

        return ProcessExistingResponse(
            success=results["failed"] == 0,
            message=f"Processed {results['processed']} files, {results['failed']} failed",
            processed=results["processed"],
            failed=results["failed"],
            skipped=results["skipped"],
            files=results["files"],
        )
    except Exception as e:
        logger.error(f"Error processing existing files: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing existing files: {str(e)}"
        )


@app.post("/watch-folder/quick-start", response_model=dict)
async def quick_start_watch_folder():
    """Quick start: Start watch folder service and process existing files."""
    try:
        # Start the service
        start_success = watch_service.start()

        results = {"start": {"success": start_success}}

        if start_success:
            # Process existing files
            existing_results = watch_service.process_existing_files()
            results["existing_files"] = existing_results
            results["message"] = (
                f"Watch folder started. Processed {existing_results['processed']} existing files."
            )
        else:
            results["message"] = "Failed to start watch folder service"

        results["status"] = watch_service.get_status()

        return results

    except Exception as e:
        logger.error(f"Error in quick start: {e}")
        raise HTTPException(status_code=500, detail=f"Error in quick start: {str(e)}")


def start_server(host: str = None, port: int = None):
    """Start the FastAPI server."""
    import uvicorn

    host = host or config.API_HOST
    port = port or config.API_PORT

    logger.info(f"Starting FastAPI server on {host}:{port}")

    uvicorn.run(
        "backend.server:app", host=host, port=port, reload=True, log_level="info"
    )


if __name__ == "__main__":
    start_server()
