#!/usr/bin/env python3
"""
Add TTS API keys and optimization settings to user table.

Adds:
- openai_api_key (for OpenAI TTS)
- elevenlabs_api_key (for ElevenLabs TTS)
- tts_optimization_mode (auto/prefer_openai/prefer_elevenlabs/kokoro_only)

Note: openrouter_api_key already exists from v1
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

async def add_tts_keys():
    """Add TTS API key columns to user table."""
    
    engine = create_async_engine(DATABASE_URL)
    
    print("\n📋 Adding TTS API keys to user table...")
    
    async with engine.begin() as conn:
        # Add openai_api_key
        print("  - Adding openai_api_key column...")
        await conn.execute(text("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS openai_api_key VARCHAR(255)
        """))
        
        # Add elevenlabs_api_key
        print("  - Adding elevenlabs_api_key column...")
        await conn.execute(text("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS elevenlabs_api_key VARCHAR(255)
        """))
        
        # Add tts_optimization_mode
        print("  - Adding tts_optimization_mode column...")
        await conn.execute(text("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS tts_optimization_mode VARCHAR(50) DEFAULT 'auto'
        """))
    
    print("\n✅ TTS columns added successfully!")
    
    await engine.dispose()

async def verify_columns():
    """Verify that columns were added."""
    
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            AND column_name IN ('openrouter_api_key', 'openai_api_key', 'elevenlabs_api_key', 'tts_optimization_mode')
            ORDER BY column_name
        """))
        
        columns = result.fetchall()
        
        print("\n📊 Verification - User table API key columns:")
        for col in columns:
            default = col[2] if col[2] else "NULL"
            print(f"  ✅ {col[0]}: {col[1]} (default: {default})")
        
        # Check if we have all expected columns
        col_names = [col[0] for col in columns]
        expected = ['elevenlabs_api_key', 'openai_api_key', 'openrouter_api_key', 'tts_optimization_mode']
        
        missing = [col for col in expected if col not in col_names]
        if missing:
            print(f"\n⚠️  Missing columns: {', '.join(missing)}")
        else:
            print("\n✅ All API key columns present!")
    
    await engine.dispose()

async def main():
    try:
        await add_tts_keys()
        await verify_columns()
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
