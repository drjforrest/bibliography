from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db import get_async_session, User
from app.services.annotation_service import AnnotationService
from app.users import current_active_user
from app.schemas.papers import (
    AnnotationCreate, AnnotationUpdate, AnnotationResponse,
    AnnotationListResponse, PaperWithAnnotationsResponse
)

router = APIRouter(prefix="/annotations", tags=["annotations"])


@router.post("/", response_model=AnnotationResponse)
async def create_annotation(
    paper_id: int,
    annotation_data: AnnotationCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a new annotation for a paper.
    """
    annotation_service = AnnotationService(session)
    
    try:
        annotation = await annotation_service.create_annotation(
            paper_id=paper_id,
            user_id=str(user.id),
            annotation_data=annotation_data
        )
        
        return AnnotationResponse.from_orm(annotation)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{annotation_id}", response_model=AnnotationResponse)
async def get_annotation(
    annotation_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get a specific annotation by ID.
    """
    annotation_service = AnnotationService(session)
    annotation = await annotation_service.get_annotation(annotation_id, str(user.id))
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found or not accessible")
    
    return AnnotationResponse.from_orm(annotation)


@router.get("/paper/{paper_id}", response_model=AnnotationListResponse)
async def get_paper_annotations(
    paper_id: int,
    include_private: bool = Query(True),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get all annotations for a specific paper.
    """
    annotation_service = AnnotationService(session)
    annotations = await annotation_service.get_paper_annotations(
        paper_id=paper_id,
        user_id=str(user.id),
        include_private=include_private
    )
    
    return AnnotationListResponse(
        annotations=[AnnotationResponse.from_orm(ann) for ann in annotations],
        total=len(annotations)
    )


@router.get("/user/me", response_model=AnnotationListResponse)
async def get_my_annotations(
    paper_id: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get all annotations by the current user.
    """
    annotation_service = AnnotationService(session)
    annotations = await annotation_service.get_user_annotations(
        user_id=str(user.id),
        paper_id=paper_id,
        limit=limit,
        offset=offset
    )
    
    return AnnotationListResponse(
        annotations=[AnnotationResponse.from_orm(ann) for ann in annotations],
        total=len(annotations)
    )


@router.put("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: int,
    update_data: AnnotationUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update an annotation. Only the owner can update their annotations.
    """
    annotation_service = AnnotationService(session)
    annotation = await annotation_service.update_annotation(
        annotation_id=annotation_id,
        user_id=str(user.id),
        update_data=update_data
    )
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found or not authorized")
    
    return AnnotationResponse.from_orm(annotation)


@router.delete("/{annotation_id}")
async def delete_annotation(
    annotation_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Delete an annotation. Only the owner can delete their annotations.
    """
    annotation_service = AnnotationService(session)
    success = await annotation_service.delete_annotation(
        annotation_id=annotation_id,
        user_id=str(user.id)
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Annotation not found or not authorized")
    
    return {"message": "Annotation deleted successfully", "annotation_id": annotation_id}


@router.post("/search", response_model=AnnotationListResponse)
async def search_annotations(
    query: str,
    paper_id: Optional[int] = Query(None),
    annotation_type: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Search annotations by content.
    """
    annotation_service = AnnotationService(session)
    annotations = await annotation_service.search_annotations(
        query=query,
        user_id=str(user.id),
        paper_id=paper_id,
        annotation_type=annotation_type,
        limit=limit
    )
    
    return AnnotationListResponse(
        annotations=[AnnotationResponse.from_orm(ann) for ann in annotations],
        total=len(annotations)
    )


@router.post("/{annotation_id}/toggle-privacy", response_model=AnnotationResponse)
async def toggle_annotation_privacy(
    annotation_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Toggle the privacy setting of an annotation (private/public).
    """
    annotation_service = AnnotationService(session)
    annotation = await annotation_service.toggle_annotation_privacy(
        annotation_id=annotation_id,
        user_id=str(user.id)
    )
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found or not authorized")
    
    return AnnotationResponse.from_orm(annotation)


@router.get("/stats/me")
async def get_my_annotation_stats(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get annotation statistics for the current user.
    """
    annotation_service = AnnotationService(session)
    stats = await annotation_service.get_annotation_stats(user_id=str(user.id))
    return stats


@router.get("/stats/global")
async def get_global_annotation_stats(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get global annotation statistics (all public annotations).
    """
    annotation_service = AnnotationService(session)
    stats = await annotation_service.get_annotation_stats()
    return stats