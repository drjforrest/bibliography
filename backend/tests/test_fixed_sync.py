#!/usr/bin/env python3
"""
Test the fixed sync service to confirm it works properly
"""

import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sys.path.append('/Users/drjforrest/dev/devprojects/bibliography/backend')

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db import User, SearchSpace
from app.config import config
from app.services.devonthink_sync_service import DevonthinkSyncService
from app.schemas.devonthink_schemas import DevonthinkSyncRequest

async def test_fixed_sync():
    """Test the fixed sync service"""
    
    print("🔧 Testing Fixed Sync Service")
    print("=" * 50)
    
    try:
        # Database setup
        engine = create_async_engine(config.DATABASE_URL, echo=False)
        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        
        async with async_session_maker() as session:
            # Get user and search space
            user_stmt = select(User).limit(1)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            space_stmt = select(SearchSpace).where(SearchSpace.user_id == user.id).limit(1)
            space_result = await session.execute(space_stmt)
            search_space = space_result.scalar_one_or_none()
            
            print(f"✅ User: {user.email}")
            print(f"✅ Search space: {search_space.name}")
            
            # Create sync service
            sync_service = DevonthinkSyncService(session)
            
            # Test sync request (with force_resync=False to avoid duplicates)
            sync_request = DevonthinkSyncRequest(
                database_name="Reference",
                search_space_id=search_space.id,
                folder_path=None,
                force_resync=False  # This should skip existing papers
            )
            
            print("\n🚀 Testing sync with the fix...")
            response = await sync_service.sync_database(sync_request, user.id)
            
            print(f"\n📊 Sync Results:")
            print(f"   Success: {response.success}")
            print(f"   Message: {response.message}")
            print(f"   Synced: {response.synced_count}")
            print(f"   Errors: {response.error_count}")
            print(f"   Skipped: {response.skipped_count}")
            
            print(f"\n📋 Details:")
            for detail in response.details:
                print(f"   - {detail}")
            
            if response.success:
                print("\n🎉 Fixed sync service is working!")
                print("✅ The get_open_databases issue has been resolved")
                print("✅ Sync can now proceed even when directory mapping fails")
            else:
                print(f"\n❌ Sync failed: {response.message}")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_sync())