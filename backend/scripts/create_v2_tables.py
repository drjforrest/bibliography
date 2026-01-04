#!/usr/bin/env python3
"""
Direct database migration script for v2.0 tables.
Handles upgrading existing podcasts table from v1 schema.
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

async def create_v2_tables():
    """Create v2 tables, handling existing podcasts table."""
    
    engine = create_async_engine(DATABASE_URL)
    
    print("\n📋 Creating v2 tables...")
    
    # Create SummaryType enum
    print("  - Creating summarytype enum...")
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE summarytype AS ENUM (
                    'lay', 'technical', 'executive', 'comparative', 'visual'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
    
    # Check if podcasts table exists with old schema
    print("  - Checking podcasts table...")
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'podcasts' 
            AND column_name = 'generation_status'
        """))
        has_new_schema = result.fetchone() is not None
    
    if has_new_schema:
        print("    → Already has v2 schema, skipping")
    else:
        # Check if old table exists
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'podcasts'
            """))
            table_exists = result.fetchone() is not None
        
        if table_exists:
            print("    → Found v1 schema, dropping and recreating...")
            async with engine.begin() as conn:
                await conn.execute(text("DROP TABLE IF EXISTS podcasts CASCADE"))
        else:
            print("    → Creating new table...")
        
        # Create podcasts table with v2 schema
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE podcasts (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    title VARCHAR(500) NOT NULL,
                    description TEXT,
                    duration_seconds INTEGER,
                    podcast_transcript JSON,
                    file_location TEXT,
                    file_size_bytes INTEGER,
                    source_paper_ids INTEGER[] NOT NULL DEFAULT '{}',
                    user_prompt TEXT,
                    generation_status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    generation_error TEXT,
                    task_id VARCHAR(255),
                    search_space_id INTEGER NOT NULL REFERENCES searchspaces(id) ON DELETE CASCADE,
                    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
                )
            """))
        
        # Create indexes for podcasts
        async with engine.begin() as conn:
            await conn.execute(text("CREATE INDEX idx_podcasts_generation_status ON podcasts(generation_status)"))
            await conn.execute(text("CREATE INDEX idx_podcasts_task_id ON podcasts(task_id)"))
            await conn.execute(text("CREATE INDEX idx_podcasts_created_at ON podcasts(created_at)"))
    
    # Create summaries table
    print("  - Creating summaries table...")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS summaries (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                title VARCHAR(500) NOT NULL,
                summary_type summarytype NOT NULL,
                content TEXT NOT NULL,
                key_findings JSON,
                source_paper_ids INTEGER[] NOT NULL DEFAULT '{}',
                user_prompt TEXT,
                generation_status VARCHAR(50) NOT NULL DEFAULT 'pending',
                generation_error TEXT,
                task_id VARCHAR(255),
                search_space_id INTEGER REFERENCES searchspaces(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
            )
        """))
    
    # Create indexes for summaries
    async with engine.begin() as conn:
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_summaries_summary_type ON summaries(summary_type)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_summaries_task_id ON summaries(task_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries(created_at)"))
    
    # Create infographics table
    print("  - Creating infographics table...")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS infographics (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                title VARCHAR(500) NOT NULL,
                infographic_type VARCHAR(50) NOT NULL,
                file_location TEXT,
                file_format VARCHAR(10),
                file_size_bytes INTEGER,
                data_json JSON,
                source_paper_ids INTEGER[] NOT NULL DEFAULT '{}',
                user_prompt TEXT,
                generation_status VARCHAR(50) NOT NULL DEFAULT 'pending',
                generation_error TEXT,
                task_id VARCHAR(255),
                search_space_id INTEGER REFERENCES searchspaces(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
            )
        """))
    
    # Create indexes for infographics
    async with engine.begin() as conn:
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_infographics_task_id ON infographics(task_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_infographics_created_at ON infographics(created_at)"))
    
    # Create slide_decks table
    print("  - Creating slide_decks table...")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS slide_decks (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                title VARCHAR(500) NOT NULL,
                slide_count INTEGER,
                file_location TEXT,
                file_format VARCHAR(10),
                file_size_bytes INTEGER,
                slides_json JSON,
                source_paper_ids INTEGER[] NOT NULL DEFAULT '{}',
                user_prompt TEXT,
                generation_status VARCHAR(50) NOT NULL DEFAULT 'pending',
                generation_error TEXT,
                task_id VARCHAR(255),
                search_space_id INTEGER REFERENCES searchspaces(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
            )
        """))
    
    # Create indexes for slide_decks
    async with engine.begin() as conn:
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_slide_decks_task_id ON slide_decks(task_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_slide_decks_created_at ON slide_decks(created_at)"))
    
    print("\n✅ All v2 tables created successfully!")
    
    await engine.dispose()

async def verify_tables():
    """Verify that tables were created."""
    
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('podcasts', 'summaries', 'infographics', 'slide_decks')
            ORDER BY tablename
        """))
        
        tables = [row[0] for row in result]
        
        print("\n📊 Verification:")
        expected = ['infographics', 'podcasts', 'slide_decks', 'summaries']
        for table in expected:
            if table in tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} - MISSING!")
    
    await engine.dispose()

async def main():
    try:
        await create_v2_tables()
        await verify_tables()
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
