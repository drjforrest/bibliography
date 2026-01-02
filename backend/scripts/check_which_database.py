#!/usr/bin/env python3
"""Quick script to verify which database we're connected to"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, func, text

# Use DATABASE_URL from environment, or default to config
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    from app.config import config
    database_url = config.DATABASE_URL
    print("⚠️  No DATABASE_URL in environment, using config")
else:
    print(f"✅ Using DATABASE_URL from environment")

# Create engine directly with the URL we want
engine = create_async_engine(database_url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def check():
    async with async_session_maker() as session:
        # Check which database and server we're connected to
        result = await session.execute(text(
            'SELECT current_database(), inet_server_addr(), inet_server_port(), version()'
        ))
        row = result.first()
        db_name, server_ip, server_port, pg_version = row
        
        print("\n" + "=" * 60)
        print("DATABASE CONNECTION INFO")
        print("=" * 60)
        print(f"Database Name: {db_name}")
        print(f"Server IP: {server_ip or 'localhost (local PostgreSQL)'}")
        print(f"Server Port: {server_port or 'N/A (local connection)'}")
        print(f"PostgreSQL Version: {pg_version[:80]}...")
        print()
        
        if server_ip:
            print("🌐 This is a REMOTE connection (production on mac-mini)")
        elif "Homebrew" in pg_version:
            print("💻 This is a LOCAL connection (Homebrew PostgreSQL on your MacBook)")
        else:
            print("💻 This is a LOCAL connection (your MacBook)")
        
        print()
        print("=" * 60)
        print("SYNC STATS")
        print("=" * 60)
        
        # Import models here after we have the session
        from app.db import DevonthinkSync, DevonthinkSyncStatus, ScientificPaper
        
        # Count synced records
        synced = await session.scalar(
            select(func.count(DevonthinkSync.id)).where(
                DevonthinkSync.sync_status == DevonthinkSyncStatus.SYNCED
            )
        )
        total_papers = await session.scalar(select(func.count(ScientificPaper.id)))
        failed = await session.scalar(
            select(func.count(DevonthinkSync.id)).where(
                DevonthinkSync.sync_status == DevonthinkSyncStatus.ERROR
            )
        )
        
        print(f"✅ Successfully synced DEVONthink records: {synced}")
        print(f"📄 Total papers in database: {total_papers}")
        print(f"❌ Failed syncs: {failed}")
        print()
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
