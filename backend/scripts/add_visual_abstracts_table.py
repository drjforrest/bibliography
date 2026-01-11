"""
Migration script to add the visual_abstracts table.

This script creates the visual_abstracts table for storing AI-generated visual
abstracts of scientific papers with 30-day expiration tracking.

Usage:
    python backend/scripts/add_visual_abstracts_table.py
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db import engine


async def add_visual_abstracts_table():
    """Add the visual_abstracts table to the database."""
    print("Starting migration: Adding visual_abstracts table...")

    async with engine.begin() as conn:
        # Check if table already exists
        result = await conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'visual_abstracts'
                )
                """
            )
        )
        table_exists = result.scalar()

        if table_exists:
            print("✓ visual_abstracts table already exists")
            return

        print("Creating visual_abstracts table...")
        await conn.execute(
            text(
                """
                CREATE TABLE visual_abstracts (
                    id SERIAL PRIMARY KEY,
                    paper_id INTEGER NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    prompt_used TEXT,
                    model_used VARCHAR(100),
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (paper_id) REFERENCES scientific_papers(id) ON DELETE CASCADE
                )
                """
            )
        )
        print("✓ visual_abstracts table created")

        # Create indexes for better performance
        print("Creating indexes...")
        await conn.execute(
            text(
                """
                CREATE INDEX idx_visual_abstracts_paper_id
                ON visual_abstracts(paper_id)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX idx_visual_abstracts_expires_at
                ON visual_abstracts(expires_at)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX idx_visual_abstracts_created_at
                ON visual_abstracts(created_at)
                """
            )
        )
        print("✓ Indexes created")

    print("\n✅ Migration complete!")
    print("Visual abstracts table has been successfully added to the database.")


async def main():
    try:
        await add_visual_abstracts_table()
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
