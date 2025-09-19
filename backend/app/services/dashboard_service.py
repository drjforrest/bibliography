import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, text, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import (
    ScientificPaper, Document, SearchSpace, User, PaperAnnotation,
    DocumentType
)

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for generating dashboard analytics and database overviews."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user_dashboard(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for a specific user.
        
        Args:
            user_id: User ID to generate dashboard for
            
        Returns:
            Dictionary containing dashboard data
        """
        try:
            # Get basic statistics
            basic_stats = await self._get_user_basic_stats(user_id)
            
            # Get recent activity
            recent_activity = await self._get_recent_activity(user_id)
            
            # Get paper analytics
            paper_analytics = await self._get_paper_analytics(user_id)
            
            # Get search space breakdown
            search_space_breakdown = await self._get_search_space_breakdown(user_id)
            
            # Get annotation stats
            annotation_stats = await self._get_user_annotation_stats(user_id)
            
            # Get quality metrics
            quality_metrics = await self._get_quality_metrics(user_id)
            
            return {
                "user_id": user_id,
                "generated_at": datetime.utcnow().isoformat(),
                "basic_stats": basic_stats,
                "recent_activity": recent_activity,
                "paper_analytics": paper_analytics,
                "search_spaces": search_space_breakdown,
                "annotations": annotation_stats,
                "quality_metrics": quality_metrics
            }
            
        except Exception as e:
            logger.error(f"Error generating user dashboard for {user_id}: {str(e)}")
            raise
    
    async def get_global_dashboard(self) -> Dict[str, Any]:
        """
        Get global dashboard data for system administrators.
        
        Returns:
            Dictionary containing global dashboard data
        """
        try:
            # System-wide statistics
            system_stats = await self._get_system_stats()
            
            # User activity
            user_activity = await self._get_global_user_activity()
            
            # Content analytics
            content_analytics = await self._get_global_content_analytics()
            
            # Processing statistics
            processing_stats = await self._get_processing_stats()
            
            # Storage metrics
            storage_metrics = await self._get_storage_metrics()
            
            return {
                "generated_at": datetime.utcnow().isoformat(),
                "system_stats": system_stats,
                "user_activity": user_activity,
                "content_analytics": content_analytics,
                "processing_stats": processing_stats,
                "storage_metrics": storage_metrics
            }
            
        except Exception as e:
            logger.error(f"Error generating global dashboard: {str(e)}")
            raise
    
    async def _get_user_basic_stats(self, user_id: str) -> Dict[str, Any]:
        """Get basic statistics for a user."""
        # Total papers
        total_papers_stmt = select(func.count(ScientificPaper.id)).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(SearchSpace.user_id == user_id)
        
        total_papers_result = await self.session.execute(total_papers_stmt)
        total_papers = total_papers_result.scalar() or 0
        
        # Total search spaces
        total_spaces_stmt = select(func.count(SearchSpace.id)).where(
            SearchSpace.user_id == user_id
        )
        total_spaces_result = await self.session.execute(total_spaces_stmt)
        total_spaces = total_spaces_result.scalar() or 0
        
        # Total annotations
        total_annotations_stmt = select(func.count(PaperAnnotation.id)).where(
            PaperAnnotation.user_id == user_id
        )
        total_annotations_result = await self.session.execute(total_annotations_stmt)
        total_annotations = total_annotations_result.scalar() or 0
        
        # Papers added this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        papers_this_week_stmt = select(func.count(ScientificPaper.id)).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(
            SearchSpace.user_id == user_id,
            ScientificPaper.created_at >= week_ago
        )
        
        papers_this_week_result = await self.session.execute(papers_this_week_stmt)
        papers_this_week = papers_this_week_result.scalar() or 0
        
        return {
            "total_papers": total_papers,
            "total_search_spaces": total_spaces,
            "total_annotations": total_annotations,
            "papers_added_this_week": papers_this_week,
            "avg_papers_per_space": round(total_papers / total_spaces, 2) if total_spaces > 0 else 0
        }
    
    async def _get_recent_activity(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent user activity."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Recent papers
        recent_papers_stmt = select(
            ScientificPaper.id,
            ScientificPaper.title,
            ScientificPaper.created_at,
            func.literal("paper_added").label("activity_type")
        ).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(
            SearchSpace.user_id == user_id,
            ScientificPaper.created_at >= cutoff_date
        ).order_by(desc(ScientificPaper.created_at)).limit(10)
        
        recent_papers_result = await self.session.execute(recent_papers_stmt)
        recent_papers = recent_papers_result.fetchall()
        
        # Recent annotations
        recent_annotations_stmt = select(
            PaperAnnotation.id,
            PaperAnnotation.content,
            PaperAnnotation.created_at,
            func.literal("annotation_added").label("activity_type")
        ).where(
            PaperAnnotation.user_id == user_id,
            PaperAnnotation.created_at >= cutoff_date
        ).order_by(desc(PaperAnnotation.created_at)).limit(10)
        
        recent_annotations_result = await self.session.execute(recent_annotations_stmt)
        recent_annotations = recent_annotations_result.fetchall()
        
        # Combine and sort activities
        activities = []
        
        for paper in recent_papers:
            activities.append({
                "id": paper.id,
                "type": "paper_added",
                "title": paper.title or "Untitled Paper",
                "timestamp": paper.created_at.isoformat(),
                "description": f"Added paper: {paper.title or 'Untitled'}"
            })
        
        for annotation in recent_annotations:
            activities.append({
                "id": annotation.id,
                "type": "annotation_added",
                "title": annotation.content[:50] + "..." if len(annotation.content) > 50 else annotation.content,
                "timestamp": annotation.created_at.isoformat(),
                "description": f"Added annotation: {annotation.content[:100]}..."
            })
        
        # Sort by timestamp (most recent first)
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return activities[:20]  # Return top 20 activities
    
    async def _get_paper_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get paper analytics for a user."""
        # Papers by publication year
        year_distribution_stmt = select(
            ScientificPaper.publication_year,
            func.count(ScientificPaper.id).label("count")
        ).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(
            SearchSpace.user_id == user_id,
            ScientificPaper.publication_year.isnot(None)
        ).group_by(ScientificPaper.publication_year).order_by(
            desc(ScientificPaper.publication_year)
        ).limit(10)
        
        year_result = await self.session.execute(year_distribution_stmt)
        year_distribution = [
            {"year": year, "count": count} 
            for year, count in year_result.fetchall()
        ]
        
        # Top journals
        journal_distribution_stmt = select(
            ScientificPaper.journal,
            func.count(ScientificPaper.id).label("count")
        ).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(
            SearchSpace.user_id == user_id,
            ScientificPaper.journal.isnot(None)
        ).group_by(ScientificPaper.journal).order_by(
            desc(func.count(ScientificPaper.id))
        ).limit(10)
        
        journal_result = await self.session.execute(journal_distribution_stmt)
        top_journals = [
            {"journal": journal, "count": count}
            for journal, count in journal_result.fetchall()
        ]
        
        # Papers by processing status
        status_distribution_stmt = select(
            ScientificPaper.processing_status,
            func.count(ScientificPaper.id).label("count")
        ).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(
            SearchSpace.user_id == user_id
        ).group_by(ScientificPaper.processing_status)
        
        status_result = await self.session.execute(status_distribution_stmt)
        processing_status = [
            {"status": status, "count": count}
            for status, count in status_result.fetchall()
        ]
        
        # Papers added over time (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        daily_additions_stmt = select(
            func.date(ScientificPaper.created_at).label("date"),
            func.count(ScientificPaper.id).label("count")
        ).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(
            SearchSpace.user_id == user_id,
            ScientificPaper.created_at >= thirty_days_ago
        ).group_by(func.date(ScientificPaper.created_at)).order_by(
            func.date(ScientificPaper.created_at)
        )
        
        daily_result = await self.session.execute(daily_additions_stmt)
        daily_additions = [
            {"date": date.isoformat(), "count": count}
            for date, count in daily_result.fetchall()
        ]
        
        return {
            "year_distribution": year_distribution,
            "top_journals": top_journals,
            "processing_status": processing_status,
            "daily_additions_30d": daily_additions
        }
    
    async def _get_search_space_breakdown(self, user_id: str) -> List[Dict[str, Any]]:
        """Get search space breakdown for a user."""
        spaces_stmt = select(
            SearchSpace.id,
            SearchSpace.name,
            SearchSpace.description,
            SearchSpace.created_at,
            func.count(ScientificPaper.id).label("paper_count")
        ).outerjoin(
            Document, SearchSpace.id == Document.search_space_id
        ).outerjoin(
            ScientificPaper, Document.id == ScientificPaper.document_id
        ).where(
            SearchSpace.user_id == user_id
        ).group_by(
            SearchSpace.id, SearchSpace.name, SearchSpace.description, SearchSpace.created_at
        ).order_by(desc(func.count(ScientificPaper.id)))
        
        spaces_result = await self.session.execute(spaces_stmt)
        spaces = []
        
        for space in spaces_result.fetchall():
            spaces.append({
                "id": space.id,
                "name": space.name,
                "description": space.description,
                "created_at": space.created_at.isoformat(),
                "paper_count": space.paper_count or 0
            })
        
        return spaces
    
    async def _get_user_annotation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get annotation statistics for a user."""
        # Total annotations
        total_annotations_stmt = select(func.count(PaperAnnotation.id)).where(
            PaperAnnotation.user_id == user_id
        )
        total_result = await self.session.execute(total_annotations_stmt)
        total_annotations = total_result.scalar() or 0
        
        # Annotations by type
        type_distribution_stmt = select(
            PaperAnnotation.annotation_type,
            func.count(PaperAnnotation.id).label("count")
        ).where(
            PaperAnnotation.user_id == user_id
        ).group_by(PaperAnnotation.annotation_type)
        
        type_result = await self.session.execute(type_distribution_stmt)
        annotations_by_type = [
            {"type": ann_type, "count": count}
            for ann_type, count in type_result.fetchall()
        ]
        
        # Privacy breakdown
        privacy_stmt = select(
            PaperAnnotation.is_private,
            func.count(PaperAnnotation.id).label("count")
        ).where(
            PaperAnnotation.user_id == user_id
        ).group_by(PaperAnnotation.is_private)
        
        privacy_result = await self.session.execute(privacy_stmt)
        privacy_breakdown = {}
        for is_private, count in privacy_result.fetchall():
            privacy_breakdown["private" if is_private else "public"] = count
        
        return {
            "total_annotations": total_annotations,
            "annotations_by_type": annotations_by_type,
            "privacy_breakdown": privacy_breakdown
        }
    
    async def _get_quality_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get quality metrics for user's papers."""
        # Average confidence score
        avg_confidence_stmt = select(
            func.avg(ScientificPaper.confidence_score)
        ).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(
            SearchSpace.user_id == user_id,
            ScientificPaper.confidence_score.isnot(None)
        )
        
        avg_confidence_result = await self.session.execute(avg_confidence_stmt)
        avg_confidence = avg_confidence_result.scalar() or 0.0
        
        # Papers with DOI
        papers_with_doi_stmt = select(func.count(ScientificPaper.id)).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(
            SearchSpace.user_id == user_id,
            ScientificPaper.doi.isnot(None)
        )
        
        papers_with_doi_result = await self.session.execute(papers_with_doi_stmt)
        papers_with_doi = papers_with_doi_result.scalar() or 0
        
        # Total papers count for percentage calculation
        total_papers_stmt = select(func.count(ScientificPaper.id)).join(
            Document, ScientificPaper.document_id == Document.id
        ).join(
            SearchSpace, Document.search_space_id == SearchSpace.id
        ).where(SearchSpace.user_id == user_id)
        
        total_papers_result = await self.session.execute(total_papers_stmt)
        total_papers = total_papers_result.scalar() or 0
        
        doi_percentage = (papers_with_doi / total_papers * 100) if total_papers > 0 else 0
        
        return {
            "avg_confidence_score": round(float(avg_confidence), 3),
            "papers_with_doi": papers_with_doi,
            "total_papers": total_papers,
            "doi_coverage_percentage": round(doi_percentage, 2)
        }
    
    async def _get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics."""
        # Total users
        total_users_stmt = select(func.count(User.id))
        total_users_result = await self.session.execute(total_users_stmt)
        total_users = total_users_result.scalar() or 0
        
        # Total papers
        total_papers_stmt = select(func.count(ScientificPaper.id))
        total_papers_result = await self.session.execute(total_papers_stmt)
        total_papers = total_papers_result.scalar() or 0
        
        # Total search spaces
        total_spaces_stmt = select(func.count(SearchSpace.id))
        total_spaces_result = await self.session.execute(total_spaces_stmt)
        total_spaces = total_spaces_result.scalar() or 0
        
        # Total annotations
        total_annotations_stmt = select(func.count(PaperAnnotation.id))
        total_annotations_result = await self.session.execute(total_annotations_stmt)
        total_annotations = total_annotations_result.scalar() or 0
        
        return {
            "total_users": total_users,
            "total_papers": total_papers,
            "total_search_spaces": total_spaces,
            "total_annotations": total_annotations,
            "avg_papers_per_user": round(total_papers / total_users, 2) if total_users > 0 else 0
        }
    
    async def _get_global_user_activity(self) -> Dict[str, Any]:
        """Get global user activity metrics."""
        # Active users in last 7 days (users who added papers or annotations)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # This is a simplified approach - in a real system you'd track login activity
        active_users_papers_stmt = select(func.count(func.distinct(SearchSpace.user_id))).join(
            Document, SearchSpace.id == Document.search_space_id
        ).join(
            ScientificPaper, Document.id == ScientificPaper.document_id
        ).where(ScientificPaper.created_at >= week_ago)
        
        active_users_result = await self.session.execute(active_users_papers_stmt)
        active_users = active_users_result.scalar() or 0
        
        return {
            "active_users_7d": active_users,
            # Add more activity metrics here
        }
    
    async def _get_global_content_analytics(self) -> Dict[str, Any]:
        """Get global content analytics."""
        # Most popular journals
        popular_journals_stmt = select(
            ScientificPaper.journal,
            func.count(ScientificPaper.id).label("count")
        ).where(
            ScientificPaper.journal.isnot(None)
        ).group_by(ScientificPaper.journal).order_by(
            desc(func.count(ScientificPaper.id))
        ).limit(10)
        
        journals_result = await self.session.execute(popular_journals_stmt)
        popular_journals = [
            {"journal": journal, "count": count}
            for journal, count in journals_result.fetchall()
        ]
        
        return {
            "popular_journals": popular_journals
        }
    
    async def _get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        # Papers by processing status
        status_stmt = select(
            ScientificPaper.processing_status,
            func.count(ScientificPaper.id).label("count")
        ).group_by(ScientificPaper.processing_status)
        
        status_result = await self.session.execute(status_stmt)
        processing_status = [
            {"status": status, "count": count}
            for status, count in status_result.fetchall()
        ]
        
        # Average confidence score globally
        avg_confidence_stmt = select(func.avg(ScientificPaper.confidence_score)).where(
            ScientificPaper.confidence_score.isnot(None)
        )
        avg_confidence_result = await self.session.execute(avg_confidence_stmt)
        avg_confidence = avg_confidence_result.scalar() or 0.0
        
        return {
            "processing_status_distribution": processing_status,
            "global_avg_confidence": round(float(avg_confidence), 3)
        }
    
    async def _get_storage_metrics(self) -> Dict[str, Any]:
        """Get storage metrics."""
        # Total file size
        total_size_stmt = select(func.sum(ScientificPaper.file_size)).where(
            ScientificPaper.file_size.isnot(None)
        )
        total_size_result = await self.session.execute(total_size_stmt)
        total_size_bytes = total_size_result.scalar() or 0
        
        # Average file size
        avg_size_stmt = select(func.avg(ScientificPaper.file_size)).where(
            ScientificPaper.file_size.isnot(None)
        )
        avg_size_result = await self.session.execute(avg_size_stmt)
        avg_size_bytes = avg_size_result.scalar() or 0
        
        return {
            "total_size_bytes": int(total_size_bytes),
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
            "total_size_gb": round(total_size_bytes / (1024 * 1024 * 1024), 2),
            "avg_file_size_mb": round(float(avg_size_bytes) / (1024 * 1024), 2)
        }