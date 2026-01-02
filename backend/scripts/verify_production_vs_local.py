#!/usr/bin/env python3
"""
Compare local vs production databases to see where the sync actually went.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, func, text

async def check_database(label, database_url):
    """Check a specific database"""
    print(f"\n{'='*60}")
    print(f"Checking: {label}")
    print(f"{'='*60}")
    print(f"Connection: {database_url.split('@')[1] if '@' in database_url else 'REDACTED'}")
    
    try:
        engine = create_async_engine(database_url)
        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        
        async with async_session_maker() as session:
            # Get connection info
            result = await session.execute(text(
                'SELECT current_database(), inet_server_addr(), inet_server_port(), version()'
            ))
            row = result.first()
            db_name, server_ip, server_port, pg_version = row
            
            print(f"✓ Connected successfully")
            print(f"  Database: {db_name}")
            print(f"  Server: {server_ip or 'localhost'}:{server_port or 'local'}")
            print(f"  PostgreSQL: {pg_version[:60]}...")
            
            # Check sync stats
            from app.db import DevonthinkSync, DevonthinkSyncStatus, ScientificPaper
            
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
            
            print(f"\n  📊 Stats:")
            print(f"     ✅ Synced: {synced}")
            print(f"     📄 Total papers: {total_papers}")
            print(f"     ❌ Failed: {failed}")
            
            # Check for recent syncs (from today)
            recent_syncs = await session.scalar(
                select(func.count(DevonthinkSync.id)).where(
                    DevonthinkSync.sync_status == DevonthinkSyncStatus.SYNCED,
                    DevonthinkSync.last_sync_date >= text("CURRENT_DATE")
                )
            )
            print(f"     📅 Synced today: {recent_syncs}")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        return False

async def main():
    # Check local database (from .env or default)
    from app.config import config
    local_url = config.DATABASE_URL
    
    # Check production via tunnel
    prod_url = os.environ.get('DATABASE_URL') or "postgresql+asyncpg://postgres:postgres@localhost:5433/hero_evidence_library_prod"
    
    print("="*60)
    print("COMPARING DATABASES")
    print("="*60)
    
    local_ok = await check_database("LOCAL (from .env)", local_url)
    prod_ok = await check_database("PRODUCTION (via SSH tunnel)", prod_url)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    if local_ok and prod_ok:
        print("✓ Both databases accessible")
        print("\n⚠️  If sync stats are different, check which one has 71 synced records")
        print("   That's where your sync went!")
    elif local_ok:
        print("⚠️  Only local database accessible - production tunnel may be down")
    elif prod_ok:
        print("⚠️  Only production accessible - local database may not be running")
    else:
        print("❌ Neither database accessible")

if __name__ == "__main__":
    asyncio.run(main())

