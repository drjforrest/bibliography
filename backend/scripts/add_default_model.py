#!/usr/bin/env python3
"""
Add default_openrouter_model to user table.

Allows users to set their preferred LLM model once in settings
instead of choosing on every generation.
"""

import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

print(f"✅ Using database: {DATABASE_URL.split('@')[-1]}")

async def add_default_model():
    """Add default_openrouter_model column to user table."""
    
    engine = create_async_engine(DATABASE_URL)
    
    print("\n📋 Adding default_openrouter_model to user table...")
    
    async with engine.begin() as conn:
        # Add default_openrouter_model
        print("  - Adding default_openrouter_model column...")
        await conn.execute(text("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS default_openrouter_model VARCHAR(100) DEFAULT 'anthropic/claude-sonnet-4-20250514'
        """))
    
    print("\n✅ Column added successfully!")
    
    await engine.dispose()

async def verify_column():
    """Verify that column was added."""
    
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            AND column_name = 'default_openrouter_model'
        """))
        
        col = result.fetchone()
        
        if col:
            print("\n📊 Verification:")
            print(f"  ✅ {col[0]}: {col[1]}")
            print(f"     Default: {col[2]}")
        else:
            print("\n❌ Column not found!")
    
    await engine.dispose()

async def main():
    try:
        await add_default_model()
        await verify_column()
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
