from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db import get_async_session, User
from app.services.semantic_search_service import SemanticSearchService
from app.users import current_active_user
from app.schemas.semantic_search import (
    SemanticSearchRequest, SemanticSearchResponse,
    SimilarPapersResponse, SearchSuggestionsResponse
)

router = APIRouter(prefix="/semantic-search", tags=["semantic-search"])


@router.post("/", response_model=SemanticSearchResponse)
async def semantic_search(
    search_request: SemanticSearchRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Perform enhanced semantic search on scientific papers.
    """
    semantic_service = SemanticSearchService(session)
    
    try:
        results = await semantic_service.semantic_paper_search(
            query=search_request.query,
            user_id=str(user.id),
            search_space_id=search_request.search_space_id,
            search_type=search_request.search_type,
            limit=search_request.limit,
            min_confidence=search_request.min_confidence,
            include_abstracts=search_request.include_abstracts
        )
        
        return SemanticSearchResponse(**results)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/similar/{paper_id}", response_model=SimilarPapersResponse)
async def find_similar_papers(
    paper_id: int,
    limit: int = Query(5, le=20),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Find papers similar to a given paper using semantic similarity.
    """
    semantic_service = SemanticSearchService(session)
    
    try:
        similar_papers = await semantic_service.similar_papers_search(
            paper_id=paper_id,
            user_id=str(user.id),
            limit=limit
        )
        
        return SimilarPapersResponse(
            reference_paper_id=paper_id,
            similar_papers=similar_papers,
            total_found=len(similar_papers)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similar papers search failed: {str(e)}")


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    query: str = Query(..., min_length=2),
    search_space_id: Optional[int] = Query(None),
    limit: int = Query(5, le=20),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get search suggestions based on partial query.
    """
    semantic_service = SemanticSearchService(session)
    
    try:
        suggestions = await semantic_service.get_search_suggestions(
            partial_query=query,
            user_id=str(user.id),
            search_space_id=search_space_id,
            limit=limit
        )
        
        return SearchSuggestionsResponse(
            query=query,
            suggestions=suggestions,
            total_suggestions=len(suggestions)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestions failed: {str(e)}")


@router.get("/quick/{query}")
async def quick_search(
    query: str,
    limit: int = Query(5, le=20),
    search_type: str = Query("hybrid", regex="^(semantic|keyword|hybrid)$"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Quick search endpoint for autocomplete and instant results.
    """
    semantic_service = SemanticSearchService(session)
    
    try:
        results = await semantic_service.semantic_paper_search(
            query=query,
            user_id=str(user.id),
            search_type=search_type,
            limit=limit,
            min_confidence=0.0,
            include_abstracts=False  # Skip abstracts for faster response
        )
        
        # Return simplified results for quick search
        simplified_results = []
        for result in results.get("results", []):
            paper_info = result.get("paper_info", {})
            simplified_results.append({
                "id": paper_info.get("id"),
                "title": paper_info.get("title"),
                "authors": paper_info.get("authors", [])[:3],  # Limit authors
                "journal": paper_info.get("journal"),
                "publication_year": paper_info.get("publication_year"),
                "score": result.get("score", 0.0)
            })
        
        return {
            "query": query,
            "results": simplified_results,
            "total_results": len(simplified_results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick search failed: {str(e)}")