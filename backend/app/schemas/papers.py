from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, field_validator
from enum import Enum


class LiteratureType(str, Enum):
    """Literature type for room classification."""

    PEER_REVIEWED = "PEER_REVIEWED"
    GREY_LITERATURE = "GREY_LITERATURE"
    NEWS = "NEWS"


class PaperResponse(BaseModel):
    """Response schema for scientific paper data."""

    id: int
    literature_type: str = "PEER_REVIEWED"  # Room classification
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
    summary: Optional[str] = None  # DEVONthink Finder Comment (article summary)
    lay_summary: Optional[str] = None  # LLM-generated accessible summary
    keywords: List[str] = []
    subject_areas: List[str] = []
    tags: List[str] = []
    confidence_score: Optional[float]
    is_open_access: Optional[bool]
    processing_status: str
    file_size: Optional[int]
    created_at: datetime

    # LLM-generated enrichment fields from extraction_metadata
    short_description: Optional[str] = None
    insights: List[str] = []
    citations: Optional[Dict[str, str]] = None  # Dict of citation styles to formatted citations

    @field_validator("keywords", "subject_areas", "tags", "insights", mode="before")
    @classmethod
    def convert_none_to_list(cls, v):
        """Convert None values to empty lists for list fields."""
        return v if v is not None else []

    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to extract summary and title from document relationship."""
        # Get base data from the ORM object
        data = {}
        for field in cls.model_fields:
            if hasattr(obj, field):
                data[field] = getattr(obj, field)
        
        # Fix title for DEVONthink imports
        if hasattr(obj, 'document') and obj.document:
            document = obj.document
            # Use document title if paper title looks incorrect (e.g., all caps journal name)
            if hasattr(document, 'title') and document.title:
                current_title = data.get('title', '')
                if current_title and current_title.isupper() and len(current_title) > 20:
                    data['title'] = document.title
            
            # Extract summary from document_metadata
            if not data.get('summary'):
                if hasattr(document, 'document_metadata') and document.document_metadata:
                    doc_metadata = document.document_metadata
                    if isinstance(doc_metadata, dict) and 'devonthink_description' in doc_metadata:
                        data['summary'] = doc_metadata['devonthink_description']
        
        # Also check extraction_metadata.finder_comment as fallback
        if not data.get('summary') and 'extraction_metadata' in data:
            metadata = data.get('extraction_metadata', {})
            if isinstance(metadata, dict) and 'finder_comment' in metadata:
                data['summary'] = metadata['finder_comment']

        # Extract LLM-generated enrichment fields from extraction_metadata
        if hasattr(obj, 'extraction_metadata') and obj.extraction_metadata:
            metadata = obj.extraction_metadata
            if isinstance(metadata, dict):
                data['short_description'] = metadata.get('short_description')
                # Ensure insights is always a list of strings
                insights_raw = metadata.get('insights', [])
                if isinstance(insights_raw, dict):
                    # If it's a dict, extract values or convert to list
                    if 'insights' in insights_raw:
                        insights_raw = insights_raw['insights']
                    elif isinstance(insights_raw, dict):
                        insights_raw = list(insights_raw.values()) if insights_raw else []
                if not isinstance(insights_raw, list):
                    insights_raw = []
                # Ensure all items are strings
                data['insights'] = [str(item) for item in insights_raw if item]
                data['citations'] = metadata.get('citations', {})

        return cls(**data)

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

    @field_validator("user_id", mode="before")
    @classmethod
    def convert_uuid_to_string(cls, v):
        """Convert UUID objects to string representation."""
        if hasattr(v, '__str__'):
            return str(v)
        return v


class AnnotationListResponse(BaseModel):
    """Response schema for annotation lists."""

    annotations: List[AnnotationResponse]
    total: int


class PaperWithAnnotationsResponse(BaseModel):
    """Response schema for paper with its annotations."""

    paper: PaperResponse
    annotations: List[AnnotationResponse]
    user_can_annotate: bool = True
