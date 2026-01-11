"""
Visual Abstract API Routes for generating and managing visual abstracts.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

from app.db import ScientificPaper, User, VisualAbstract, get_async_session
from app.middleware.clerk_auth import require_clerk_auth
from app.services.visual_abstract_service import VisualAbstractService
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visual-abstracts", tags=["visual-abstracts"])


# Request/Response Schemas
class VisualAbstractGenerateRequest(BaseModel):
    """Request schema for generating a visual abstract."""

    paper_id: int
    regenerate: bool = False  # If True, regenerate even if one exists


class VisualAbstractResponse(BaseModel):
    """Response schema for visual abstract data."""

    id: int
    paper_id: int
    file_path: str
    prompt_used: Optional[str] = None
    model_used: Optional[str] = None
    expires_at: str
    created_at: str
    paper_title: Optional[str] = None

    class Config:
        from_attributes = True


class VisualAbstractListResponse(BaseModel):
    """Response schema for listing visual abstracts."""

    visual_abstracts: List[VisualAbstractResponse]
    total: int


async def get_user_api_keys(user: User) -> dict:
    """
    Get user's API keys for visual abstract generation.

    Prefers OpenAI if configured (likely cheaper), falls back to OpenRouter.

    Args:
        user: User object with API keys

    Returns:
        Dictionary with API keys
    """
    keys = {
        "openai_api_key": user.openai_api_key,
        "openrouter_api_key": user.openrouter_api_key
        or os.getenv("OPENROUTER_API_KEY"),
    }

    return keys


async def verify_paper_access(
    session: AsyncSession, paper_id: int, user: User
) -> ScientificPaper:
    """
    Verify user has access to the paper.

    Returns:
        ScientificPaper object
    """
    stmt = (
        select(ScientificPaper)
        .where(ScientificPaper.id == paper_id)
        .options(selectinload(ScientificPaper.document))
    )
    result = await session.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")

    if not paper.document:
        raise HTTPException(
            status_code=404, detail=f"Paper {paper_id} has no associated document"
        )

    # Verify user owns the search space
    from app.db import SearchSpace

    stmt = select(SearchSpace).where(
        SearchSpace.id == paper.document.search_space_id,
        SearchSpace.user_id == user.id,
    )
    result = await session.execute(stmt)
    search_space = result.scalar_one_or_none()

    if not search_space:
        raise HTTPException(
            status_code=403, detail="You don't have access to this paper"
        )

    return paper


@router.post("/generate", response_model=VisualAbstractResponse)
async def generate_visual_abstract(
    request: VisualAbstractGenerateRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """
    Generate a visual abstract for a paper.

    Requires:
    - User's OpenAI API key (preferred, likely cheaper) OR
    - User's OpenRouter API key (fallback)
    """
    try:
        # Verify paper access
        paper = await verify_paper_access(session, request.paper_id, user)

        # Get user's API keys
        api_keys = await get_user_api_keys(user)

        if not api_keys["openai_api_key"] and not api_keys["openrouter_api_key"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Either OpenAI API key or OpenRouter API key is required. "
                    "Please configure one in Settings."
                ),
            )

        # Initialize visual abstract service
        visual_abstract_service = VisualAbstractService(
            session=session,
            openai_api_key=api_keys["openai_api_key"],
            openrouter_api_key=api_keys["openrouter_api_key"],
        )

        try:
            # Generate visual abstract
            visual_abstract = await visual_abstract_service.generate_visual_abstract(
                paper_id=request.paper_id, regenerate=request.regenerate
            )

            return VisualAbstractResponse(
                id=visual_abstract.id,
                paper_id=visual_abstract.paper_id,
                file_path=visual_abstract.file_path,
                prompt_used=visual_abstract.prompt_used,
                model_used=visual_abstract.model_used,
                expires_at=visual_abstract.expires_at.isoformat()
                if visual_abstract.expires_at
                else "",
                created_at=visual_abstract.created_at.isoformat()
                if visual_abstract.created_at
                else "",
                paper_title=paper.title,
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to generate visual abstract: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to generate visual abstract: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating visual abstract: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate visual abstract: {str(e)}"
        )


@router.get("/paper/{paper_id}", response_model=Optional[VisualAbstractResponse])
async def get_paper_visual_abstract(
    paper_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """Get the current visual abstract for a paper (if not expired)."""
    try:
        # Verify paper access
        paper = await verify_paper_access(session, paper_id, user)

        # Get user's API keys (needed for service initialization)
        api_keys = await get_user_api_keys(user)

        visual_abstract_service = VisualAbstractService(
            session=session,
            openai_api_key=api_keys["openai_api_key"],
            openrouter_api_key=api_keys["openrouter_api_key"],
        )

        visual_abstract = await visual_abstract_service.get_visual_abstract(paper_id)

        if not visual_abstract:
            return None

        return VisualAbstractResponse(
            id=visual_abstract.id,
            paper_id=visual_abstract.paper_id,
            file_path=visual_abstract.file_path,
            prompt_used=visual_abstract.prompt_used,
            model_used=visual_abstract.model_used,
            expires_at=visual_abstract.expires_at.isoformat()
            if visual_abstract.expires_at
            else "",
            created_at=visual_abstract.created_at.isoformat()
            if visual_abstract.created_at
            else "",
            paper_title=paper.title,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get visual abstract: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get visual abstract: {str(e)}"
        )


@router.get("/", response_model=VisualAbstractListResponse)
async def list_visual_abstracts(
    limit: int = Query(50, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """List user's visual abstracts (from their papers)."""
    try:
        # Get all papers owned by user
        from app.db import Document, SearchSpace

        # Build query to get visual abstracts for user's papers
        stmt = (
            select(VisualAbstract, ScientificPaper)
            .join(ScientificPaper, VisualAbstract.paper_id == ScientificPaper.id)
            .join(Document, ScientificPaper.document_id == Document.id)
            .join(SearchSpace, Document.search_space_id == SearchSpace.id)
            .where(SearchSpace.user_id == user.id)
        )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Get paginated results
        stmt = (
            stmt.order_by(VisualAbstract.created_at.desc()).limit(limit).offset(offset)
        )
        result = await session.execute(stmt)
        rows = result.all()

        visual_abstract_responses = []
        for visual_abstract, paper in rows:
            visual_abstract_responses.append(
                VisualAbstractResponse(
                    id=visual_abstract.id,
                    paper_id=visual_abstract.paper_id,
                    file_path=visual_abstract.file_path,
                    prompt_used=visual_abstract.prompt_used,
                    model_used=visual_abstract.model_used,
                    expires_at=visual_abstract.expires_at.isoformat()
                    if visual_abstract.expires_at
                    else "",
                    created_at=visual_abstract.created_at.isoformat()
                    if visual_abstract.created_at
                    else "",
                    paper_title=paper.title,
                )
            )

        return VisualAbstractListResponse(
            visual_abstracts=visual_abstract_responses, total=total
        )

    except Exception as e:
        logger.error(f"Failed to list visual abstracts: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list visual abstracts: {str(e)}"
        )


@router.get("/{visual_abstract_id}/image")
async def get_visual_abstract_image(
    visual_abstract_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """Get the image file for a visual abstract."""
    try:
        from app.db import Document, SearchSpace

        # Get visual abstract and verify ownership
        stmt = (
            select(VisualAbstract)
            .join(ScientificPaper, VisualAbstract.paper_id == ScientificPaper.id)
            .join(Document, ScientificPaper.document_id == Document.id)
            .join(SearchSpace, Document.search_space_id == SearchSpace.id)
            .where(
                VisualAbstract.id == visual_abstract_id,
                SearchSpace.user_id == user.id,
            )
        )
        result = await session.execute(stmt)
        visual_abstract = result.scalar_one_or_none()

        if not visual_abstract:
            raise HTTPException(
                status_code=404,
                detail=f"Visual abstract {visual_abstract_id} not found",
            )

        file_path = Path(visual_abstract.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Image file not found for visual abstract {visual_abstract_id}",
            )

        return FileResponse(
            path=str(file_path),
            filename=f"visual_abstract_{visual_abstract_id}.png",
            media_type="image/png",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get visual abstract image: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get visual abstract image: {str(e)}"
        )


@router.post("/cleanup-expired")
async def cleanup_expired_abstracts(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """
    Manually trigger cleanup of expired visual abstracts.

    This endpoint can be called periodically (e.g., via cron job) to clean up
    visual abstracts that have exceeded their 30-day expiration period.
    """
    try:
        from app.services.visual_abstract_service import VisualAbstractService

        # Initialize service (API keys not needed for cleanup)
        visual_abstract_service = VisualAbstractService(
            session=session,
            openai_api_key=None,
            openrouter_api_key=None,
        )

        deleted_count = await visual_abstract_service.cleanup_expired()

        return {
            "message": f"Cleanup completed: {deleted_count} expired visual abstracts deleted",
            "deleted_count": deleted_count,
        }

    except Exception as e:
        logger.error(f"Failed to cleanup expired visual abstracts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup expired visual abstracts: {str(e)}",
        )


@router.delete("/{visual_abstract_id}")
async def delete_visual_abstract(
    visual_abstract_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """Delete a visual abstract and its image file."""
    try:
        from app.db import Document, SearchSpace

        # Get visual abstract and verify ownership
        stmt = (
            select(VisualAbstract)
            .join(ScientificPaper, VisualAbstract.paper_id == ScientificPaper.id)
            .join(Document, ScientificPaper.document_id == Document.id)
            .join(SearchSpace, Document.search_space_id == SearchSpace.id)
            .where(
                VisualAbstract.id == visual_abstract_id,
                SearchSpace.user_id == user.id,
            )
        )
        result = await session.execute(stmt)
        visual_abstract = result.scalar_one_or_none()

        if not visual_abstract:
            raise HTTPException(
                status_code=404,
                detail=f"Visual abstract {visual_abstract_id} not found",
            )

        # Delete image file
        file_path = Path(visual_abstract.file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted image file: {file_path}")

        # Delete database record
        await session.delete(visual_abstract)
        await session.commit()

        return {"message": f"Visual abstract {visual_abstract_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to delete visual abstract: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete visual abstract: {str(e)}"
        )
