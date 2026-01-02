#!/usr/bin/env python3
"""
Migration script to fix DevonthinkSync foreign key constraint.

This fixes a critical bug where deleting a paper would cascade-delete the sync record,
preventing the user_deleted flag from persisting. The fix changes the foreign key
from ON DELETE CASCADE to ON DELETE SET NULL, allowing sync records to persist
after paper deletion so the user_deleted flag can prevent re-syncing.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import engine
from sqlalchemy import text


async def fix_devonthink_sync_cascade():
    """Change DevonthinkSync.scientific_paper_id foreign key from CASCADE to SET NULL."""

    print("Starting migration: Fixing DevonthinkSync foreign key constraint...")
    print(
        "This allows sync records to persist when papers are deleted, preserving user_deleted flag."
    )
    print()

    async with engine.begin() as conn:
        try:
            # Step 1: Drop the existing foreign key constraint
            print("Step 1: Dropping existing foreign key constraint...")
            await conn.execute(
                text(
                    """
                    ALTER TABLE devonthink_sync
                    DROP CONSTRAINT IF EXISTS devonthink_sync_scientific_paper_id_fkey;
                """
                )
            )
            print("✓ Existing constraint dropped")

            # Step 2: Add the new foreign key constraint with SET NULL
            print(
                "Step 2: Adding new foreign key constraint with ON DELETE SET NULL..."
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE devonthink_sync
                    ADD CONSTRAINT devonthink_sync_scientific_paper_id_fkey
                    FOREIGN KEY (scientific_paper_id)
                    REFERENCES scientific_papers(id)
                    ON DELETE SET NULL;
                """
                )
            )
            print("✓ New constraint added with ON DELETE SET NULL")

            # Step 3: Verify the constraint
            print("Step 3: Verifying constraint...")
            result = await conn.execute(
                text(
                    """
                    SELECT 
                        conname,
                        pg_get_constraintdef(oid) as constraint_def
                    FROM pg_constraint
                    WHERE conrelid = 'devonthink_sync'::regclass
                    AND conname = 'devonthink_sync_scientific_paper_id_fkey';
                """
                )
            )
            row = result.fetchone()
            if row:
                print(f"✓ Constraint verified: {row[1]}")
            else:
                print("⚠ Warning: Could not verify constraint (this may be normal)")

            print("\n✅ Migration completed successfully!")
            print("\nNote: Sync records will now persist when papers are deleted,")
            print("      allowing the user_deleted flag to prevent re-syncing.")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback

            traceback.print_exc()
            raise


async def main():
    """Run the migration."""
    await fix_devonthink_sync_cascade()


if __name__ == "__main__":
    asyncio.run(main())
