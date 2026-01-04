"""
OpenRouter API status routes for checking credit balance.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db import get_db, User
from app.middleware.clerk_auth import ClerkUser, get_current_user_id
from app.services.openrouter_helpers import check_openrouter_balance, estimate_generation_cost


router = APIRouter(prefix="/api/v2/openrouter", tags=["openrouter"])


class BalanceResponse(BaseModel):
    """OpenRouter credit balance information."""
    balance: float
    usage: float
    limit: float
    is_free_tier: bool
    label: str


class CostEstimateResponse(BaseModel):
    """Cost estimate for a generation type."""
    min_cost: float
    typical_cost: float
    max_cost: float
    currency: str
    details: str


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    user: ClerkUser = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Check OpenRouter credit balance for the current user.
    
    Returns remaining credits, usage, and limits.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.clerk_user_id == user.user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not db_user.openrouter_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key not configured"
        )
    
    # Check balance
    result = await check_openrouter_balance(db_user.openrouter_api_key)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    data = result["data"]
    return BalanceResponse(
        balance=data["balance"],
        usage=data["usage"],
        limit=data["limit"],
        is_free_tier=data["is_free_tier"],
        label=data["label"]
    )


@router.get("/cost-estimate/{generation_type}", response_model=CostEstimateResponse)
async def get_cost_estimate(
    generation_type: str,
    user: ClerkUser = Depends(get_current_user_id)
):
    """
    Get cost estimate for a generation type.
    
    Args:
        generation_type: "podcast", "infographic", or "summary"
    """
    if generation_type not in ["podcast", "infographic", "summary"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid generation type. Must be: podcast, infographic, or summary"
        )
    
    estimate = await estimate_generation_cost(generation_type)
    
    return CostEstimateResponse(**estimate)
