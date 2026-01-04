#!/usr/bin/env python3
"""Drop old v1 tables before creating v2 schema."""

import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

async def drop_old_tables():
    engine = create_async_engine(DATABASE_URL)
    
    print("🗑️  Dropping old v1 podcast-related tables...")
    
    async with engine.begin() as conn:
        # Drop podcasts if it exists
        await conn.execute(text("DROP TABLE IF EXISTS podcasts CASCADE"))
        print("  ✅ Dropped podcasts table")
        
        # Also drop any v2 tables that might partially exist
        await conn.execute(text("DROP TABLE IF EXISTS summaries CASCADE"))
        print("  ✅ Dropped summaries table (if existed)")
        
        await conn.execute(text("DROP TABLE IF EXISTS infographics CASCADE"))
        print("  ✅ Dropped infographics table (if existed)")
        
        await conn.execute(text("DROP TABLE IF EXISTS slide_decks CASCADE"))
        print("  ✅ Dropped slide_decks table (if existed)")
        
        # Drop enum type
        await conn.execute(text("DROP TYPE IF EXISTS summarytype CASCADE"))
        print("  ✅ Dropped summarytype enum (if existed)")
    
    await engine.dispose()
    print("\n✅ Ready for fresh v2 migration")

if __name__ == "__main__":
    asyncio.run(drop_old_tables())
