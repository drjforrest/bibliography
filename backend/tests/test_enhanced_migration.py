#!/usr/bin/env python3
"""
Test script for the Enhanced Migration Service with detailed console logging.

This script demonstrates the migration pipeline with comprehensive logging
showing progress through each phase:
- DEVONthink record discovery
- PDF processing and chunking
- Vector embedding and pgvector storage
- PostgreSQL metadata updates
- AI lay summary generation
"""

import asyncio
import logging
import os
import sys
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append('/Users/drjforrest/dev/devprojects/bibliography/backend')

from app.services.enhanced_migration_service import EnhancedMigrationService


def setup_detailed_logging():
    """Setup comprehensive console logging with colors and emojis"""
    
    # Create custom formatter with detailed information
    class DetailedFormatter(logging.Formatter):
        """Custom formatter with timestamps and colors"""
        
        def format(self, record):
            # Add timestamp
            if not hasattr(record, 'created'):
                record.created = 0
            
            # Format timestamp
            import datetime
            timestamp = datetime.datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            
            # Create the log message
            if record.levelno >= logging.ERROR:
                prefix = f"[{timestamp}] ❌ ERROR"
            elif record.levelno >= logging.WARNING:
                prefix = f"[{timestamp}] ⚠️  WARN"
            elif record.levelno >= logging.INFO:
                prefix = f"[{timestamp}] ℹ️  INFO"
            else:
                prefix = f"[{timestamp}] 🔍 DEBUG"
            
            return f"{prefix}: {record.getMessage()}"
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(DetailedFormatter())
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set specific loggers to appropriate levels
    logging.getLogger('app.services').setLevel(logging.DEBUG)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)  # Reduce SQL noise
    logging.getLogger('httpx').setLevel(logging.WARNING)  # Reduce HTTP noise
    
    print("🚀 Enhanced Migration Service Test")
    print("=" * 50)
    print("🔍 Logging configured for detailed migration tracking")
    print("📊 Watch for progress through these phases:")
    print("  1️⃣  Initialization & Prerequisites")
    print("  2️⃣  Directory Mapping")
    print("  3️⃣  Record Discovery")
    print("  4️⃣  PDF Migration (Processing, Chunking, Vector Storage)")
    print("  5️⃣  AI Lay Summary Generation")
    print("  6️⃣  Job Completion")
    print("=" * 50)


async def test_migration():
    """Test the enhanced migration service"""
    
    # Setup logging
    setup_detailed_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Database connection
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return
            
        logger.info("🔌 Connecting to database...")
        engine = create_async_engine(database_url, echo=False)
        
        # Create session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Create service
            logger.info("🏗️  Initializing Enhanced Migration Service...")
            service = EnhancedMigrationService(session)
            
            # Test configuration - ADJUST THESE VALUES FOR YOUR SETUP
            test_config = {
                "database_name": "References",  # Your DEVONthink database name
                "user_id": UUID("12345678-1234-5678-9abc-123456789012"),  # Replace with your user ID
                "search_space_id": 1,  # Replace with your search space ID
                "folder_path": None,  # Set to specific folder if desired, e.g., "/Research Papers"
                "force_resync": False  # Set True to re-process already synced records
            }
            
            logger.info("🎯 Migration Configuration:")
            logger.info(f"   📚 Database: {test_config['database_name']}")
            logger.info(f"   👤 User ID: {test_config['user_id']}")
            logger.info(f"   🔍 Search Space ID: {test_config['search_space_id']}")
            logger.info(f"   📁 Folder Path: {test_config['folder_path'] or 'All folders'}")
            logger.info(f"   🔄 Force Resync: {test_config['force_resync']}")
            
            # Start migration
            logger.info("🚀 Starting migration job...")
            job_id = await service.start_complete_migration(**test_config)
            
            logger.info(f"📋 Migration job started with ID: {job_id}")
            logger.info("👀 Watch the logs above for detailed progress...")
            
            # Monitor progress (for demo purposes, just wait a bit)
            await asyncio.sleep(5)
            
            # Get status
            status = await service.get_migration_status(job_id)
            if status:
                logger.info(f"📊 Current job status: {status.get('phase', 'Unknown')}")
                logger.info(f"📈 Progress: {status.get('completed', 0)}/{status.get('total', 0)} records")
            
            # Cleanup
            await service.cleanup()
            logger.info("✅ Test completed successfully")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    # Check if DEVONthink is running
    print("📝 IMPORTANT: Before running this test:")
    print("   1. Make sure DEVONthink is running")
    print("   2. Open your 'References' database (or update database name in script)")
    print("   3. Update the user_id and search_space_id in the script")
    print("   4. Ensure Redis is running for progress tracking")
    print("   5. Ensure Ollama is running for lay summary generation")
    print()
    
    response = input("Ready to start migration test? [y/N]: ")
    if response.lower() != 'y':
        print("👋 Test cancelled")
        sys.exit(0)
    
    # Run the test
    asyncio.run(test_migration())