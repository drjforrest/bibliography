"""
Migration script to add the user_favorites table.

This script creates the user_favorites table for tracking which papers
users have favorited.

Usage:
    python backend/scripts/add_favorites_table.py
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db import engine


async def add_favorites_table():
    """Add the user_favorites table to the database."""
    print("Starting migration: Adding user_favorites table...")

    async with engine.begin() as conn:
        # Check if table already exists
        result = await conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'user_favorites'
                )
                """
            )
        )
        table_exists = result.scalar()

        if table_exists:
            print("✓ user_favorites table already exists")
            return

        print("Creating user_favorites table...")
        await conn.execute(
            text(
                """
                CREATE TABLE user_favorites (
                    user_id UUID NOT NULL,
                    paper_id INTEGER NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, paper_id),
                    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
                    FOREIGN KEY (paper_id) REFERENCES scientific_papers(id) ON DELETE CASCADE
                )
                """
            )
        )
        print("✓ user_favorites table created")

        # Create index on created_at for sorting
        print("Creating index on created_at...")
        await conn.execute(
            text(
                """
                CREATE INDEX idx_user_favorites_created_at
                ON user_favorites(created_at)
                """
            )
        )
        print("✓ Index created")

    print("\n✅ Migration complete!")
    print("User favorites table has been successfully added to the database.")


async def main():
    try:
        await add_favorites_table()
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
