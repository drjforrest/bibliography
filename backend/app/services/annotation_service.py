import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import PaperAnnotation, ScientificPaper, User
from app.schemas.papers import AnnotationCreate, AnnotationUpdate

logger = logging.getLogger(__name__)


class AnnotationService:
    """Service for managing user-attributed annotations on scientific papers."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_annotation(
        self,
        paper_id: int,
        user_id: str,
        annotation_data: AnnotationCreate
    ) -> PaperAnnotation:
        """
        Create a new annotation for a paper.
        
        Args:
            paper_id: ID of the paper to annotate
            user_id: ID of the user creating the annotation
            annotation_data: Annotation data
            
        Returns:
            Created PaperAnnotation object
        """
        # Verify paper exists
        paper_stmt = select(ScientificPaper).where(ScientificPaper.id == paper_id)
        paper_result = await self.session.execute(paper_stmt)
        paper = paper_result.scalar_one_or_none()
        
        if not paper:
            raise ValueError(f"Paper with ID {paper_id} not found")
        
        # Create annotation
        annotation = PaperAnnotation(
            content=annotation_data.content,
            annotation_type=annotation_data.annotation_type,
            page_number=annotation_data.page_number,
            x_coordinate=annotation_data.x_coordinate,
            y_coordinate=annotation_data.y_coordinate,
            width=annotation_data.width,
            height=annotation_data.height,
            color=annotation_data.color,
            is_private=annotation_data.is_private,
            paper_id=paper_id,
            user_id=user_id
        )
        
        self.session.add(annotation)
        await self.session.commit()
        await self.session.refresh(annotation)
        
        logger.info(f"Created annotation {annotation.id} for paper {paper_id} by user {user_id}")
        return annotation
    
    async def get_annotation(self, annotation_id: int, user_id: str) -> Optional[PaperAnnotation]:
        """
        Get an annotation by ID, with access control.
        
        Args:
            annotation_id: ID of the annotation
            user_id: ID of the requesting user
            
        Returns:
            PaperAnnotation object if found and accessible, None otherwise
        """
        stmt = select(PaperAnnotation).options(
            joinedload(PaperAnnotation.user)
        ).where(
            and_(
                PaperAnnotation.id == annotation_id,
                or_(
                    PaperAnnotation.user_id == user_id,  # User's own annotation
                    PaperAnnotation.is_private == False  # Public annotation
                )
            )
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_paper_annotations(
        self,
        paper_id: int,
        user_id: str,
        include_private: bool = True
    ) -> List[PaperAnnotation]:
        """
        Get all annotations for a paper, respecting privacy settings.
        
        Args:
            paper_id: ID of the paper
            user_id: ID of the requesting user
            include_private: Whether to include private annotations (only user's own)
            
        Returns:
            List of accessible PaperAnnotation objects
        """
        stmt = select(PaperAnnotation).options(
            joinedload(PaperAnnotation.user)
        ).where(PaperAnnotation.paper_id == paper_id)
        
        if include_private:
            # Show all public annotations + user's own private annotations
            stmt = stmt.where(
                or_(
                    PaperAnnotation.is_private == False,  # Public annotations
                    PaperAnnotation.user_id == user_id    # User's own annotations
                )
            )
        else:
            # Only public annotations
            stmt = stmt.where(PaperAnnotation.is_private == False)
        
        stmt = stmt.order_by(PaperAnnotation.created_at.desc())
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_user_annotations(
        self,
        user_id: str,
        paper_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[PaperAnnotation]:
        """
        Get all annotations by a specific user.
        
        Args:
            user_id: ID of the user
            paper_id: Optional paper ID to filter by
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of PaperAnnotation objects
        """
        stmt = select(PaperAnnotation).options(
            joinedload(PaperAnnotation.paper),
            joinedload(PaperAnnotation.user)
        ).where(PaperAnnotation.user_id == user_id)
        
        if paper_id:
            stmt = stmt.where(PaperAnnotation.paper_id == paper_id)
        
        stmt = stmt.order_by(PaperAnnotation.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_annotation(
        self,
        annotation_id: int,
        user_id: str,
        update_data: AnnotationUpdate
    ) -> Optional[PaperAnnotation]:
        """
        Update an annotation. Only the owner can update their annotations.
        
        Args:
            annotation_id: ID of the annotation to update
            user_id: ID of the requesting user
            update_data: Updated annotation data
            
        Returns:
            Updated PaperAnnotation object if successful, None otherwise
        """
        # Get annotation and verify ownership
        stmt = select(PaperAnnotation).where(
            and_(
                PaperAnnotation.id == annotation_id,
                PaperAnnotation.user_id == user_id
            )
        )
        
        result = await self.session.execute(stmt)
        annotation = result.scalar_one_or_none()
        
        if not annotation:
            return None
        
        # Update fields that were provided
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(annotation, field, value)
        
        await self.session.commit()
        await self.session.refresh(annotation)
        
        logger.info(f"Updated annotation {annotation_id} by user {user_id}")
        return annotation
    
    async def delete_annotation(self, annotation_id: int, user_id: str) -> bool:
        """
        Delete an annotation. Only the owner can delete their annotations.
        
        Args:
            annotation_id: ID of the annotation to delete
            user_id: ID of the requesting user
            
        Returns:
            True if deleted successfully, False otherwise
        """
        # Get annotation and verify ownership
        stmt = select(PaperAnnotation).where(
            and_(
                PaperAnnotation.id == annotation_id,
                PaperAnnotation.user_id == user_id
            )
        )
        
        result = await self.session.execute(stmt)
        annotation = result.scalar_one_or_none()
        
        if not annotation:
            return False
        
        await self.session.delete(annotation)
        await self.session.commit()
        
        logger.info(f"Deleted annotation {annotation_id} by user {user_id}")
        return True
    
    async def get_annotation_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get annotation statistics.
        
        Args:
            user_id: Optional user ID to get stats for specific user
            
        Returns:
            Dictionary with annotation statistics
        """
        from sqlalchemy import func
        
        base_stmt = select(func.count(PaperAnnotation.id))
        
        if user_id:
            base_stmt = base_stmt.where(PaperAnnotation.user_id == user_id)
        
        # Total annotations
        total_result = await self.session.execute(base_stmt)
        total_annotations = total_result.scalar()
        
        # Annotations by type
        type_stmt = select(
            PaperAnnotation.annotation_type,
            func.count(PaperAnnotation.id)
        ).group_by(PaperAnnotation.annotation_type)
        
        if user_id:
            type_stmt = type_stmt.where(PaperAnnotation.user_id == user_id)
        
        type_result = await self.session.execute(type_stmt)
        annotations_by_type = dict(type_result.fetchall())
        
        # Privacy breakdown
        privacy_stmt = select(
            PaperAnnotation.is_private,
            func.count(PaperAnnotation.id)
        ).group_by(PaperAnnotation.is_private)
        
        if user_id:
            privacy_stmt = privacy_stmt.where(PaperAnnotation.user_id == user_id)
        
        privacy_result = await self.session.execute(privacy_stmt)
        privacy_breakdown = dict(privacy_result.fetchall())
        
        return {
            'total_annotations': total_annotations,
            'annotations_by_type': annotations_by_type,
            'privacy_breakdown': {
                'private': privacy_breakdown.get(True, 0),
                'public': privacy_breakdown.get(False, 0)
            }
        }
    
    async def search_annotations(
        self,
        query: str,
        user_id: str,
        paper_id: Optional[int] = None,
        annotation_type: Optional[str] = None,
        limit: int = 20
    ) -> List[PaperAnnotation]:
        """
        Search annotations by content.
        
        Args:
            query: Search query string
            user_id: ID of the requesting user
            paper_id: Optional paper ID to filter by
            annotation_type: Optional annotation type to filter by
            limit: Maximum number of results
            
        Returns:
            List of matching PaperAnnotation objects
        """
        stmt = select(PaperAnnotation).options(
            joinedload(PaperAnnotation.paper),
            joinedload(PaperAnnotation.user)
        ).where(
            and_(
                PaperAnnotation.content.ilike(f'%{query}%'),
                or_(
                    PaperAnnotation.is_private == False,  # Public annotations
                    PaperAnnotation.user_id == user_id    # User's own annotations
                )
            )
        )
        
        if paper_id:
            stmt = stmt.where(PaperAnnotation.paper_id == paper_id)
        
        if annotation_type:
            stmt = stmt.where(PaperAnnotation.annotation_type == annotation_type)
        
        stmt = stmt.order_by(PaperAnnotation.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def toggle_annotation_privacy(
        self,
        annotation_id: int,
        user_id: str
    ) -> Optional[PaperAnnotation]:
        """
        Toggle the privacy setting of an annotation.
        
        Args:
            annotation_id: ID of the annotation
            user_id: ID of the requesting user (must be owner)
            
        Returns:
            Updated PaperAnnotation object if successful, None otherwise
        """
        stmt = select(PaperAnnotation).where(
            and_(
                PaperAnnotation.id == annotation_id,
                PaperAnnotation.user_id == user_id
            )
        )
        
        result = await self.session.execute(stmt)
        annotation = result.scalar_one_or_none()
        
        if not annotation:
            return None
        
        annotation.is_private = not annotation.is_private
        await self.session.commit()
        await self.session.refresh(annotation)
        
        logger.info(f"Toggled privacy for annotation {annotation_id} by user {user_id} to {'private' if annotation.is_private else 'public'}")
        return annotation