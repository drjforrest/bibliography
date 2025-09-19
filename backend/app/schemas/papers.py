from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class PaperResponse(BaseModel):
    """Response schema for scientific paper data."""
    id: int
    title: Optional[str]
    authors: List[str] = []
    journal: Optional[str]
    volume: Optional[str]
    issue: Optional[str]
    pages: Optional[str]
    publication_date: Optional[datetime]
    publication_year: Optional[int]
    doi: Optional[str]
    pmid: Optional[str]
    arxiv_id: Optional[str]
    abstract: Optional[str]
    keywords: List[str] = []
    subject_areas: List[str] = []
    tags: List[str] = []
    confidence_score: Optional[float]
    is_open_access: Optional[bool]
    processing_status: str
    file_size: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaperListResponse(BaseModel):
    """Response schema for paginated paper lists."""
    papers: List[PaperResponse]
    total: int
    limit: int
    offset: int


class PaperSearchRequest(BaseModel):
    """Request schema for paper search."""
    query: str
    search_space_id: Optional[int] = None
    limit: int = 20


class PaperUploadResponse(BaseModel):
    """Response schema for paper upload."""
    status: str
    paper_id: Optional[int] = None
    title: Optional[str] = None
    authors: List[str] = []
    stored_path: Optional[str] = None
    extraction_confidence: Optional[float] = None
    error: Optional[str] = None
    message: Optional[str] = None


class CitationRequest(BaseModel):
    """Request schema for citation formatting."""
    style: str = "apa"  # apa, mla, chicago, ieee, harvard, bibtex


class CitationResponse(BaseModel):
    """Response schema for formatted citations."""
    citation: str
    style: str
    paper_id: int


class StorageStatsResponse(BaseModel):
    """Response schema for storage statistics."""
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    storage_root: str
    total_papers_db: int
    papers_by_status: Dict[str, int]


class WatcherStatusResponse(BaseModel):
    """Response schema for folder watcher status."""
    is_running: bool
    watched_folder: str
    folder_exists: bool
    pdf_count: int


# Annotation schemas
class AnnotationCreate(BaseModel):
    """Schema for creating a new annotation."""
    content: str
    annotation_type: str = "note"  # note, highlight, bookmark
    page_number: Optional[int] = None
    x_coordinate: Optional[float] = None
    y_coordinate: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    color: Optional[str] = None
    is_private: bool = True


class AnnotationUpdate(BaseModel):
    """Schema for updating an annotation."""
    content: Optional[str] = None
    annotation_type: Optional[str] = None
    page_number: Optional[int] = None
    x_coordinate: Optional[float] = None
    y_coordinate: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    color: Optional[str] = None
    is_private: Optional[bool] = None


class AnnotationResponse(BaseModel):
    """Response schema for annotation data."""
    id: int
    content: str
    annotation_type: str
    page_number: Optional[int]
    x_coordinate: Optional[float]
    y_coordinate: Optional[float]
    width: Optional[float]
    height: Optional[float]
    color: Optional[str]
    is_private: bool
    paper_id: int
    user_id: str
    created_at: datetime
    
    # User information for team context
    user_email: Optional[str] = None  # Can be populated via join
    
    class Config:
        from_attributes = True


class AnnotationListResponse(BaseModel):
    """Response schema for annotation lists."""
    annotations: List[AnnotationResponse]
    total: int


class PaperWithAnnotationsResponse(BaseModel):
    """Response schema for paper with its annotations."""
    paper: PaperResponse
    annotations: List[AnnotationResponse]
    user_can_annotate: bool = True