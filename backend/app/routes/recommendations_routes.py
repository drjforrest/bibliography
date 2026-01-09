"""
API routes for paper recommendations using Semantic Scholar.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.middleware.clerk_auth import require_clerk_auth, User
from app.services.semantic_scholar_service import create_semantic_scholar_service
from app.services.paper_manager import PaperManagerService
from app.schemas.recommendations import (
    RecommendationsResponse,
    RecommendedPaper,
    SearchResponse
)
from app.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


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
    try:
        # Get paper from library
        paper_manager = PaperManagerService(session)
        paper = await paper_manager.get_paper_by_id(paper_id)

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Get Semantic Scholar service
        api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
        s2_service = create_semantic_scholar_service(api_key=api_key)

        # Get recommendations
        logger.info(f"Getting recommendations for paper {paper_id}: {paper.title[:60]}...")

        result = await s2_service.get_recommendations_for_library_paper(
            paper={
                "doi": paper.doi,
                "title": paper.title,
            },
            limit=limit
        )

        recommendations = [
            RecommendedPaper(**rec)
            for rec in result.get("recommendedPapers", [])
        ]

        return RecommendationsResponse(
            source_paper_id=paper_id,
            source_paper_title=paper.title,
            recommendations=recommendations,
            total_found=len(recommendations)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendations: {str(e)}"
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
    try:
        # Get Semantic Scholar service
        api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
        s2_service = create_semantic_scholar_service(api_key=api_key)

        # Search
        logger.info(f"Searching Semantic Scholar: '{query}'")
        result = await s2_service.search_papers(query=query, limit=limit)

        return SearchResponse(**result)

    except Exception as e:
        logger.error(f"Error searching Semantic Scholar: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/health")
async def check_semantic_scholar_health():
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
            "test_search_results": result.get("total", 0)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "api_key_configured": bool(getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None))
        }
