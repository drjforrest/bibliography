import io
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from app.db import ScientificPaper, User, get_async_session, get_async_session_context
from app.middleware.clerk_auth import require_clerk_auth
from app.schemas.papers import (
    CitationRequest,
    CitationResponse,
    PaperListResponse,
    PaperResponse,
    PaperSearchRequest,
    PaperUploadResponse,
    StorageStatsResponse,
    WatcherStatusResponse,
)
from app.services.citation_formatter import CitationFormatter
from app.services.paper_manager import PaperManagerService
from app.services.paper_report_service import PaperReportService
from app.services.thumbnail_generator import ThumbnailGenerator
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["papers"])

# In-memory set to track papers currently being enriched (prevents duplicate background tasks)
_enrichment_in_progress: set[int] = set()


# Report generation schemas
class PaperReportResponse(BaseModel):
    """Response schema for paper report generation."""

    report_type: str
    report_content: str
    paper_id: int


class PaperReportRequest(BaseModel):
    """Request schema for paper report generation."""

    report_type: str  # "quick-summary", "comprehensive", "critical-appraisal", "methodology", "research-gaps"


async def _enrich_paper_in_background(paper_id: int):
    """
    Background task to enrich a paper when triggered by a user event (event-based).

    This is triggered when a user views/requests a paper. Uses cloud-based LLMs
    since this runs in production when users access papers.
    Creates its own database session to avoid context issues.

    Includes deduplication to prevent multiple concurrent enrichment tasks for the same paper.
    """
    # Check if this paper is already being enriched
    if paper_id in _enrichment_in_progress:
        logger.debug(
            f"Paper {paper_id} enrichment already in progress, skipping duplicate task"
        )
        return

    # Mark this paper as being enriched
    _enrichment_in_progress.add(paper_id)

    try:
        async with get_async_session_context() as session:
            from app.services.embedding_service import EmbeddingService
            from app.services.llm_enrichment_service import LLMEnrichmentService
            from app.services.paper_manager import PaperManagerService

            # Create paper manager to check if enrichment is needed
            paper_manager = PaperManagerService(session)
            paper = await paper_manager.get_paper_by_id(paper_id)

            if not paper:
                logger.warning(f"Paper {paper_id} not found for background enrichment")
                return

            # Check if enrichment is needed
            if not paper_manager._needs_enrichment(paper):
                logger.debug(f"Paper {paper_id} already enriched, skipping")
                return

            logger.info(
                f"Starting event-based enrichment for paper {paper_id} (using cloud LLM)"
            )

            # Get the paper with document
            if not paper.document:
                logger.error(f"Paper {paper_id} has no document for enrichment")
                return

            # Step 1: Vectorization (embeddings and chunks)
            logger.info(f"Step 1/2: Generating embeddings for paper {paper_id}")
            embedding_service = EmbeddingService(session)
            try:
                # Embed the document itself
                doc_embedded = await embedding_service.embed_document(paper.document_id)
                if doc_embedded:
                    logger.info(f"Successfully embedded document {paper.document_id}")

                # Create and embed chunks
                chunks_embedded = await embedding_service.create_and_embed_chunks(
                    paper.document
                )
                if chunks_embedded:
                    logger.info(
                        f"Successfully created and embedded chunks for document {paper.document_id}"
                    )
            except Exception as e:
                logger.error(f"Vectorization failed for paper {paper_id}: {str(e)}")
                # Continue to LLM enrichment even if vectorization fails

            # Step 2: LLM enrichment with cloud LLM (event-based = user triggered, always uses cloud)
            logger.info(
                f"Step 2/2: Running LLM enrichment for paper {paper_id} (cloud LLM)"
            )
            try:
                # Use cloud LLM for event-based enrichment (user-triggered)
                cloud_llm_enrichment = LLMEnrichmentService(session, use_cloud_llm=True)
                enriched = await cloud_llm_enrichment.enrich_paper(paper_id)
                if enriched:
                    logger.info(
                        f"Successfully enriched paper {paper_id} with cloud LLM"
                    )
                else:
                    logger.warning(
                        f"Cloud LLM enrichment returned False for paper {paper_id}"
                    )
            except Exception as e:
                logger.error(
                    f"Cloud LLM enrichment failed for paper {paper_id}: {str(e)}"
                )

            logger.info(f"Completed event-based enrichment for paper {paper_id}")

    except Exception as e:
        logger.error(
            f"Error in background enrichment for paper {paper_id}: {str(e)}",
            exc_info=True,
        )
    finally:
        # Always remove from in-progress set when done (success or failure)
        _enrichment_in_progress.discard(paper_id)


async def _get_paper_file_path(
    paper_id: int, session: AsyncSession
) -> Tuple[ScientificPaper, Path]:
    """
    Helper function to retrieve a paper and resolve its file path.

    Args:
        paper_id: The ID of the paper to retrieve
        session: Database session

    Returns:
        Tuple of (paper, full_path) where full_path is a Path object

    Raises:
        HTTPException: If paper not found, has no file_path, path resolution fails,
                      or file doesn't exist on filesystem
    """
    paper_manager = PaperManagerService(session)
    paper = await paper_manager.get_paper_by_id(paper_id)

    if not paper:
        logger.error(f"Paper {paper_id} not found in database")
        raise HTTPException(status_code=404, detail="Paper not found")

    if not paper.file_path:
        logger.error(f"Paper {paper_id} has no file_path in database")
        raise HTTPException(status_code=404, detail="Paper has no associated PDF file")

    # Log storage root for debugging
    storage_root = paper_manager.file_storage.storage_root
    logger.info(
        f"Resolving path for paper {paper_id}: stored_path='{paper.file_path}', "
        f"storage_root='{storage_root}'"
    )

    # Get full file path
    try:
        full_path = paper_manager.file_storage.get_full_path(paper.file_path)
        logger.info(f"Resolved full path for paper {paper_id}: {full_path}")
    except Exception as e:
        logger.error(
            f"Error getting full path for paper {paper_id}: {e}, "
            f"stored_path: {paper.file_path}, storage_root: {storage_root}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error resolving file path: {str(e)}"
        )

    # If file doesn't exist, try fallback locations for legacy imports
    if not full_path.exists():
        # Check if this is a legacy devonthink_import path
        if paper.file_path.startswith("devonthink_import/"):
            # Try to find the file in the devonthink_import subdirectory
            dt_uuid = paper.file_path.replace("devonthink_import/", "")
            fallback_paths = [
                paper_manager.file_storage.storage_root
                / "devonthink_import"
                / f"{dt_uuid}.pdf",
                paper_manager.file_storage.storage_root / "devonthink_import" / dt_uuid,
                # Also check if PDF_STORAGE_ROOT points to a different location
                Path(paper_manager.file_storage.storage_root)
                / "devonthink_import"
                / f"{dt_uuid}.pdf",
            ]

            for fallback in fallback_paths:
                if fallback.exists() and fallback.is_file():
                    logger.info(
                        f"Found PDF for paper {paper_id} at fallback location: {fallback}"
                    )
                    full_path = fallback
                    break
            else:
                logger.error(
                    f"PDF file not found for paper {paper_id}: {full_path} (resolved from: {paper.file_path})"
                )
                logger.error(
                    f"Tried fallback paths: {[str(p) for p in fallback_paths]}"
                )
                logger.warning(
                    f"Paper {paper_id} has legacy devonthink_import/ path but file not found. "
                    f"This may need to be re-imported. DT UUID: {dt_uuid}"
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"PDF file not found. This paper may need to be re-imported (DT UUID: {dt_uuid}).",
                )
        else:
            logger.error(
                f"PDF file not found for paper {paper_id}: {full_path} (resolved from: {paper.file_path})"
            )
            raise HTTPException(status_code=404, detail="PDF file not found")

    return paper, full_path


@router.post("/upload", response_model=PaperUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    search_space_id: int = Form(...),
    literature_type: str = Form("PEER_REVIEWED"),
    move_file: bool = Form(True),
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Upload and process a PDF file.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Validate literature_type
    from app.db import LiteratureType

    try:
        lit_type = LiteratureType(literature_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid literature_type. Must be one of: {[t.value for t in LiteratureType]}",
        )

    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        paper_manager = PaperManagerService(session)
        result = await paper_manager.process_pdf_file(
            file_path=temp_path,
            user_id=str(user.id),
            search_space_id=search_space_id,
            literature_type=literature_type,
            move_file=move_file,
        )

        return PaperUploadResponse(**result)

    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except OSError:
            pass


@router.post("/search", response_model=PaperListResponse)
async def search_papers(
    search_request: PaperSearchRequest,
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Search papers by query string.
    """
    paper_manager = PaperManagerService(session)
    papers = await paper_manager.search_papers(
        query=search_request.query,
        search_space_id=search_request.search_space_id,
        limit=search_request.limit,
    )

    return PaperListResponse(
        papers=[PaperResponse.from_orm(paper) for paper in papers],
        total=len(papers),
        limit=search_request.limit,
        offset=0,
    )


@router.get("", response_model=PaperListResponse)
@router.get("/", response_model=PaperListResponse)
async def get_papers(
    search_space_id: Optional[int] = Query(None),
    literature_type: Optional[str] = Query(
        None,
        description="Filter by literature type: PEER_REVIEWED, GREY_LITERATURE, NEWS",
    ),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get paginated list of papers for the current user.
    Optionally filter by literature_type (room).
    """
    paper_manager = PaperManagerService(session)
    papers = await paper_manager.get_papers_by_user(
        user_id=str(user.id),
        search_space_id=search_space_id,
        literature_type=literature_type,
        limit=limit,
        offset=offset,
    )

    return PaperListResponse(
        papers=[PaperResponse.from_orm(paper) for paper in papers],
        total=len(papers),
        limit=limit,
        offset=offset,
    )


@router.get("/by-folder")
async def get_papers_by_folder(
    folder_path: str = Query(...),
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get papers in a specific DEVONthink folder path.
    """
    from app.db import ScientificPaper
    from sqlalchemy import select

    stmt = (
        select(ScientificPaper)
        .where(ScientificPaper.dt_source_path.like(f"{folder_path}%"))
        .limit(100)
    )

    result = await session.execute(stmt)
    papers = result.scalars().all()

    return {
        "papers": [PaperResponse.from_orm(paper) for paper in papers],
        "folder_path": folder_path,
        "total": len(papers),
    }


# IMPORTANT: More specific routes must come BEFORE the generic /{paper_id} route
# to ensure proper route matching in FastAPI
@router.get("/{paper_id}/pdf")
async def get_paper_pdf(
    paper_id: int, session: AsyncSession = Depends(get_async_session)
):
    """
    Get PDF file for viewing (not download).
    Public endpoint - no authentication required for PDF viewing.
    """
    logger.info(f"PDF request received for paper_id: {paper_id}")
    try:
        paper, full_path = await _get_paper_file_path(paper_id, session)
        logger.info(
            f"PDF file found for paper {paper_id}: stored_path='{paper.file_path}', "
            f"resolved_path='{full_path}', exists={full_path.exists()}"
        )

        # Verify file exists and is readable
        if not full_path.exists():
            logger.error(
                f"PDF file does not exist for paper {paper_id}: {full_path} "
                f"(resolved from stored path: {paper.file_path})"
            )
            raise HTTPException(
                status_code=404,
                detail=f"PDF file not found on server. Stored path: {paper.file_path}, "
                f"Resolved path: {full_path}",
            )

        if not full_path.is_file():
            logger.error(
                f"PDF path exists but is not a file for paper {paper_id}: {full_path}"
            )
            raise HTTPException(
                status_code=404, detail="PDF path exists but is not a file"
            )

        # Return file for inline viewing
        try:
            with open(full_path, "rb") as f:
                pdf_bytes = f.read()
            logger.info(
                f"Successfully read {len(pdf_bytes)} bytes for paper {paper_id}"
            )
        except PermissionError as e:
            logger.error(
                f"Permission denied reading PDF file for paper {paper_id}: {full_path} - {e}"
            )
            raise HTTPException(
                status_code=403, detail="Permission denied reading PDF file"
            )
        except Exception as e:
            logger.error(f"Error reading PDF file for paper {paper_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error reading PDF file: {str(e)}"
            )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                "Access-Control-Allow-Origin": "*",  # Allow cross-origin requests
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error serving PDF for paper {paper_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Unexpected server error: {str(e)}"
        )


@router.get("/{paper_id}/download")
async def download_paper(
    paper_id: int,
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Download the PDF file for a paper.
    """
    paper, full_path = await _get_paper_file_path(paper_id, session)

    # Generate a nice filename
    filename = f"{paper.title[:50]}.pdf" if paper.title else f"paper_{paper_id}.pdf"
    # Clean filename for download
    filename = "".join(
        c for c in filename if c.isalnum() or c in (" ", "-", "_", ".")
    ).strip()

    return FileResponse(
        path=str(full_path), filename=filename, media_type="application/pdf"
    )


@router.get("/{paper_id}/thumbnail")
async def get_paper_thumbnail(
    paper_id: int,
    regenerate: bool = Query(False, description="Force regenerate thumbnail"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get thumbnail image for a paper. Generates it if it doesn't exist.
    Public endpoint - no authentication required for thumbnail access.
    """
    try:
        # Use helper function to get paper and validate file path
        paper, pdf_full_path = await _get_paper_file_path(paper_id, session)

        # Initialize thumbnail generator with the same storage root
        paper_manager = PaperManagerService(session)
        thumbnail_gen = ThumbnailGenerator(
            storage_root=str(paper_manager.file_storage.storage_root)
        )

        # Generate thumbnail using the full PDF path
        # Pass the absolute path directly since we've already resolved it
        # The generate_thumbnail method will handle absolute paths correctly
        thumbnail_relative_path = thumbnail_gen.generate_thumbnail(
            str(pdf_full_path.resolve()), paper_id, force_regenerate=regenerate
        )

        if not thumbnail_relative_path:
            logger.error(
                f"Thumbnail generation failed for paper {paper_id}, PDF path: {paper.file_path}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate thumbnail. Check server logs for details.",
            )

        # Get full thumbnail path
        thumbnail_full_path = thumbnail_gen.get_thumbnail_path(thumbnail_relative_path)

        if not thumbnail_full_path.exists():
            logger.error(f"Generated thumbnail not found at: {thumbnail_full_path}")
            raise HTTPException(status_code=404, detail="Thumbnail file not found")

        # Return thumbnail image with CORS headers for cross-origin requests
        return FileResponse(
            path=str(thumbnail_full_path),
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                "Content-Disposition": "inline",
                "Access-Control-Allow-Origin": "*",  # Allow cross-origin requests
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Unexpected error generating thumbnail for paper {paper_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail="Unexpected server error while generating thumbnail"
        )


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get a specific paper by ID.

    If the paper needs enrichment (missing lay_summary, insights, etc.),
    enrichment will be triggered in the background without blocking the response.
    """
    try:
        paper_manager = PaperManagerService(session)
        paper = await paper_manager.get_paper_by_id(paper_id)

        if not paper:
            logger.warning(f"Paper {paper_id} not found for user {user.id}")
            raise HTTPException(status_code=404, detail="Paper not found")

        # Check if enrichment is needed and trigger it in the background
        # Also check if enrichment is already in progress to avoid duplicate tasks
        if (
            paper_manager._needs_enrichment(paper)
            and paper_id not in _enrichment_in_progress
        ):
            logger.info(
                f"Paper {paper_id} needs enrichment, triggering background task"
            )
            background_tasks.add_task(_enrich_paper_in_background, paper_id)
        elif paper_id in _enrichment_in_progress:
            logger.debug(
                f"Paper {paper_id} enrichment already in progress, skipping duplicate task spawn"
            )

        return PaperResponse.from_orm(paper)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving paper {paper_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving paper: {str(e)}")


@router.post("/{paper_id}/citation", response_model=CitationResponse)
async def get_citation(
    paper_id: int,
    citation_request: CitationRequest,
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
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
            citation=citation, style=citation_request.style, paper_id=paper_id
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
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
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
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
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
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Start the folder watcher for automatic PDF processing.
    """
    paper_manager = PaperManagerService(session)
    paper_manager.start_folder_watcher(
        user_id=str(user.id), search_space_id=search_space_id
    )

    return {"message": "Folder watcher started", "search_space_id": search_space_id}


@router.post("/watcher/stop")
async def stop_watcher(
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Stop the folder watcher.
    """
    paper_manager = PaperManagerService(session)
    paper_manager.stop_folder_watcher()

    return {"message": "Folder watcher stopped"}


@router.get("/watcher/status", response_model=WatcherStatusResponse)
async def get_watcher_status(
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
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
            pdf_count=0,
        )

    return WatcherStatusResponse(**status)


@router.get("/for-devonthink-export")
async def get_papers_for_devonthink_export(
    limit: int = Query(100, le=500, description="Maximum number of papers to return"),
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get papers that were uploaded by users but not yet synced to DEVONthink.

    These papers have dt_source_uuid = NULL, meaning they were uploaded directly
    to the library (not imported from DEVONthink). They can be exported back to
    DEVONthink to complete bidirectional syncing.

    Returns papers that need to be synced TO DEVONthink.
    """
    from app.db import Document, ScientificPaper, SearchSpace
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # Query papers without dt_source_uuid (uploaded by users, not from DEVONthink)
    # and belonging to the current user's search spaces
    stmt = (
        select(ScientificPaper)
        .options(selectinload(ScientificPaper.document))
        .join(Document)
        .join(SearchSpace)
        .where(
            ScientificPaper.dt_source_uuid.is_(None),  # Not from DEVONthink
            SearchSpace.user_id == user.id,  # Belongs to current user
        )
        .order_by(ScientificPaper.created_at.desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    papers = result.scalars().all()

    return {
        "papers": [PaperResponse.from_orm(paper) for paper in papers],
        "total": len(papers),
        "message": f"Found {len(papers)} paper(s) ready for DEVONthink export",
    }


@router.get("/stats/by-room")
async def get_papers_by_room(
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get paper counts by literature type (room).
    """
    from app.db import Document, ScientificPaper, SearchSpace
    from sqlalchemy import func, select

    # Count papers by literature type for user's search spaces
    stmt = (
        select(
            ScientificPaper.literature_type,
            func.count(ScientificPaper.id).label("count"),
        )
        .join(Document, Document.id == ScientificPaper.document_id)
        .join(SearchSpace, SearchSpace.id == Document.search_space_id)
        .where(SearchSpace.user_id == user.id)
        .group_by(ScientificPaper.literature_type)
    )

    result = await session.execute(stmt)
    room_stats = {row[0]: row[1] for row in result.fetchall()}

    # Ensure all rooms are represented
    return {
        "PEER_REVIEWED": room_stats.get("PEER_REVIEWED", 0),
        "GREY_LITERATURE": room_stats.get("GREY_LITERATURE", 0),
        "NEWS": room_stats.get("NEWS", 0),
        "total": sum(room_stats.values()),
    }


@router.post("/thumbnails/generate-batch")
async def generate_thumbnails_batch(
    search_space_id: Optional[int] = Form(None),
    force_regenerate: bool = Form(False),
    limit: int = Form(100, le=500),
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Generate thumbnails for multiple papers in batch.
    Useful for initial setup or regenerating thumbnails.
    """
    from app.db import Document, ScientificPaper, SearchSpace
    from sqlalchemy import select

    # Build query to get papers
    stmt = (
        select(ScientificPaper)
        .join(Document, Document.id == ScientificPaper.document_id)
        .join(SearchSpace, SearchSpace.id == Document.search_space_id)
        .where(SearchSpace.user_id == user.id)
    )

    if search_space_id:
        stmt = stmt.where(Document.search_space_id == search_space_id)

    stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    papers = result.scalars().all()

    if not papers:
        return {
            "message": "No papers found",
            "success_count": 0,
            "failure_count": 0,
            "total": 0,
        }

    # Initialize thumbnail generator with the same storage root
    paper_manager = PaperManagerService(session)
    thumbnail_gen = ThumbnailGenerator(
        storage_root=str(paper_manager.file_storage.storage_root)
    )
    success_count, failure_count = thumbnail_gen.batch_generate_thumbnails(
        papers, force_regenerate=force_regenerate
    )

    return {
        "message": f"Generated thumbnails for {success_count} papers",
        "success_count": success_count,
        "failure_count": failure_count,
        "total": len(papers),
    }


@router.post("/{paper_id}/favorite")
async def add_favorite(
    paper_id: int,
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Add a paper to the user's favorites.
    """
    from app.db import ScientificPaper, user_favorites
    from sqlalchemy import insert, select

    # Check if paper exists
    paper_stmt = select(ScientificPaper).where(ScientificPaper.id == paper_id)
    paper_result = await session.execute(paper_stmt)
    paper = paper_result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Check if already favorited
    check_stmt = select(user_favorites).where(
        user_favorites.c.user_id == user.id,
        user_favorites.c.paper_id == paper_id,
    )
    check_result = await session.execute(check_stmt)
    if check_result.first():
        return {"message": "Paper already in favorites", "is_favorited": True}

    # Add to favorites
    insert_stmt = insert(user_favorites).values(
        user_id=user.id,
        paper_id=paper_id,
    )
    await session.execute(insert_stmt)
    await session.commit()

    return {"message": "Paper added to favorites", "is_favorited": True}


@router.delete("/{paper_id}/favorite")
async def remove_favorite(
    paper_id: int,
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Remove a paper from the user's favorites.
    """
    from app.db import user_favorites
    from sqlalchemy import delete

    # Remove from favorites
    delete_stmt = delete(user_favorites).where(
        user_favorites.c.user_id == user.id,
        user_favorites.c.paper_id == paper_id,
    )
    result = await session.execute(delete_stmt)
    await session.commit()

    if result.rowcount == 0:
        return {"message": "Paper was not in favorites", "is_favorited": False}

    return {"message": "Paper removed from favorites", "is_favorited": False}


@router.get("/{paper_id}/is-favorited")
async def is_favorited(
    paper_id: int,
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Check if a paper is in the user's favorites.
    """
    from app.db import user_favorites
    from sqlalchemy import select

    check_stmt = select(user_favorites).where(
        user_favorites.c.user_id == user.id,
        user_favorites.c.paper_id == paper_id,
    )
    check_result = await session.execute(check_stmt)
    is_fav = check_result.first() is not None

    return {"is_favorited": is_fav, "paper_id": paper_id}


@router.get("/favorites/list", response_model=PaperListResponse)
async def get_favorites(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get all papers in the user's favorites.
    """
    from app.db import ScientificPaper, user_favorites
    from sqlalchemy import select

    # Get favorited papers
    stmt = (
        select(ScientificPaper)
        .join(user_favorites, user_favorites.c.paper_id == ScientificPaper.id)
        .where(user_favorites.c.user_id == user.id)
        .order_by(user_favorites.c.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(stmt)
    papers = result.scalars().all()

    return PaperListResponse(
        papers=[PaperResponse.from_orm(paper) for paper in papers],
        total=len(papers),
        limit=limit,
        offset=offset,
    )


@router.post("/{paper_id}/reports/generate", response_model=PaperReportResponse)
async def generate_paper_report(
    paper_id: int,
    request: PaperReportRequest,
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Generate a report for a paper.

    Supports multiple report types: quick-summary, comprehensive, critical-appraisal,
    methodology, and research-gaps. Uses the user's OpenRouter API key for BYOK.
    """
    try:
        # Verify paper exists and user has access
        paper_manager = PaperManagerService(session)
        paper = await paper_manager.get_paper_by_id(paper_id)

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Check ownership via document's search space
        if paper.document:
            from app.db import SearchSpace
            from sqlalchemy import select

            stmt = select(SearchSpace).where(
                SearchSpace.id == paper.document.search_space_id
            )
            result = await session.execute(stmt)
            search_space = result.scalar_one_or_none()

            if search_space and search_space.user_id != user.id:
                raise HTTPException(
                    status_code=403, detail="You don't have access to this paper"
                )

        # Initialize report service with user's OpenRouter key
        report_service = PaperReportService(
            session=session,
            openrouter_api_key=user.openrouter_api_key,
        )

        # Generate report based on type
        report_type_map = {
            "quick-summary": report_service.generate_quick_summary,
            "comprehensive": report_service.generate_comprehensive_analysis,
            "critical-appraisal": report_service.generate_critical_appraisal,
            "methodology": report_service.generate_methodology_assessment,
            "research-gaps": report_service.generate_research_gap_analysis,
        }

        if request.report_type not in report_type_map:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report type. Must be one of: {', '.join(report_type_map.keys())}",
            )

        logger.info(
            f"Generating {request.report_type} report for paper {paper_id} (user: {user.id})"
        )
        report_content = await report_type_map[request.report_type](paper_id)

        if not report_content:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate report. Please check your API key configuration and try again.",
            )

        return PaperReportResponse(
            report_type=request.report_type,
            report_content=report_content,
            paper_id=paper_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error generating report for paper {paper_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Error generating report: {str(e)}"
        )
