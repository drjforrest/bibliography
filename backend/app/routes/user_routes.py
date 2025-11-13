from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_async_session, User
from app.users import current_active_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class UserAPIKeysUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

class UserAPIKeysResponse(BaseModel):
    openai_api_key_set: bool
    anthropic_api_key_set: bool

@router.get("/api-keys", response_model=UserAPIKeysResponse)
async def get_api_keys_status(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """Get the status of user's API keys (whether they are set or not)."""
    return UserAPIKeysResponse(
        openai_api_key_set=bool(user.openai_api_key),
        anthropic_api_key_set=bool(user.anthropic_api_key)
    )

@router.put("/api-keys", response_model=UserAPIKeysResponse)
async def update_api_keys(
    api_keys: UserAPIKeysUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """Update user's API keys."""
    if api_keys.openai_api_key is not None:
        user.openai_api_key = api_keys.openai_api_key

    if api_keys.anthropic_api_key is not None:
        user.anthropic_api_key = api_keys.anthropic_api_key

    await session.commit()

    return UserAPIKeysResponse(
        openai_api_key_set=bool(user.openai_api_key),
        anthropic_api_key_set=bool(user.anthropic_api_key)
    )