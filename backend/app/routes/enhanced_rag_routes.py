"""
API routes for Enhanced RAG functionality.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session, User
from app.services.enhanced_rag_service import EnhancedRAGService
from app.users import current_active_user

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/api/v1/enhanced-rag", tags=["Enhanced RAG"])


# Pydantic models for requests/responses
class SearchQuery(BaseModel):
    query: str = Field(..., description="Search query")
    search_space_id: Optional[int] = Field(None, description="Optional search space filter")
    limit: int = Field(10, description="Number of results to return", ge=1, le=50)


class QuestionQuery(BaseModel):
    question: str = Field(..., description="Question to ask about the research papers")
    search_space_id: Optional[int] = Field(None, description="Optional search space filter")


class SearchResponse(BaseModel):
    query: str
    search_type: str
    total_results: int
    results: list
    insights: dict
    search_metadata: dict
    error: Optional[str] = None


class QAResponse(BaseModel):
    question: str
    answer: str
    sources: list
    metadata: dict
    error: Optional[str] = None


class StatsResponse(BaseModel):
    status: str
    embedding_model: Optional[str] = None
    llm_model: Optional[str] = None
    vector_store_type: Optional[str] = None
    documents_indexed: int = 0
    error: Optional[str] = None


# Helper function to get RAG service
async def get_rag_service(session: AsyncSession = Depends(get_async_session)) -> EnhancedRAGService:
    """Get Enhanced RAG service instance."""
    return EnhancedRAGService(session)


@router.post("/search", response_model=SearchResponse)
async def enhanced_semantic_search(
    search_query: SearchQuery,
    current_user: User = Depends(current_active_user),
    rag_service: EnhancedRAGService = Depends(get_rag_service)
):
    """
    Perform enhanced semantic search using FAISS vector store.
    
    This endpoint uses the working RAG pipeline with HuggingFace embeddings
    and FAISS vector store for improved search performance.
    """
    try:
        logger.info(f"Enhanced semantic search request from user {current_user.id}")
        
        result = await rag_service.semantic_search(
            query=search_query.query,
            user_id=str(current_user.id),
            search_space_id=search_query.search_space_id,
            limit=search_query.limit
        )
        
        return SearchResponse(**result)
        
    except Exception as e:
        logger.error(f"Enhanced search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/ask", response_model=QAResponse)
async def ask_question(
    question_query: QuestionQuery,
    current_user: User = Depends(current_active_user),
    rag_service: EnhancedRAGService = Depends(get_rag_service)
):
    """
    Ask a question about research papers using RAG.
    
    This endpoint uses the Ollama LLM with retrieval-augmented generation
    to answer questions based on the user's research papers.
    """
    try:
        logger.info(f"Question from user {current_user.id}: {question_query.question[:50]}...")
        
        result = await rag_service.ask_question(
            question=question_query.question,
            user_id=str(current_user.id),
            search_space_id=question_query.search_space_id
        )
        
        return QAResponse(**result)
        
    except Exception as e:
        logger.error(f"Question answering error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question answering failed: {str(e)}"
        )


@router.post("/rebuild-index")
async def rebuild_vector_index(
    search_space_id: Optional[int] = None,
    current_user: User = Depends(current_active_user),
    rag_service: EnhancedRAGService = Depends(get_rag_service)
):
    """
    Rebuild the FAISS vector index from research papers in the database.
    
    This will recreate the vector store using all papers accessible to the user.
    Optionally filter by search space.
    """
    try:
        logger.info(f"Rebuilding vector index for user {current_user.id}")
        
        success = await rag_service.build_vector_store_from_papers(
            user_id=str(current_user.id),
            search_space_id=search_space_id
        )
        
        if success:
            stats = rag_service.get_stats()
            return {
                "message": "Vector index rebuilt successfully",
                "stats": stats
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to rebuild vector index - no papers found or processing error"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Index rebuild error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Index rebuild failed: {str(e)}"
        )


@router.get("/stats", response_model=StatsResponse)
async def get_rag_stats(
    current_user: User = Depends(current_active_user),
    rag_service: EnhancedRAGService = Depends(get_rag_service)
):
    """
    Get statistics about the Enhanced RAG system.
    
    Returns information about the current state of the vector store,
    embedding model, LLM, and indexed documents.
    """
    try:
        stats = rag_service.get_stats()
        return StatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Stats retrieval error: {str(e)}")
        return StatsResponse(
            status="error",
            error=str(e),
            documents_indexed=0
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for Enhanced RAG service.
    """
    try:
        return {
            "status": "healthy",
            "service": "Enhanced RAG",
            "embedding_model": "all-MiniLM-L6-v2",
            "llm_model": "mistral",
            "vector_store": "FAISS"
        }
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service unhealthy: {str(e)}"
        )