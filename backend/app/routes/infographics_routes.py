"""
Infographic API Routes for HERO Evidence Library v2.0

Endpoints for generating visual infographics from research papers.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from pydantic import BaseModel, Field
from pathlib import Path

from app.db import get_db, Infographic, User
from app.middleware.clerk_auth import ClerkUser, get_current_user_id
from app.services.infographic_generation_service import (
    InfographicGenerationService,
    InfographicStyle,
    InfographicFocus
)


router = APIRouter(prefix="/api/v2/infographics", tags=["infographics-v2"])


# Request/Response Models
class InfographicGenerateRequest(BaseModel):
    """Request body for infographic generation."""
    paper_id: int = Field(..., description="ID of the paper to create infographic from")
    style: Optional[InfographicStyle] = Field("modern", description="Visual style")
    focus: Optional[InfographicFocus] = Field("all", description="Content focus area")
    color_scheme: Optional[str] = Field("professional", description="Color palette")
    custom_description: Optional[str] = Field(None, max_length=500, description="Optional customization")


class InfographicResponse(BaseModel):
    """Response model for infographic data."""
    id: int
    user_id: int
    source_paper_id: int
    title: str
    image_url: str
    style: str
    focus_area: str
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/generate", response_model=InfographicResponse, status_code=status.HTTP_201_CREATED)
async def generate_infographic(
    request: InfographicGenerateRequest,
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a visual infographic from a research paper.
    
    Creates a full-page 16:9 infographic using Google Gemini imagen.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check for OpenRouter API key
    if not db_user.openrouter_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key not configured. Please add it in your profile settings."
        )
    
    # Initialize service
    infographic_service = InfographicGenerationService(
        db=db,
        openrouter_api_key=db_user.openrouter_api_key
    )
    
    # Generate infographic
    try:
        infographic = await infographic_service.generate_infographic(
            paper_id=request.paper_id,
            user_id=db_user.id,
            style=request.style,
            focus=request.focus,
            color_scheme=request.color_scheme,
            custom_description=request.custom_description
        )
        
        return InfographicResponse(
            id=infographic.id,
            user_id=infographic.user_id,
            source_paper_id=infographic.source_paper_id,
            title=infographic.title,
            image_url=infographic.image_url,
            style=infographic.style,
            focus_area=infographic.focus_area,
            created_at=infographic.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate infographic: {str(e)}"
        )


@router.get("", response_model=List[InfographicResponse])
async def list_infographics(
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    List all infographics created by the current user.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Fetch infographics
    result = await db.execute(
        select(Infographic)
        .where(Infographic.user_id == db_user.id)
        .order_by(Infographic.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    infographics = result.scalars().all()
    
    return [
        InfographicResponse(
            id=i.id,
            user_id=i.user_id,
            source_paper_id=i.source_paper_id,
            title=i.title,
            image_url=i.image_url,
            style=i.style,
            focus_area=i.focus_area,
            created_at=i.created_at.isoformat()
        )
        for i in infographics
    ]


@router.get("/{infographic_id}", response_model=InfographicResponse)
async def get_infographic(
    infographic_id: int,
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific infographic.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Fetch infographic
    result = await db.execute(
        select(Infographic).where(
            and_(
                Infographic.id == infographic_id,
                Infographic.user_id == db_user.id
            )
        )
    )
    infographic = result.scalar_one_or_none()
    
    if not infographic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infographic not found"
        )
    
    return InfographicResponse(
        id=infographic.id,
        user_id=infographic.user_id,
        source_paper_id=infographic.source_paper_id,
        title=infographic.title,
        image_url=infographic.image_url,
        style=infographic.style,
        focus_area=infographic.focus_area,
        created_at=infographic.created_at.isoformat()
    )


@router.delete("/{infographic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_infographic(
    infographic_id: int,
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an infographic.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Fetch and delete infographic
    result = await db.execute(
        select(Infographic).where(
            and_(
                Infographic.id == infographic_id,
                Infographic.user_id == db_user.id
            )
        )
    )
    infographic = result.scalar_one_or_none()
    
    if not infographic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infographic not found"
        )
    
    # Delete image file if it exists
    image_path = Path(infographic.image_url)
    if image_path.exists():
        image_path.unlink()
    
    # Delete database record
    await db.delete(infographic)
    await db.commit()


@router.get("/{infographic_id}/download")
async def download_infographic(
    infographic_id: int,
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Download the image file for an infographic.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Fetch infographic
    result = await db.execute(
        select(Infographic).where(
            and_(
                Infographic.id == infographic_id,
                Infographic.user_id == db_user.id
            )
        )
    )
    infographic = result.scalar_one_or_none()
    
    if not infographic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infographic not found"
        )
    
    # Check if file exists
    image_path = Path(infographic.image_url)
    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found"
        )
    
    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        filename=f"infographic_{infographic_id}.png"
    )
