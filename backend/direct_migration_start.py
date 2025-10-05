#!/usr/bin/env python3
"""
Direct starter for Enhanced Migration Service
"""

import asyncio
import logging
from uuid import UUID
from app.services.enhanced_migration_service import EnhancedMigrationService
from app.db import get_async_session_context

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

async def start_migration():
    """Start migration with hardcoded values - update these for your setup"""
    
    # UPDATE THESE VALUES FOR YOUR SETUP:
    DATABASE_NAME = "References"  # Your DEVONthink database name
    USER_ID = "12345678-1234-5678-9abc-123456789012"  # Replace with your actual user UUID
    SEARCH_SPACE_ID = 1  # Update if you have a different search space ID
    FOLDER_PATH = None  # Set to a specific folder path if needed, e.g., "/Research Papers"
    FORCE_RESYNC = False  # Set to True to re-process existing records
    
    try:
        async with get_async_session_context() as session:
            service = EnhancedMigrationService(session)
            
            job_id = await service.start_complete_migration(
                database_name=DATABASE_NAME,
                user_id=UUID(USER_ID),
                search_space_id=SEARCH_SPACE_ID,
                folder_path=FOLDER_PATH,
                force_resync=FORCE_RESYNC
            )
            
            print(f"✅ Migration started! Job ID: {job_id}")
            print("🔍 Check the logs for detailed progress updates")
            
            # Keep running to monitor progress
            while True:
                status = await service.get_migration_status(job_id)
                if not status:
                    break
                    
                phase = status.get('phase', 'unknown')
                if phase in ['completed', 'failed']:
                    print(f"🎉 Migration {phase}!")
                    break
                    
                await asyncio.sleep(10)
            
            await service.cleanup()
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(start_migration())