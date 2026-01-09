"""
API routes for paper recommendations using Semantic Scholar.
"""

import logging

from app.config import config
from app.db import Document, SearchSpace, get_async_session
from app.middleware.clerk_auth import User, require_clerk_auth
from app.schemas.recommendations import (
    RecommendationsResponse,
    RecommendedPaper,
    SearchResponse,
)
from app.services.paper_manager import PaperManagerService
from app.services.rate_limiter import RateLimiter
from app.services.semantic_scholar_service import (
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW,
    create_semantic_scholar_service,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Initialize rate limiter with constants from semantic_scholar_service
# This enforces per-user rate limits on our recommendations endpoints
rate_limiter = RateLimiter(
    window=RATE_LIMIT_WINDOW,
    max_requests=RATE_LIMIT_MAX_REQUESTS,
)


@router.get("/search", response_model=SearchResponse)
async def search_semantic_scholar(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=100),
    user: User = Depends(require_clerk_auth),
):
    """
    Search Semantic Scholar for papers.

    Args:
        query: Search query string
        limit: Number of results (1-100, default 10)

    Returns:
        Search results from Semantic Scholar
    """
    # Rate limiting: check if user has exceeded request limit
    client_id = str(user.id)
    allowed, remaining, reset_after = rate_limiter.check_rate_limit(client_id)

    if not allowed:
        logger.warning(
            f"Rate limit exceeded for user {user.id}: {remaining} remaining, "
            f"reset in {reset_after}s"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please try again in {reset_after} seconds.",
            headers={
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_after),
            },
        )

    try:
        # Get Semantic Scholar service
        api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
        s2_service = create_semantic_scholar_service(api_key=api_key)

        # Search
        logger.info(
            f"Searching Semantic Scholar: '{query}' (user {user.id}, {remaining} requests remaining)"
        )
        result = await s2_service.search_papers(query=query, limit=limit)

        # Add rate limit headers to response
        response_data = SearchResponse(**result)
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching Semantic Scholar: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Search failed. Please try again later."
        )


@router.get("/{paper_id}", response_model=RecommendationsResponse)
async def get_recommendations_for_paper(
    paper_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get paper recommendations based on a paper in your library.

    Args:
        paper_id: ID of paper in your library
        limit: Number of recommendations (1-100, default 10)

    Returns:
        Recommendations from Semantic Scholar
    """
    # Rate limiting: check if user has exceeded request limit
    client_id = str(user.id)
    allowed, remaining, reset_after = rate_limiter.check_rate_limit(client_id)

    if not allowed:
        logger.warning(
            f"Rate limit exceeded for user {user.id}: {remaining} remaining, "
            f"reset in {reset_after}s"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please try again in {reset_after} seconds.",
            headers={
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_after),
            },
        )

    try:
        # Get paper from library
        paper_manager = PaperManagerService(session)
        paper = await paper_manager.get_paper_by_id(paper_id)

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Verify authorization: check that the paper's document belongs to a SearchSpace owned by the current user
        stmt = (
            select(SearchSpace.user_id)
            .join(Document, Document.search_space_id == SearchSpace.id)
            .where(Document.id == paper.document_id)
        )
        result = await session.execute(stmt)
        search_space_user_id = result.scalar_one_or_none()

        if search_space_user_id is None:
            # This should not happen if data integrity is maintained, but handle gracefully
            raise HTTPException(status_code=404, detail="Paper not found")

        if search_space_user_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")

        # Get Semantic Scholar service
        api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
        s2_service = create_semantic_scholar_service(api_key=api_key)

        # Get recommendations
        logger.info(
            f"Getting recommendations for paper {paper_id}: {paper.title[:60]}... "
            f"(user {user.id}, {remaining} requests remaining)"
        )

        result = await s2_service.get_recommendations_for_library_paper(
            paper={
                "doi": paper.doi,
                "title": paper.title,
            },
            limit=limit,
        )

        recommendations = [
            RecommendedPaper(**rec) for rec in result.get("recommendedPapers", [])
        ]

        return RecommendationsResponse(
            source_paper_id=paper_id,
            source_paper_title=paper.title,
            recommendations=recommendations,
            total_found=len(recommendations),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get recommendations", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get recommendations",
        )


@router.get("/health")
async def check_semantic_scholar_health(
    user: User = Depends(require_clerk_auth),
):
    """
    Check if Semantic Scholar API is accessible.

    Returns:
        Status and configuration info
    """
    try:
        api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
        s2_service = create_semantic_scholar_service(api_key=api_key)

        # Try a simple search to test connectivity
        result = await s2_service.search_papers("machine learning", limit=1)

        return {
            "status": "healthy",
            "api_key_configured": bool(api_key),
            "rate_limit": "1000/5min" if api_key else "100/5min",
            "test_search_results": result.get("total", 0),
        }
    except Exception as e:
        logger.error(f"Error checking Semantic Scholar health: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": "Service unavailable. Please try again later.",
            "api_key_configured": bool(
                getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
            ),
        }
