"""Schemas for paper recommendations."""

from typing import List, Optional
from pydantic import BaseModel, Field


class Author(BaseModel):
    """Author information from Semantic Scholar."""
    authorId: Optional[str] = None
    name: str


class OpenAccessPdf(BaseModel):
    """Open access PDF information."""
    url: Optional[str] = None
    status: Optional[str] = None


class RecommendedPaper(BaseModel):
    """A recommended paper from Semantic Scholar."""
    paperId: str
    title: str
    url: Optional[str] = None
    abstract: Optional[str] = None
    year: Optional[int] = None
    authors: Optional[List[Author]] = []
    citationCount: Optional[int] = 0
    isOpenAccess: Optional[bool] = False
    openAccessPdf: Optional[OpenAccessPdf] = None

    class Config:
        from_attributes = True


class RecommendationsResponse(BaseModel):
    """Response for paper recommendations request."""
    source_paper_id: int
    source_paper_title: str
    recommendations: List[RecommendedPaper]
    total_found: int

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    """Paper search result from Semantic Scholar."""
    paperId: str
    title: str
    url: Optional[str] = None
    abstract: Optional[str] = None
    year: Optional[int] = None
    authors: Optional[List[Author]] = []


class SearchResponse(BaseModel):
    """Response for paper search request."""
    total: int
    offset: int
    data: List[SearchResult]

    class Config:
        from_attributes = True
