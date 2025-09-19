from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import tempfile
import os
import io

from app.db import get_async_session, User
from app.services.paper_manager import PaperManagerService
from app.services.citation_formatter import CitationFormatter
from app.users import current_active_user
from app.schemas.papers import (
    PaperResponse, PaperListResponse, PaperSearchRequest,
    PaperUploadResponse, CitationRequest, CitationResponse,
    StorageStatsResponse, WatcherStatusResponse
)

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/upload", response_model=PaperUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    search_space_id: int = Form(...),
    move_file: bool = Form(True),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Upload and process a PDF file.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        paper_manager = PaperManagerService(session)
        result = await paper_manager.process_pdf_file(
            file_path=temp_path,
            user_id=str(user.id),
            search_space_id=search_space_id,
            move_file=move_file
        )
        
        return PaperUploadResponse(**result)
        
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except OSError:
            pass


@router.get("/", response_model=PaperListResponse)
async def get_papers(
    search_space_id: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get paginated list of papers for the current user.
    """
    paper_manager = PaperManagerService(session)
    papers = await paper_manager.get_papers_by_user(
        user_id=str(user.id),
        search_space_id=search_space_id,
        limit=limit,
        offset=offset
    )
    
    return PaperListResponse(
        papers=[PaperResponse.from_orm(paper) for paper in papers],
        total=len(papers),
        limit=limit,
        offset=offset
    )


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get a specific paper by ID.
    """
    paper_manager = PaperManagerService(session)
    paper = await paper_manager.get_paper_by_id(paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return PaperResponse.from_orm(paper)


@router.post("/search", response_model=PaperListResponse)
async def search_papers(
    search_request: PaperSearchRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Search papers by query string.
    """
    paper_manager = PaperManagerService(session)
    papers = await paper_manager.search_papers(
        query=search_request.query,
        search_space_id=search_request.search_space_id,
        limit=search_request.limit
    )
    
    return PaperListResponse(
        papers=[PaperResponse.from_orm(paper) for paper in papers],
        total=len(papers),
        limit=search_request.limit,
        offset=0
    )


@router.get("/{paper_id}/download")
async def download_paper(
    paper_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Download the PDF file for a paper.
    """
    paper_manager = PaperManagerService(session)
    paper = await paper_manager.get_paper_by_id(paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Get full file path
    full_path = paper_manager.file_storage.get_full_path(paper.file_path)
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    
    # Generate a nice filename
    filename = f"{paper.title[:50]}.pdf" if paper.title else f"paper_{paper_id}.pdf"
    # Clean filename for download
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).strip()
    
    return FileResponse(
        path=str(full_path),
        filename=filename,
        media_type='application/pdf'
    )


@router.post("/{paper_id}/citation", response_model=CitationResponse)
async def get_citation(
    paper_id: int,
    citation_request: CitationRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get formatted citation for a paper.
    """
    paper_manager = PaperManagerService(session)
    paper = await paper_manager.get_paper_by_id(paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    try:
        if citation_request.style.lower() == "bibtex":
            citation = CitationFormatter.format_bibtex(paper)
        else:
            citation = CitationFormatter.format_citation(paper, citation_request.style)
        
        return CitationResponse(
            citation=citation,
            style=citation_request.style,
            paper_id=paper_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/citation-styles/", response_model=List[dict])
async def get_citation_styles():
    """
    Get available citation styles.
    """
    return CitationFormatter.get_available_styles()


@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Delete a paper and its associated file.
    """
    paper_manager = PaperManagerService(session)
    
    # Verify paper exists and user has access (through search space ownership)
    paper = await paper_manager.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    success = await paper_manager.delete_paper(paper_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete paper")
    
    return {"message": "Paper deleted successfully", "paper_id": paper_id}


@router.get("/stats/storage", response_model=StorageStatsResponse)
async def get_storage_stats(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get storage statistics.
    """
    paper_manager = PaperManagerService(session)
    stats = await paper_manager.get_storage_stats()
    return StorageStatsResponse(**stats)


@router.post("/watcher/start")
async def start_watcher(
    search_space_id: int = Form(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Start the folder watcher for automatic PDF processing.
    """
    paper_manager = PaperManagerService(session)
    paper_manager.start_folder_watcher(
        user_id=str(user.id),
        search_space_id=search_space_id
    )
    
    return {"message": "Folder watcher started", "search_space_id": search_space_id}


@router.post("/watcher/stop")
async def stop_watcher(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Stop the folder watcher.
    """
    paper_manager = PaperManagerService(session)
    paper_manager.stop_folder_watcher()
    
    return {"message": "Folder watcher stopped"}


@router.get("/watcher/status", response_model=WatcherStatusResponse)
async def get_watcher_status(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get folder watcher status.
    """
    paper_manager = PaperManagerService(session)
    status = paper_manager.get_watcher_status()
    
    if not status:
        return WatcherStatusResponse(
            is_running=False,
            watched_folder="Not initialized",
            folder_exists=False,
            pdf_count=0
        )
    
    return WatcherStatusResponse(**status)