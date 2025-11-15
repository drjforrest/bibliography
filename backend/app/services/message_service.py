from typing import List, Optional
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import Message, MessageTopic, User
from app.schemas.messages import MessageCreate, MessageTopicCreate, MessageTopicUpdate


class MessageService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Topic methods
    async def create_topic(
        self, user_id: str, topic_data: MessageTopicCreate
    ) -> MessageTopic:
        """Create a new message topic for a user."""
        topic = MessageTopic(
            name=topic_data.name,
            icon=topic_data.icon,
            description=topic_data.description,
            user_id=user_id,
        )

        self.session.add(topic)
        await self.session.commit()
        await self.session.refresh(topic)
        return topic

    async def get_topic_by_id(
        self, topic_id: int, user_id: str
    ) -> Optional[MessageTopic]:
        """Get a topic by ID (only user's own topics)."""
        stmt = select(MessageTopic).where(
            and_(MessageTopic.id == topic_id, MessageTopic.user_id == user_id)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_topics(self, user_id: str) -> List[MessageTopic]:
        """Get all topics for a user."""
        stmt = (
            select(MessageTopic)
            .where(MessageTopic.user_id == user_id)
            .order_by(MessageTopic.name)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_topic(
        self, topic_id: int, user_id: str, update_data: MessageTopicUpdate
    ) -> Optional[MessageTopic]:
        """Update a topic."""
        topic = await self.get_topic_by_id(topic_id, user_id)
        if not topic:
            return None

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(topic, field, value)

        await self.session.commit()
        await self.session.refresh(topic)
        return topic

    async def delete_topic(self, topic_id: int, user_id: str) -> bool:
        """Delete a topic. Messages in the topic will also be deleted due to CASCADE."""
        topic = await self.get_topic_by_id(topic_id, user_id)
        if not topic:
            return False

        await self.session.delete(topic)
        await self.session.commit()
        return True

    async def get_topic_message_count(self, topic_id: int, user_id: str) -> int:
        """Get count of messages in a topic."""
        topic = await self.get_topic_by_id(topic_id, user_id)
        if not topic:
            return 0

        stmt = select(func.count()).select_from(Message).where(Message.topic_id == topic_id)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_topic_last_message_date(
        self, topic_id: int, user_id: str
    ) -> Optional[str]:
        """Get the date of the last message in a topic."""
        topic = await self.get_topic_by_id(topic_id, user_id)
        if not topic:
            return None

        stmt = (
            select(Message.created_at)
            .where(Message.topic_id == topic_id)
            .order_by(desc(Message.created_at))
            .limit(1)
        )

        result = await self.session.execute(stmt)
        last_message = result.scalar_one_or_none()
        return last_message

    # Message methods
    async def create_message(
        self, user_id: str, message_data: MessageCreate
    ) -> Message:
        """Create a new message."""
        # Verify topic exists and belongs to user
        topic = await self.get_topic_by_id(message_data.topic_id, user_id)
        if not topic:
            raise ValueError("Topic not found")

        # Verify parent message exists if specified
        if message_data.parent_id:
            parent = await self.get_message_by_id(message_data.parent_id, user_id)
            if not parent:
                raise ValueError("Parent message not found")
            if parent.topic_id != message_data.topic_id:
                raise ValueError("Parent message must be in the same topic")

        message = Message(
            content=message_data.content,
            topic_id=message_data.topic_id,
            user_id=user_id,
            parent_id=message_data.parent_id,
        )

        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        
        # Load user relationship
        await self.session.refresh(message, ["user"])
        
        return message

    async def get_message_by_id(
        self, message_id: int, user_id: str
    ) -> Optional[Message]:
        """Get a message by ID."""
        stmt = (
            select(Message)
            .options(selectinload(Message.user))
            .where(Message.id == message_id)
        )

        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        # Verify user has access to this message (through the topic)
        if message:
            topic = await self.get_topic_by_id(message.topic_id, user_id)
            if not topic:
                return None

        return message

    async def get_messages_by_topic(
        self, topic_id: int, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Message]:
        """Get all messages in a topic."""
        # Verify topic exists and belongs to user
        topic = await self.get_topic_by_id(topic_id, user_id)
        if not topic:
            return []

        stmt = (
            select(Message)
            .options(selectinload(Message.user))
            .where(Message.topic_id == topic_id)
            .order_by(Message.created_at)
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_message(self, message_id: int, user_id: str) -> bool:
        """Delete a message. Only the message creator can delete it."""
        stmt = select(Message).where(
            and_(Message.id == message_id, Message.user_id == user_id)
        )

        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            return False

        await self.session.delete(message)
        await self.session.commit()
        return True

    async def get_thread(
        self, parent_message_id: int, user_id: str
    ) -> List[Message]:
        """Get all replies to a message."""
        # Verify parent message exists and user has access
        parent = await self.get_message_by_id(parent_message_id, user_id)
        if not parent:
            return []

        stmt = (
            select(Message)
            .options(selectinload(Message.user))
            .where(Message.parent_id == parent_message_id)
            .order_by(Message.created_at)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
