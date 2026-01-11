"""
Podcast API Routes for generating and managing podcasts from scientific papers.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from app.db import (
    Document,
    Podcast,
    ScientificPaper,
    SearchSpace,
    User,
    get_async_session,
)
from app.middleware.clerk_auth import require_clerk_auth
from app.services.podcast_generation_service import PodcastGenerationService
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/podcasts", tags=["podcasts"])


# Request/Response Schemas
class PodcastGenerateRequest(BaseModel):
    """Request schema for generating a podcast from a single paper."""

    paper_id: int
    title: Optional[str] = None
    tts_provider: Optional[str] = "openai"  # "openai", "elevenlabs", "kokoro"


class PodcastGenerateMultiRequest(BaseModel):
    """Request schema for generating a podcast from multiple papers."""

    paper_ids: List[int]
    title: Optional[str] = None
    tts_provider: Optional[str] = "openai"


class PodcastResponse(BaseModel):
    """Response schema for podcast data."""

    id: int
    title: str
    podcast_transcript: List[dict]
    file_location: str
    search_space_id: int
    created_at: str

    class Config:
        from_attributes = True


class PodcastListResponse(BaseModel):
    """Response schema for listing podcasts."""

    podcasts: List[PodcastResponse]
    total: int


async def get_user_api_keys(user: User, tts_provider: str = "openai") -> dict:
    """
    Get user's API keys for podcast generation.

    For TTS provider keys, uses user's database keys only (no environment variable fallback).
    For OpenRouter (LLM), uses user's database key with environment variable fallback.

    Args:
        user: User object with API keys
        tts_provider: TTS provider name ("openai" or "elevenlabs")

    Returns:
        Dictionary with API keys for the specified TTS provider
    """
    keys = {
        "openrouter_api_key": user.openrouter_api_key
        or os.getenv("OPENROUTER_API_KEY"),
    }

    # TTS provider keys come from user's database only (no env fallback)
    if tts_provider == "openai":
        keys["openai_api_key"] = user.openai_api_key
        keys["elevenlabs_api_key"] = None  # Not needed for OpenAI TTS
    elif tts_provider == "elevenlabs":
        keys["openai_api_key"] = None  # Not needed for ElevenLabs TTS
        keys["elevenlabs_api_key"] = user.elevenlabs_api_key
    else:
        # Default to OpenAI if provider not recognized
        keys["openai_api_key"] = user.openai_api_key
        keys["elevenlabs_api_key"] = None

    return keys


async def get_paper_with_search_space(
    session: AsyncSession, paper_id: int, user: User
) -> tuple[ScientificPaper, int]:
    """
    Get a paper and its search_space_id, ensuring user ownership.

    Returns:
        Tuple of (paper, search_space_id)
    """
    stmt = (
        select(ScientificPaper)
        .where(ScientificPaper.id == paper_id)
        .options(
            selectinload(ScientificPaper.document).selectinload(Document.search_space)
        )
    )
    result = await session.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")

    if not paper.document:
        raise HTTPException(
            status_code=404, detail=f"Paper {paper_id} has no associated document"
        )

    search_space_id = paper.document.search_space_id

    # Verify user owns this search space
    stmt = select(SearchSpace).where(
        SearchSpace.id == search_space_id, SearchSpace.user_id == user.id
    )
    result = await session.execute(stmt)
    search_space = result.scalar_one_or_none()

    if not search_space:
        raise HTTPException(
            status_code=403, detail="You don't have access to this paper"
        )

    return paper, search_space_id


@router.post("/generate", response_model=PodcastResponse)
async def generate_podcast(
    request: PodcastGenerateRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """
    Generate a podcast from a single paper.

    Requires:
    - User's OpenRouter API key (for LLM script generation)
    - TTS provider API key (OpenAI or ElevenLabs, based on tts_provider)
    """
    try:
        # Get paper and verify ownership
        paper, search_space_id = await get_paper_with_search_space(
            session, request.paper_id, user
        )

        # Get user's API keys for the specified TTS provider
        tts_provider = request.tts_provider or "openai"
        api_keys = await get_user_api_keys(user, tts_provider)

        if not api_keys["openrouter_api_key"]:
            raise HTTPException(
                status_code=400,
                detail="OpenRouter API key is required. Please configure it in Settings.",
            )

        # Validate TTS provider key
        if tts_provider == "openai" and not api_keys["openai_api_key"]:
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key is required for OpenAI TTS. Please configure it in Settings.",
            )
        elif tts_provider == "elevenlabs" and not api_keys["elevenlabs_api_key"]:
            raise HTTPException(
                status_code=400,
                detail="ElevenLabs API key is required for ElevenLabs TTS. Please configure it in Settings.",
            )

        # Initialize podcast generation service
        podcast_service = PodcastGenerationService(
            session=session,
            openrouter_api_key=api_keys["openrouter_api_key"],
            openai_api_key=api_keys["openai_api_key"],
            elevenlabs_api_key=api_keys["elevenlabs_api_key"],
            tts_provider=tts_provider,
        )

        try:
            # Generate podcast
            podcast = await podcast_service.generate_podcast(
                paper_id=request.paper_id,
                search_space_id=search_space_id,
                title=request.title,
            )

            if not podcast:
                raise HTTPException(
                    status_code=500, detail="Failed to generate podcast"
                )

            await podcast_service.close()

            return PodcastResponse(
                id=podcast.id,
                title=podcast.title,
                podcast_transcript=podcast.podcast_transcript,
                file_location=podcast.file_location,
                search_space_id=podcast.search_space_id,
                created_at=podcast.created_at.isoformat() if podcast.created_at else "",
            )

        finally:
            await podcast_service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate podcast: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate podcast: {str(e)}"
        )


@router.post("/generate-multi", response_model=PodcastResponse)
async def generate_multi_paper_podcast(
    request: PodcastGenerateMultiRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """
    Generate a comparative podcast from multiple papers.

    NOTE: This is a placeholder. Multi-paper podcast generation requires
    more complex script generation logic and is planned for future implementation.
    """
    raise HTTPException(
        status_code=501, detail="Multi-paper podcast generation is not yet implemented"
    )


@router.get("/", response_model=PodcastListResponse)
async def list_podcasts(
    search_space_id: Optional[int] = Query(None, description="Filter by search space"),
    limit: int = Query(50, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """List user's podcasts, optionally filtered by search space."""
    try:
        # Build query with user ownership check
        stmt = select(Podcast).join(SearchSpace).where(SearchSpace.user_id == user.id)

        if search_space_id:
            stmt = stmt.where(Podcast.search_space_id == search_space_id)

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Get paginated results
        stmt = stmt.order_by(Podcast.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        podcasts = result.scalars().all()

        podcast_responses = [
            PodcastResponse(
                id=p.id,
                title=p.title,
                podcast_transcript=p.podcast_transcript,
                file_location=p.file_location,
                search_space_id=p.search_space_id,
                created_at=p.created_at.isoformat() if p.created_at else "",
            )
            for p in podcasts
        ]

        return PodcastListResponse(podcasts=podcast_responses, total=total)

    except Exception as e:
        logger.error(f"Failed to list podcasts: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list podcasts: {str(e)}"
        )


@router.get("/{podcast_id}", response_model=PodcastResponse)
async def get_podcast(
    podcast_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """Get podcast details by ID."""
    try:
        stmt = (
            select(Podcast)
            .join(SearchSpace)
            .where(Podcast.id == podcast_id, SearchSpace.user_id == user.id)
        )
        result = await session.execute(stmt)
        podcast = result.scalar_one_or_none()

        if not podcast:
            raise HTTPException(
                status_code=404, detail=f"Podcast {podcast_id} not found"
            )

        return PodcastResponse(
            id=podcast.id,
            title=podcast.title,
            podcast_transcript=podcast.podcast_transcript,
            file_location=podcast.file_location,
            search_space_id=podcast.search_space_id,
            created_at=podcast.created_at.isoformat() if podcast.created_at else "",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get podcast: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get podcast: {str(e)}")


@router.delete("/{podcast_id}")
async def delete_podcast(
    podcast_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """Delete a podcast and its audio file."""
    try:
        stmt = (
            select(Podcast)
            .join(SearchSpace)
            .where(Podcast.id == podcast_id, SearchSpace.user_id == user.id)
        )
        result = await session.execute(stmt)
        podcast = result.scalar_one_or_none()

        if not podcast:
            raise HTTPException(
                status_code=404, detail=f"Podcast {podcast_id} not found"
            )

        # Delete audio file if it exists
        if podcast.file_location:
            try:
                file_path = Path(podcast.file_location)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted audio file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete audio file: {str(e)}")

        # Delete podcast record
        await session.delete(podcast)
        await session.commit()

        return {"message": f"Podcast {podcast_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to delete podcast: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete podcast: {str(e)}"
        )


@router.get("/{podcast_id}/download")
async def download_podcast(
    podcast_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_clerk_auth),
):
    """Download/stream podcast audio file."""
    try:
        stmt = (
            select(Podcast)
            .join(SearchSpace)
            .where(Podcast.id == podcast_id, SearchSpace.user_id == user.id)
        )
        result = await session.execute(stmt)
        podcast = result.scalar_one_or_none()

        if not podcast:
            raise HTTPException(
                status_code=404, detail=f"Podcast {podcast_id} not found"
            )

        if not podcast.file_location:
            raise HTTPException(
                status_code=404, detail=f"Podcast {podcast_id} has no audio file"
            )

        file_path = Path(podcast.file_location)
        if not file_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Audio file not found for podcast {podcast_id}"
            )

        return FileResponse(
            path=str(file_path),
            filename=f"{podcast.title}.mp3",
            media_type="audio/mpeg",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download podcast: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to download podcast: {str(e)}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download podcast: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to download podcast: {str(e)}"
        )
