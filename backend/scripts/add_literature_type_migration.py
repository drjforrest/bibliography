#!/usr/bin/env python3
"""
Migration script to add literature_type column to scientific_papers table.
This adds support for "rooms" feature (Peer-reviewed, Grey Literature, News).
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine, LiteratureType


async def migrate_add_literature_type():
    """Add literature_type column to scientific_papers table."""

    print("Starting migration: Adding literature_type column to scientific_papers...")

    async with engine.begin() as conn:
        try:
            # First, create the enum type if it doesn't exist
            print("Creating LiteratureType enum type...")
            await conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE literaturetype AS ENUM ('PEER_REVIEWED', 'GREY_LITERATURE', 'NEWS');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            print("✓ LiteratureType enum type created/verified")

            # Add the column with default value
            print("Adding literature_type column...")
            await conn.execute(text("""
                ALTER TABLE scientific_papers
                ADD COLUMN IF NOT EXISTS literature_type literaturetype
                NOT NULL DEFAULT 'PEER_REVIEWED'::literaturetype;
            """))
            print("✓ literature_type column added")

            # Create index on literature_type for better query performance
            print("Creating index on literature_type...")
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_scientific_papers_literature_type
                ON scientific_papers(literature_type);
            """))
            print("✓ Index created on literature_type")

            # Set existing papers to PEER_REVIEWED (default)
            result = await conn.execute(text("""
                UPDATE scientific_papers
                SET literature_type = 'PEER_REVIEWED'::literaturetype
                WHERE literature_type IS NULL;
            """))
            print(f"✓ Updated {result.rowcount} existing papers to PEER_REVIEWED")

            print("\n✅ Migration completed successfully!")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            raise


async def rollback_migration():
    """Rollback the migration - remove literature_type column."""

    print("Starting rollback: Removing literature_type column...")

    async with engine.begin() as conn:
        try:
            # Drop the index
            print("Dropping index...")
            await conn.execute(text("""
                DROP INDEX IF EXISTS idx_scientific_papers_literature_type;
            """))
            print("✓ Index dropped")

            # Drop the column
            print("Dropping literature_type column...")
            await conn.execute(text("""
                ALTER TABLE scientific_papers
                DROP COLUMN IF EXISTS literature_type;
            """))
            print("✓ literature_type column dropped")

            # Note: We don't drop the enum type as it might be in use
            print("Note: literaturetype enum type not dropped (might be in use)")

            print("\n✅ Rollback completed successfully!")

        except Exception as e:
            print(f"\n❌ Rollback failed: {e}")
            raise


async def check_migration_status():
    """Check if migration has been applied."""

    print("Checking migration status...")

    async with engine.begin() as conn:
        try:
            # Check if column exists
            result = await conn.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'scientific_papers'
                AND column_name = 'literature_type';
            """))

            row = result.fetchone()
            if row:
                print(f"✓ Migration applied: literature_type column exists")
                print(f"  - Type: {row[1]}")
                print(f"  - Default: {row[2]}")

                # Count papers by type
                count_result = await conn.execute(text("""
                    SELECT literature_type, COUNT(*) as count
                    FROM scientific_papers
                    GROUP BY literature_type
                    ORDER BY count DESC;
                """))

                print("\nPapers by literature type:")
                for type_row in count_result:
                    print(f"  - {type_row[0]}: {type_row[1]} papers")
            else:
                print("✗ Migration not applied: literature_type column does not exist")

        except Exception as e:
            print(f"\n❌ Status check failed: {e}")
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate database to add literature_type column")
    parser.add_argument("action", choices=["migrate", "rollback", "status"],
                       help="Action to perform")

    args = parser.parse_args()

    if args.action == "migrate":
        asyncio.run(migrate_add_literature_type())
    elif args.action == "rollback":
        asyncio.run(rollback_migration())
    elif args.action == "status":
        asyncio.run(check_migration_status())
