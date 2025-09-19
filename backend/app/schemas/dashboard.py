from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class BasicStats(BaseModel):
    """Basic user statistics."""
    total_papers: int
    total_search_spaces: int
    total_annotations: int
    papers_added_this_week: int
    avg_papers_per_space: float


class ActivityItem(BaseModel):
    """Single activity item."""
    id: int
    type: str
    title: str
    timestamp: str
    description: str


class PaperAnalytics(BaseModel):
    """Paper analytics data."""
    year_distribution: List[Dict[str, Any]]
    top_journals: List[Dict[str, Any]]
    processing_status: List[Dict[str, Any]]
    daily_additions_30d: List[Dict[str, Any]]


class SearchSpaceInfo(BaseModel):
    """Search space information."""
    id: int
    name: str
    description: Optional[str]
    created_at: str
    paper_count: int


class AnnotationStats(BaseModel):
    """Annotation statistics."""
    total_annotations: int
    annotations_by_type: List[Dict[str, Any]]
    privacy_breakdown: Dict[str, int]


class QualityMetrics(BaseModel):
    """Quality metrics for papers."""
    avg_confidence_score: float
    papers_with_doi: int
    total_papers: int
    doi_coverage_percentage: float


class UserDashboardResponse(BaseModel):
    """Complete user dashboard response."""
    user_id: str
    generated_at: str
    basic_stats: BasicStats
    recent_activity: List[ActivityItem]
    paper_analytics: PaperAnalytics
    search_spaces: List[SearchSpaceInfo]
    annotations: AnnotationStats
    quality_metrics: QualityMetrics


class SystemStats(BaseModel):
    """System-wide statistics."""
    total_users: int
    total_papers: int
    total_search_spaces: int
    total_annotations: int
    avg_papers_per_user: float


class UserActivity(BaseModel):
    """Global user activity metrics."""
    active_users_7d: int


class ContentAnalytics(BaseModel):
    """Global content analytics."""
    popular_journals: List[Dict[str, Any]]


class ProcessingStats(BaseModel):
    """Processing statistics."""
    processing_status_distribution: List[Dict[str, Any]]
    global_avg_confidence: float


class StorageMetrics(BaseModel):
    """Storage metrics."""
    total_size_bytes: int
    total_size_mb: float
    total_size_gb: float
    avg_file_size_mb: float


class GlobalDashboardResponse(BaseModel):
    """Global dashboard response."""
    generated_at: str
    system_stats: SystemStats
    user_activity: UserActivity
    content_analytics: ContentAnalytics
    processing_stats: ProcessingStats
    storage_metrics: StorageMetrics