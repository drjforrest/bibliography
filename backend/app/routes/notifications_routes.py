from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.db import get_async_session, User
from app.services.notification_service import NotificationService
from app.users import current_active_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    """Response model for a single notification"""
    id: int
    notification_type: str
    content: str
    related_entity_type: str | None
    related_entity_id: int | None
    is_read: bool
    created_at: datetime
    read_at: datetime | None
    sender: dict | None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Response model for list of notifications"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """Response model for unread count"""
    unread_count: int


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get notifications for the current user.
    """
    notification_service = NotificationService(session)

    notifications = await notification_service.get_user_notifications(
        user_id=str(user.id),
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )

    unread_count = await notification_service.get_unread_count(str(user.id))

    # Convert to response format
    notification_responses = []
    for notif in notifications:
        sender_data = None
        if notif.sender:
            sender_data = {
                "id": str(notif.sender.id),
                "email": notif.sender.email,
                "display_name": notif.sender.display_name,
                "avatar_url": notif.sender.avatar_url,
            }

        notification_responses.append(
            NotificationResponse(
                id=notif.id,
                notification_type=notif.notification_type.value,
                content=notif.content,
                related_entity_type=notif.related_entity_type.value if notif.related_entity_type else None,
                related_entity_id=notif.related_entity_id,
                is_read=notif.is_read,
                created_at=notif.created_at,
                read_at=notif.read_at,
                sender=sender_data,
            )
        )

    return NotificationListResponse(
        notifications=notification_responses,
        total=len(notifications),
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get count of unread notifications for the current user.
    """
    notification_service = NotificationService(session)
    unread_count = await notification_service.get_unread_count(str(user.id))

    return UnreadCountResponse(unread_count=unread_count)


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Mark a specific notification as read.
    """
    notification_service = NotificationService(session)
    success = await notification_service.mark_as_read(notification_id, str(user.id))

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Notification not found or not authorized"
        )

    return {"message": "Notification marked as read", "notification_id": notification_id}


@router.post("/mark-all-read")
async def mark_all_notifications_as_read(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Mark all notifications as read for the current user.
    """
    notification_service = NotificationService(session)
    count = await notification_service.mark_all_as_read(str(user.id))

    return {"message": f"{count} notifications marked as read", "count": count}
