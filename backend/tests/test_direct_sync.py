#!/usr/bin/env python3
"""
Test direct sync bypassing the get_open_databases issue
"""

import asyncio
import logging
import os
import sys
from uuid import UUID

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.append('/Users/drjforrest/dev/devprojects/bibliography/backend')

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db import User, SearchSpace
from app.config import config
from app.services.devonthink_mcp_client import DevonthinkMCPClient
from app.services.devonthink_sync_service import DevonthinkSyncService
from app.schemas.devonthink_schemas import DevonthinkSyncRequest

logger = logging.getLogger(__name__)


async def test_direct_sync():
    """Test direct sync by bypassing the directory mapping that uses get_open_databases"""
    
    print("🔄 Testing Direct Sync (bypassing get_open_databases issue)")
    print("=" * 60)
    
    try:
        # Database setup
        engine = create_async_engine(config.DATABASE_URL, echo=False)
        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        
        async with async_session_maker() as session:
            # Get user and search space
            user_stmt = select(User).limit(1)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                print("❌ No user found")
                return
            
            space_stmt = select(SearchSpace).where(SearchSpace.user_id == user.id).limit(1)
            space_result = await session.execute(space_stmt)
            search_space = space_result.scalar_one_or_none()
            
            if not search_space:
                print("❌ No search space found")
                return
            
            print(f"✅ User: {user.email}")
            print(f"✅ Search space: {search_space.name}")
            
            # Test MCP client directly first
            print("\n1. Testing MCP search for PDFs...")
            os.environ['DEVONTHINK_MCP_BACKEND'] = 'real'
            mcp_client = DevonthinkMCPClient()
            
            # Search for PDFs in Reference database
            pdf_records = await mcp_client.search_records("kind:pdf", database_name="Reference", limit=3)
            print(f"   Found {len(pdf_records)} PDFs in Reference database")
            
            if not pdf_records:
                print("❌ No PDFs found in Reference database")
                return
            
            for i, record in enumerate(pdf_records, 1):
                print(f"     {i}. {record.get('name', 'Unknown')}")
                print(f"        UUID: {record.get('uuid', 'N/A')}")
            
            # Now test sync service with modified approach
            print("\n2. Testing sync service...")
            sync_service = DevonthinkSyncService(session)
            
            # Try to sync just one record manually
            test_record = pdf_records[0]
            print(f"   Testing single record: {test_record.get('name')}")
            
            try:
                # Test single record sync
                await sync_service._sync_single_record(
                    test_record, 
                    "Reference", 
                    user.id, 
                    search_space.id, 
                    force_resync=True
                )
                print("   ✅ Single record sync successful!")
                
            except Exception as e:
                print(f"   ❌ Single record sync failed: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # Alternative: Test without directory mapping
            print("\n3. Testing simplified sync request...")
            
            # Create a custom sync function that skips directory mapping
            async def simplified_sync():
                """Simplified sync that skips the problematic directory mapping"""
                try:
                    # Step 1: Search for PDFs directly
                    pdf_records = await mcp_client.search_records("kind:pdf", database_name="Reference", limit=5)
                    print(f"   Found {len(pdf_records)} PDFs to sync")
                    
                    # Step 2: Sync records directly (skip directory mapping)
                    stats = {"synced": 0, "errors": 0, "skipped": 0, "details": []}
                    
                    for record in pdf_records[:2]:  # Limit to 2 for testing
                        try:
                            await sync_service._sync_single_record(
                                record, "Reference", user.id, search_space.id, force_resync=False
                            )
                            stats["synced"] += 1
                            stats["details"].append(f"Synced: {record.get('name', 'Unknown')}")
                            
                        except Exception as e:
                            stats["errors"] += 1
                            error_msg = f"Failed to sync {record.get('name', 'Unknown')}: {str(e)}"
                            stats["details"].append(error_msg)
                            logger.error(error_msg)
                    
                    return stats
                
                except Exception as e:
                    logger.error(f"Simplified sync failed: {str(e)}")
                    raise
            
            # Run simplified sync
            result = await simplified_sync()
            
            print(f"   Sync Results:")
            print(f"     Synced: {result['synced']}")
            print(f"     Errors: {result['errors']}")
            print(f"     Details:")
            for detail in result['details']:
                print(f"       - {detail}")
            
            if result['synced'] > 0:
                print("\n   🎉 Simplified sync worked! The pipeline can process records.")
                print("   💡 Issue is with get_open_databases MCP call, not the core pipeline.")
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_direct_sync())