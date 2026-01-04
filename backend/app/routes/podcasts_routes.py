"""
Podcast API Routes for HERO Evidence Library v2.0

Endpoints:
- POST /api/v2/podcasts/generate - Generate podcast from single paper
- POST /api/v2/podcasts/generate-multi - Generate from multiple papers
- GET /api/v2/podcasts - List user's podcasts
- GET /api/v2/podcasts/{podcast_id} - Get podcast details
- DELETE /api/v2/podcasts/{podcast_id} - Delete podcast
- GET /api/v2/podcasts/{podcast_id}/download - Download audio file
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from pydantic import BaseModel, Field
from pathlib import Path

from app.db import get_db, Podcast, User
from app.middleware.clerk_auth import ClerkUser, get_current_user_id
from app.services.podcast_generation_service import PodcastGenerationService
from app.services.tts_service import TTSService, TTSProvider


router = APIRouter(prefix="/api/v2/podcasts", tags=["podcasts-v2"])


# Request/Response Models
class PodcastGenerateRequest(BaseModel):
    """Request body for single-paper podcast generation."""
    paper_id: int = Field(..., description="ID of the paper to generate podcast from")
    model: Optional[str] = Field(None, description="OpenRouter model (uses user default if not specified)")
    tts_provider: Optional[str] = Field("auto", description="TTS provider: auto, kokoro, openai, elevenlabs")
    voice: Optional[str] = Field(None, description="Voice ID (provider-specific)")


class PodcastGenerateMultiRequest(BaseModel):
    """Request body for multi-paper podcast generation."""
    paper_ids: List[int] = Field(..., description="List of paper IDs", min_items=2, max_items=10)
    model: Optional[str] = Field(None, description="OpenRouter model")
    tts_provider: Optional[str] = Field("auto", description="TTS provider")
    voice: Optional[str] = Field(None, description="Voice ID")
    focus: Optional[str] = Field(None, description="Focus area (e.g., 'methodology', 'findings')")


class PodcastResponse(BaseModel):
    """Response model for podcast data."""
    id: int
    user_id: int
    source_paper_ids: List[int]
    title: str
    podcast_transcript: str
    duration_seconds: int
    file_location: str
    generation_model: str
    tts_provider: str
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/generate", response_model=PodcastResponse, status_code=status.HTTP_201_CREATED)
async def generate_podcast(
    request: PodcastGenerateRequest,
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a podcast from a single research paper.
    
    The podcast will be a conversational discussion between two AI hosts
    explaining and analyzing the paper.
    """
    # Get user from database to access API keys
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check for required API keys
    if not db_user.openrouter_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key not configured. Please add it in your profile settings."
        )
    
    # Initialize services
    tts_service = TTSService(
        user_id=db_user.id,
        openai_api_key=db_user.openai_api_key,
        elevenlabs_api_key=db_user.elevenlabs_api_key,
        optimization_mode=db_user.tts_optimization_mode or "auto"
    )
    
    podcast_service = PodcastGenerationService(
        db=db,
        openrouter_api_key=db_user.openrouter_api_key,
        tts_service=tts_service
    )
    
    # Generate podcast
    try:
        podcast = await podcast_service.generate_podcast(
            paper_id=request.paper_id,
            user_id=db_user.id,
            model=request.model or db_user.default_openrouter_model or "anthropic/claude-sonnet-4-20250514",
            tts_provider=request.tts_provider,
            voice=request.voice
        )
        
        return PodcastResponse(
            id=podcast.id,
            user_id=podcast.user_id,
            source_paper_ids=podcast.source_paper_ids,
            title=podcast.title,
            podcast_transcript=podcast.podcast_transcript,
            duration_seconds=podcast.duration_seconds,
            file_location=podcast.file_location,
            generation_model=podcast.generation_model,
            tts_provider=podcast.tts_provider,
            created_at=podcast.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate podcast: {str(e)}"
        )


@router.post("/generate-multi", response_model=PodcastResponse, status_code=status.HTTP_201_CREATED)
async def generate_multi_paper_podcast(
    request: PodcastGenerateMultiRequest,
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a comparative podcast discussing multiple research papers.
    
    The podcast will compare and contrast the papers, identifying
    common themes and key differences.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if not db_user.openrouter_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key not configured"
        )
    
    # Initialize services
    tts_service = TTSService(
        user_id=db_user.id,
        openai_api_key=db_user.openai_api_key,
        elevenlabs_api_key=db_user.elevenlabs_api_key,
        optimization_mode=db_user.tts_optimization_mode or "auto"
    )
    
    podcast_service = PodcastGenerationService(
        db=db,
        openrouter_api_key=db_user.openrouter_api_key,
        tts_service=tts_service
    )
    
    # Generate podcast
    try:
        podcast = await podcast_service.generate_multi_paper_podcast(
            paper_ids=request.paper_ids,
            user_id=db_user.id,
            model=request.model or db_user.default_openrouter_model or "anthropic/claude-sonnet-4-20250514",
            tts_provider=request.tts_provider,
            voice=request.voice,
            focus=request.focus
        )
        
        return PodcastResponse(
            id=podcast.id,
            user_id=podcast.user_id,
            source_paper_ids=podcast.source_paper_ids,
            title=podcast.title,
            podcast_transcript=podcast.podcast_transcript,
            duration_seconds=podcast.duration_seconds,
            file_location=podcast.file_location,
            generation_model=podcast.generation_model,
            tts_provider=podcast.tts_provider,
            created_at=podcast.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate podcast: {str(e)}"
        )


@router.get("", response_model=List[PodcastResponse])
async def list_podcasts(
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    List all podcasts created by the current user.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Fetch podcasts
    result = await db.execute(
        select(Podcast)
        .where(Podcast.user_id == db_user.id)
        .order_by(Podcast.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    podcasts = result.scalars().all()
    
    return [
        PodcastResponse(
            id=p.id,
            user_id=p.user_id,
            source_paper_ids=p.source_paper_ids,
            title=p.title,
            podcast_transcript=p.podcast_transcript,
            duration_seconds=p.duration_seconds,
            file_location=p.file_location,
            generation_model=p.generation_model,
            tts_provider=p.tts_provider,
            created_at=p.created_at.isoformat()
        )
        for p in podcasts
    ]


@router.get("/{podcast_id}", response_model=PodcastResponse)
async def get_podcast(
    podcast_id: int,
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific podcast.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Fetch podcast
    result = await db.execute(
        select(Podcast).where(
            and_(
                Podcast.id == podcast_id,
                Podcast.user_id == db_user.id
            )
        )
    )
    podcast = result.scalar_one_or_none()
    
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    return PodcastResponse(
        id=podcast.id,
        user_id=podcast.user_id,
        source_paper_ids=podcast.source_paper_ids,
        title=podcast.title,
        podcast_transcript=podcast.podcast_transcript,
        duration_seconds=podcast.duration_seconds,
        file_location=podcast.file_location,
        generation_model=podcast.generation_model,
        tts_provider=podcast.tts_provider,
        created_at=podcast.created_at.isoformat()
    )


@router.delete("/{podcast_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_podcast(
    podcast_id: int,
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a podcast.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Fetch and delete podcast
    result = await db.execute(
        select(Podcast).where(
            and_(
                Podcast.id == podcast_id,
                Podcast.user_id == db_user.id
            )
        )
    )
    podcast = result.scalar_one_or_none()
    
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    # Delete audio file if it exists
    audio_path = Path(podcast.file_location)
    if audio_path.exists():
        audio_path.unlink()
    
    # Delete database record
    await db.delete(podcast)
    await db.commit()


@router.get("/{podcast_id}/download")
async def download_podcast(
    podcast_id: int,
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Download the audio file for a podcast.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Fetch podcast
    result = await db.execute(
        select(Podcast).where(
            and_(
                Podcast.id == podcast_id,
                Podcast.user_id == db_user.id
            )
        )
    )
    podcast = result.scalar_one_or_none()
    
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    # Check if file exists
    audio_path = Path(podcast.file_location)
    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )
    
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=f"podcast_{podcast_id}.mp3"
    )
