from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    """Request schema for semantic search."""
    query: str = Field(..., min_length=1, description="Search query")
    search_space_id: Optional[int] = Field(None, description="Search space to filter by")
    search_type: str = Field("hybrid", regex="^(semantic|keyword|hybrid)$", description="Type of search to perform")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Minimum extraction confidence score")
    include_abstracts: bool = Field(True, description="Whether to include abstracts in results")


class SearchInsights(BaseModel):
    """Search insights and analytics."""
    total_papers: int
    avg_confidence: float
    avg_search_score: float
    top_journals: List[Dict[str, Any]] = []
    publication_years: List[Dict[str, Any]] = []
    top_authors: List[Dict[str, Any]] = []
    subject_areas: List[Dict[str, Any]] = []


class PaperInfo(BaseModel):
    """Enhanced paper information."""
    id: int
    title: Optional[str]
    authors: List[str] = []
    journal: Optional[str]
    publication_year: Optional[int]
    doi: Optional[str]
    abstract: Optional[str]
    keywords: List[str] = []
    subject_areas: List[str] = []
    confidence_score: Optional[float]
    citation_count: Optional[int]
    is_open_access: Optional[bool]


class SearchResult(BaseModel):
    """Enhanced search result with paper information."""
    document_id: int
    title: str
    content: Optional[str]
    document_type: Optional[str]
    metadata: Optional[Dict[str, Any]]
    score: float
    search_space_id: int
    paper_confidence: float
    paper_info: Optional[PaperInfo]


class SemanticSearchResponse(BaseModel):
    """Response schema for semantic search."""
    query: str
    search_type: str
    total_results: int
    results: List[SearchResult]
    insights: SearchInsights
    search_metadata: Dict[str, Any]


class SimilarPapersResponse(BaseModel):
    """Response schema for similar papers search."""
    reference_paper_id: int
    similar_papers: List[SearchResult]
    total_found: int


class SearchSuggestionsResponse(BaseModel):
    """Response schema for search suggestions."""
    query: str
    suggestions: List[str]
    total_suggestions: int