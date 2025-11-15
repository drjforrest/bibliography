from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_async_session, User
from app.users import current_active_user
from pydantic import BaseModel
from typing import Optional
import os
import uuid
from pathlib import Path

router = APIRouter()


class UserAPIKeysUpdate(BaseModel):
    openrouter_api_key: Optional[str] = None


class UserAPIKeysResponse(BaseModel):
    openrouter_api_key_set: bool


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    openrouter_api_key_set: bool

    class Config:
        from_attributes = True


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Get the current user's profile information."""
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        openrouter_api_key_set=bool(user.openrouter_api_key),
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile: UserProfileUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Update the current user's profile information."""
    if profile.display_name is not None:
        user.display_name = profile.display_name

    if profile.bio is not None:
        user.bio = profile.bio

    await session.commit()
    await session.refresh(user)

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        openrouter_api_key_set=bool(user.openrouter_api_key),
    )


@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Upload a new avatar image for the user."""
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed.")

    # Create avatars directory if it doesn't exist
    avatars_dir = Path("data/avatars")
    avatars_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{user.id}{file_ext}"
    file_path = avatars_dir / filename

    # Save the file
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save avatar: {str(e)}")

    # Update user's avatar_url
    user.avatar_url = f"/avatars/{filename}"
    await session.commit()
    await session.refresh(user)

    return {
        "avatar_url": user.avatar_url,
        "message": "Avatar uploaded successfully"
    }


@router.delete("/profile/avatar")
async def delete_avatar(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Delete the user's avatar."""
    if user.avatar_url:
        # Try to delete the physical file
        try:
            file_path = Path(f"data{user.avatar_url}")
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to delete avatar file: {str(e)}")

        # Update database
        user.avatar_url = None
        await session.commit()

    return {"message": "Avatar deleted successfully"}


@router.get("/avatars/{filename}")
async def get_avatar(filename: str):
    """Serve user avatar files."""
    file_path = Path(f"data/avatars/{filename}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Avatar not found")

    return FileResponse(file_path)


@router.get("/api-keys", response_model=UserAPIKeysResponse)
async def get_api_keys_status(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Get the status of user's OpenRouter API key (whether it is set or not)."""
    return UserAPIKeysResponse(
        openrouter_api_key_set=bool(user.openrouter_api_key),
    )


@router.put("/api-keys", response_model=UserAPIKeysResponse)
async def update_api_keys(
    api_keys: UserAPIKeysUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Update user's OpenRouter API key."""
    if api_keys.openrouter_api_key is not None:
        user.openrouter_api_key = api_keys.openrouter_api_key

    await session.commit()

    return UserAPIKeysResponse(
        openrouter_api_key_set=bool(user.openrouter_api_key),
    )
