"""
Migration script to add the user_notifications table for @mentions and notifications.

This script creates the user_notifications table for tracking user notifications
and mentions in annotations and messages.

Usage:
    python backend/scripts/add_notifications_table.py
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db import engine


async def add_notifications_table():
    """Add the user_notifications table to the database."""
    print("Starting migration: Adding user_notifications table...")

    async with engine.begin() as conn:
        # Check if table already exists
        result = await conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'user_notifications'
                )
                """
            )
        )
        table_exists = result.scalar()

        if table_exists:
            print("✓ user_notifications table already exists")
            return

        print("Creating notification type enums...")
        # Create enums for notification types
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE notificationtype AS ENUM (
                        'MENTION_IN_ANNOTATION',
                        'MENTION_IN_MESSAGE',
                        'NEW_ANNOTATION_ON_PAPER'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )

        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE notificationentitytype AS ENUM (
                        'ANNOTATION',
                        'MESSAGE',
                        'PAPER'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )
        print("✓ Enums created")

        print("Creating user_notifications table...")
        await conn.execute(
            text(
                """
                CREATE TABLE user_notifications (
                    id SERIAL PRIMARY KEY,
                    user_id UUID NOT NULL,
                    sender_id UUID,
                    notification_type notificationtype NOT NULL,
                    content TEXT NOT NULL,
                    related_entity_type notificationentitytype,
                    related_entity_id INTEGER,
                    is_read BOOLEAN NOT NULL DEFAULT FALSE,
                    read_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
                    FOREIGN KEY (sender_id) REFERENCES "user"(id) ON DELETE SET NULL
                )
                """
            )
        )
        print("✓ user_notifications table created")

        # Create indexes for better performance
        print("Creating indexes...")
        await conn.execute(
            text(
                """
                CREATE INDEX idx_user_notifications_user_id
                ON user_notifications(user_id)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX idx_user_notifications_is_read
                ON user_notifications(is_read)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX idx_user_notifications_created_at
                ON user_notifications(created_at)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX idx_user_notifications_type
                ON user_notifications(notification_type)
                """
            )
        )
        print("✓ Indexes created")

    print("\n✅ Migration complete!")
    print("User notifications table has been successfully added to the database.")


async def main():
    try:
        await add_notifications_table()
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
