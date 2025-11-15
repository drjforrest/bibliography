"""
Notification service for managing user notifications and @mentions.
"""

import re
import logging
from typing import List, Optional, Set
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import (
    UserNotification,
    User,
    NotificationType,
    NotificationEntityType,
    PaperAnnotation,
    Message,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for handling notifications and user mentions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def extract_mentions(content: str) -> Set[str]:
        """
        Extract @mentions from text content.

        Matches patterns like:
        - @username
        - @user.name
        - @user_name

        Args:
            content: Text content to search for mentions

        Returns:
            Set of mentioned usernames (without @ symbol)
        """
        # Match @username pattern (letters, numbers, dots, underscores, hyphens)
        pattern = r'@([a-zA-Z0-9._-]+)'
        mentions = re.findall(pattern, content)
        return set(mentions)

    async def find_users_by_display_name_or_email(
        self, mentions: Set[str]
    ) -> List[User]:
        """
        Find users who match the mentioned usernames.
        Checks both display_name and email (before @ symbol).

        Args:
            mentions: Set of usernames to look up

        Returns:
            List of matched User objects
        """
        if not mentions:
            return []

        # Build conditions for display_name or email prefix
        conditions = []
        for mention in mentions:
            # Check if display_name matches
            conditions.append(User.display_name.ilike(mention))
            # Check if email starts with mention
            conditions.append(User.email.ilike(f"{mention}%"))

        stmt = select(User).where(or_(*conditions))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_mention_notification(
        self,
        mentioned_user_id: str,
        sender_id: str,
        content: str,
        notification_type: NotificationType,
        entity_type: NotificationEntityType,
        entity_id: int,
    ) -> UserNotification:
        """
        Create a notification for a mentioned user.

        Args:
            mentioned_user_id: User ID of the person being mentioned
            sender_id: User ID of the person who created the mention
            content: Preview content for the notification
            notification_type: Type of notification
            entity_type: Type of entity (annotation/message)
            entity_id: ID of the entity

        Returns:
            Created UserNotification object
        """
        # Don't create notification if user mentions themselves
        if mentioned_user_id == sender_id:
            return None

        notification = UserNotification(
            user_id=mentioned_user_id,
            sender_id=sender_id,
            notification_type=notification_type,
            content=content[:500],  # Limit content length
            related_entity_type=entity_type,
            related_entity_id=entity_id,
            is_read=False,
        )

        self.session.add(notification)
        await self.session.commit()
        await self.session.refresh(notification)

        return notification

    async def process_annotation_mentions(
        self,
        annotation_id: int,
        annotation_content: str,
        author_id: str,
    ) -> List[UserNotification]:
        """
        Process @mentions in an annotation and create notifications.

        Args:
            annotation_id: ID of the annotation
            annotation_content: Content of the annotation
            author_id: User ID of the annotation author

        Returns:
            List of created notifications
        """
        mentions = self.extract_mentions(annotation_content)
        if not mentions:
            return []

        mentioned_users = await self.find_users_by_display_name_or_email(mentions)
        notifications = []

        for user in mentioned_users:
            if str(user.id) != author_id:  # Don't notify if user mentions themselves
                notification = await self.create_mention_notification(
                    mentioned_user_id=str(user.id),
                    sender_id=author_id,
                    content=annotation_content,
                    notification_type=NotificationType.MENTION_IN_ANNOTATION,
                    entity_type=NotificationEntityType.ANNOTATION,
                    entity_id=annotation_id,
                )
                if notification:
                    notifications.append(notification)

        return notifications

    async def process_message_mentions(
        self,
        message_id: int,
        message_content: str,
        author_id: str,
    ) -> List[UserNotification]:
        """
        Process @mentions in a message and create notifications.

        Args:
            message_id: ID of the message
            message_content: Content of the message
            author_id: User ID of the message author

        Returns:
            List of created notifications
        """
        mentions = self.extract_mentions(message_content)
        if not mentions:
            return []

        mentioned_users = await self.find_users_by_display_name_or_email(mentions)
        notifications = []

        for user in mentioned_users:
            if str(user.id) != author_id:  # Don't notify if user mentions themselves
                notification = await self.create_mention_notification(
                    mentioned_user_id=str(user.id),
                    sender_id=author_id,
                    content=message_content,
                    notification_type=NotificationType.MENTION_IN_MESSAGE,
                    entity_type=NotificationEntityType.MESSAGE,
                    entity_id=message_id,
                )
                if notification:
                    notifications.append(notification)

        return notifications

    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserNotification]:
        """
        Get notifications for a user.

        Args:
            user_id: User ID to get notifications for
            unread_only: If True, only return unread notifications
            limit: Maximum number of notifications to return
            offset: Offset for pagination

        Returns:
            List of UserNotification objects
        """
        conditions = [UserNotification.user_id == user_id]

        if unread_only:
            conditions.append(UserNotification.is_read == False)

        stmt = (
            select(UserNotification)
            .where(and_(*conditions))
            .order_by(desc(UserNotification.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_read(self, notification_id: int, user_id: str) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: ID of the notification
            user_id: User ID (for authorization check)

        Returns:
            True if successful, False if notification not found or unauthorized
        """
        stmt = select(UserNotification).where(
            and_(
                UserNotification.id == notification_id,
                UserNotification.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        notification = result.scalar_one_or_none()

        if not notification:
            return False

        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await self.session.commit()

        return True

    async def mark_all_as_read(self, user_id: str) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        stmt = select(UserNotification).where(
            and_(
                UserNotification.user_id == user_id,
                UserNotification.is_read == False,
            )
        )
        result = await self.session.execute(stmt)
        notifications = result.scalars().all()

        count = 0
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            count += 1

        await self.session.commit()
        return count

    async def get_unread_count(self, user_id: str) -> int:
        """
        Get count of unread notifications for a user.

        Args:
            user_id: User ID

        Returns:
            Number of unread notifications
        """
        from sqlalchemy import func

        stmt = select(func.count(UserNotification.id)).where(
            and_(
                UserNotification.user_id == user_id,
                UserNotification.is_read == False,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
