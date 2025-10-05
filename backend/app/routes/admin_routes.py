"""Admin routes for user management and system administration."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import User, get_async_session
from app.users import current_active_user
from app.schemas import UserRead

router = APIRouter()


@router.get("/users", response_model=List[UserRead])
async def list_users(
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """List all users (admin only)."""
    # Check if user is superuser
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get all users
    stmt = select(User)
    result = await session.execute(stmt)
    users = result.scalars().all()

    return users


@router.get("/users/stats")
async def user_stats(
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get user statistics (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get user counts
    stmt = select(User)
    result = await session.execute(stmt)
    all_users = result.scalars().all()

    total_users = len(all_users)
    active_users = sum(1 for u in all_users if u.is_active)
    verified_users = sum(1 for u in all_users if u.is_verified)
    superusers = sum(1 for u in all_users if u.is_superuser)

    return {
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "superusers": superusers,
        "inactive_users": total_users - active_users
    }
