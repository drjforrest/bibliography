#!/usr/bin/env python3
"""
Add user_deleted columns to devonthink_sync table.

This migration adds:
- user_deleted (BOOLEAN) - marks records as deleted by user
- user_deleted_at (TIMESTAMP) - when the record was deleted

These columns prevent re-syncing of papers that have been deleted.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import os

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import config


async def main():
    """Add user_deleted columns to devonthink_sync table."""
    engine = create_async_engine(config.DATABASE_URL)
    
    print("🔧 Adding user_deleted columns to devonthink_sync table...")
    
    try:
        async with engine.begin() as conn:
            # Check if columns already exist
            check_stmt = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'devonthink_sync' 
                AND column_name IN ('user_deleted', 'user_deleted_at')
            """)
            result = await conn.execute(check_stmt)
            existing_columns = {row[0] for row in result.fetchall()}
            
            if 'user_deleted' in existing_columns and 'user_deleted_at' in existing_columns:
                print("✅ Columns already exist, skipping migration")
                return
            
            # Add user_deleted column if it doesn't exist
            if 'user_deleted' not in existing_columns:
                print("   Adding user_deleted column...")
                await conn.execute(text("""
                    ALTER TABLE devonthink_sync 
                    ADD COLUMN user_deleted BOOLEAN DEFAULT FALSE NOT NULL
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_devonthink_sync_user_deleted 
                    ON devonthink_sync(user_deleted)
                """))
                print("   ✅ Added user_deleted column")
            
            # Add user_deleted_at column if it doesn't exist
            if 'user_deleted_at' not in existing_columns:
                print("   Adding user_deleted_at column...")
                await conn.execute(text("""
                    ALTER TABLE devonthink_sync 
                    ADD COLUMN user_deleted_at TIMESTAMP WITH TIME ZONE
                """))
                print("   ✅ Added user_deleted_at column")
            
            print("\n✅ Migration complete!")
            print("   The devonthink_sync table now supports user_deleted exclusion")
    
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
