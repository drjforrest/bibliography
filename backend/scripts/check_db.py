#!/usr/bin/env python3
"""Check what's in the database."""

import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

async def check_database():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        # Check if podcasts table exists
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'podcasts'
        """))
        
        exists = result.fetchone()
        
        if exists:
            print("✅ podcasts table EXISTS")
            
            # Get column info
            result = await conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'podcasts'
                ORDER BY ordinal_position
            """))
            
            print("\nColumns in podcasts table:")
            for row in result:
                print(f"  - {row[0]}: {row[1]}")
        else:
            print("❌ podcasts table does NOT exist")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_database())
