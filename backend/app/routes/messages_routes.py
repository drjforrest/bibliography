from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db import get_async_session, User
from app.services.message_service import MessageService
from app.services.notification_service import NotificationService
from app.users import current_active_user
from app.schemas.messages import (
    MessageCreate,
    MessageResponse,
    MessageTopicCreate,
    MessageTopicUpdate,
    MessageTopicResponse,
    UserInfo,
)

router = APIRouter(prefix="/messages", tags=["messages"])


# Topic endpoints
@router.post("/topics/", response_model=MessageTopicResponse, status_code=201)
async def create_topic(
    topic_data: MessageTopicCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new message topic."""
    message_service = MessageService(session)

    try:
        topic = await message_service.create_topic(str(user.id), topic_data)
        return MessageTopicResponse(
            id=topic.id,
            name=topic.name,
            icon=topic.icon,
            description=topic.description,
            user_id=str(topic.user_id),
            created_at=topic.created_at,
            unread_count=0,
            last_message=None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/topics/", response_model=List[MessageTopicResponse])
async def get_topics(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get all message topics for the current user."""
    message_service = MessageService(session)
    topics = await message_service.get_user_topics(str(user.id))

    # Enhance with message counts and last message dates
    topic_responses = []
    for topic in topics:
        # Get message count - for now we'll skip unread count
        last_message = await message_service.get_topic_last_message_date(
            topic.id, str(user.id)
        )

        topic_responses.append(
            MessageTopicResponse(
                id=topic.id,
                name=topic.name,
                icon=topic.icon,
                description=topic.description,
                user_id=str(topic.user_id),
                created_at=topic.created_at,
                unread_count=0,  # TODO: Implement unread tracking
                last_message=last_message,
            )
        )

    return topic_responses


@router.get("/topics/{topic_id}", response_model=MessageTopicResponse)
async def get_topic(
    topic_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific topic by ID."""
    message_service = MessageService(session)
    topic = await message_service.get_topic_by_id(topic_id, str(user.id))

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    last_message = await message_service.get_topic_last_message_date(
        topic.id, str(user.id)
    )

    return MessageTopicResponse(
        id=topic.id,
        name=topic.name,
        icon=topic.icon,
        description=topic.description,
        user_id=str(topic.user_id),
        created_at=topic.created_at,
        unread_count=0,
        last_message=last_message,
    )


@router.put("/topics/{topic_id}", response_model=MessageTopicResponse)
async def update_topic(
    topic_id: int,
    update_data: MessageTopicUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update a topic."""
    message_service = MessageService(session)

    try:
        topic = await message_service.update_topic(topic_id, str(user.id), update_data)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        last_message = await message_service.get_topic_last_message_date(
            topic.id, str(user.id)
        )

        return MessageTopicResponse(
            id=topic.id,
            name=topic.name,
            icon=topic.icon,
            description=topic.description,
            user_id=str(topic.user_id),
            created_at=topic.created_at,
            unread_count=0,
            last_message=last_message,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/topics/{topic_id}")
async def delete_topic(
    topic_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a topic and all its messages."""
    message_service = MessageService(session)

    success = await message_service.delete_topic(topic_id, str(user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Topic not found")

    return {"message": "Topic deleted successfully", "topic_id": topic_id}


# Message endpoints
@router.post("/", response_model=MessageResponse, status_code=201)
async def create_message(
    message_data: MessageCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new message."""
    message_service = MessageService(session)
    notification_service = NotificationService(session)

    try:
        message = await message_service.create_message(str(user.id), message_data)

        # Process @mentions in the message content
        await notification_service.process_message_mentions(
            message_id=message.id,
            message_content=message.content,
            author_id=str(user.id),
        )

        return MessageResponse(
            id=message.id,
            content=message.content,
            topic_id=message.topic_id,
            user_id=str(message.user_id),
            user=UserInfo(
                id=str(message.user.id),
                email=message.user.email,
                display_name=message.user.display_name,
                avatar_url=message.user.avatar_url,
            ),
            created_at=message.created_at,
            parent_id=message.parent_id,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/topics/{topic_id}/messages", response_model=List[MessageResponse])
async def get_messages_by_topic(
    topic_id: int,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get all messages in a topic."""
    message_service = MessageService(session)

    # Verify topic exists and belongs to user
    topic = await message_service.get_topic_by_id(topic_id, str(user.id))
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    messages = await message_service.get_messages_by_topic(
        topic_id, str(user.id), limit, offset
    )

    return [
        MessageResponse(
            id=msg.id,
            content=msg.content,
            topic_id=msg.topic_id,
            user_id=str(msg.user_id),
            user=UserInfo(
                id=str(msg.user.id),
                email=msg.user.email,
                display_name=msg.user.display_name,
                avatar_url=msg.user.avatar_url,
            ),
            created_at=msg.created_at,
            parent_id=msg.parent_id,
        )
        for msg in messages
    ]


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific message by ID."""
    message_service = MessageService(session)
    message = await message_service.get_message_by_id(message_id, str(user.id))

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    return MessageResponse(
        id=message.id,
        content=message.content,
        topic_id=message.topic_id,
        user_id=str(message.user_id),
        user=UserInfo(
            id=str(message.user.id),
            email=message.user.email,
            display_name=message.user.display_name,
            avatar_url=message.user.avatar_url,
        ),
        created_at=message.created_at,
        parent_id=message.parent_id,
    )


@router.delete("/{message_id}")
async def delete_message(
    message_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a message. Only the message creator can delete it."""
    message_service = MessageService(session)

    success = await message_service.delete_message(message_id, str(user.id))
    if not success:
        raise HTTPException(
            status_code=404, detail="Message not found or you don't have permission"
        )

    return {"message": "Message deleted successfully", "message_id": message_id}


@router.get("/{message_id}/thread", response_model=List[MessageResponse])
async def get_thread(
    message_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get all replies to a message."""
    message_service = MessageService(session)

    # Verify parent message exists
    parent = await message_service.get_message_by_id(message_id, str(user.id))
    if not parent:
        raise HTTPException(status_code=404, detail="Message not found")

    replies = await message_service.get_thread(message_id, str(user.id))

    return [
        MessageResponse(
            id=msg.id,
            content=msg.content,
            topic_id=msg.topic_id,
            user_id=str(msg.user_id),
            user=UserInfo(
                id=str(msg.user.id),
                email=msg.user.email,
                display_name=msg.user.display_name,
                avatar_url=msg.user.avatar_url,
            ),
            created_at=msg.created_at,
            parent_id=msg.parent_id,
        )
        for msg in replies
    ]
