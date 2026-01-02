#!/usr/bin/env python3
"""
Migration script to add user_deleted and user_deleted_at columns to devonthink_sync table.
This prevents re-syncing records that users have deleted.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import engine
from sqlalchemy import text


async def migrate_add_user_deleted():
    """Add user_deleted and user_deleted_at columns to devonthink_sync table."""

    print("Starting migration: Adding user_deleted tracking to devonthink_sync...")

    async with engine.begin() as conn:
        try:
            # Add user_deleted column with default False
            print("Adding user_deleted column...")
            await conn.execute(
                text(
                    """
                ALTER TABLE devonthink_sync
                ADD COLUMN IF NOT EXISTS user_deleted BOOLEAN
                NOT NULL DEFAULT FALSE;
            """
                )
            )
            print("✓ user_deleted column added")

            # Add user_deleted_at column
            print("Adding user_deleted_at column...")
            await conn.execute(
                text(
                    """
                ALTER TABLE devonthink_sync
                ADD COLUMN IF NOT EXISTS user_deleted_at TIMESTAMP WITH TIME ZONE;
            """
                )
            )
            print("✓ user_deleted_at column added")

            # Create index on user_deleted for faster queries
            print("Creating index on user_deleted...")
            await conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_devonthink_sync_user_deleted
                ON devonthink_sync (user_deleted);
            """
                )
            )
            print("✓ Index created on user_deleted")

            print("\n✅ Migration completed successfully!")
            print("   - user_deleted column added (default: FALSE)")
            print("   - user_deleted_at column added (nullable)")
            print("   - Index created for faster queries")

        except Exception as e:
            print(f"\n❌ Migration failed: {str(e)}")
            raise


async def check_migration_status():
    """Check if migration has already been applied."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'devonthink_sync'
            AND column_name IN ('user_deleted', 'user_deleted_at')
            ORDER BY column_name;
        """
            )
        )

        rows = result.fetchall()
        if rows:
            print("\n📊 Migration Status:")
            for row in rows:
                print(f"   ✓ {row[0]}: {row[1]} (default: {row[2]})")
        else:
            print("\n⚠️  Migration not yet applied")


async def main():
    """Run the migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add user_deleted tracking to devonthink_sync"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check migration status without applying",
    )
    args = parser.parse_args()

    if args.check:
        await check_migration_status()
    else:
        await migrate_add_user_deleted()
        print("\n💡 Tip: Run with --check to verify the migration")


if __name__ == "__main__":
    asyncio.run(main())
