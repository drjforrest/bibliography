"""
Migration script to add profile fields to the User table.

This script adds the following fields to the user table:
- display_name: VARCHAR(100) - User's display name
- bio: TEXT - User's bio/description
- avatar_url: VARCHAR(500) - URL to user's avatar image
- openrouter_api_key: VARCHAR - OpenRouter API key for BYOK functionality

It also removes the old openai_api_key and anthropic_api_key columns if they exist.

Usage:
    python backend/scripts/add_user_profile_fields.py
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db import engine


async def add_user_profile_fields():
    """Add profile fields to the user table."""
    print("Starting migration: Adding user profile fields...")

    async with engine.begin() as conn:
        # Check if columns already exist
        result = await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'user'
                AND column_name IN ('display_name', 'bio', 'avatar_url', 'openrouter_api_key',
                                     'openai_api_key', 'anthropic_api_key')
                """
            )
        )
        existing_columns = {row[0] for row in result}

        # Add display_name if it doesn't exist
        if "display_name" not in existing_columns:
            print("Adding display_name column...")
            await conn.execute(
                text("ALTER TABLE \"user\" ADD COLUMN display_name VARCHAR(100)")
            )
            print("✓ display_name column added")
        else:
            print("✓ display_name column already exists")

        # Add bio if it doesn't exist
        if "bio" not in existing_columns:
            print("Adding bio column...")
            await conn.execute(text("ALTER TABLE \"user\" ADD COLUMN bio TEXT"))
            print("✓ bio column added")
        else:
            print("✓ bio column already exists")

        # Add avatar_url if it doesn't exist
        if "avatar_url" not in existing_columns:
            print("Adding avatar_url column...")
            await conn.execute(
                text("ALTER TABLE \"user\" ADD COLUMN avatar_url VARCHAR(500)")
            )
            print("✓ avatar_url column added")
        else:
            print("✓ avatar_url column already exists")

        # Add openrouter_api_key if it doesn't exist
        if "openrouter_api_key" not in existing_columns:
            print("Adding openrouter_api_key column...")
            await conn.execute(
                text("ALTER TABLE \"user\" ADD COLUMN openrouter_api_key VARCHAR")
            )
            print("✓ openrouter_api_key column added")
        else:
            print("✓ openrouter_api_key column already exists")

        # Remove old API key columns if they exist
        if "openai_api_key" in existing_columns:
            print("Removing old openai_api_key column...")
            await conn.execute(
                text("ALTER TABLE \"user\" DROP COLUMN openai_api_key")
            )
            print("✓ openai_api_key column removed")

        if "anthropic_api_key" in existing_columns:
            print("Removing old anthropic_api_key column...")
            await conn.execute(
                text("ALTER TABLE \"user\" DROP COLUMN anthropic_api_key")
            )
            print("✓ anthropic_api_key column removed")

    print("\n✅ Migration complete!")
    print("User profile fields have been successfully migrated to use OpenRouter.")


async def main():
    try:
        await add_user_profile_fields()
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
