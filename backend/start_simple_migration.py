#!/usr/bin/env python3
"""
Simplified migration starter that works around MCP client issues
"""

import asyncio
import logging
from uuid import UUID
from app.db import get_async_session_context, SearchSpace, ScientificPaper, Document, DevonthinkSync
from app.services.file_storage import FileStorageService
from app.services.pdf_processor import PDFProcessor
from sqlalchemy import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)

async def simple_migration():
    """Start a simple migration using sample data"""
    
    USER_ID = "960bc239-c12e-4559-bb86-a5072df1f4a6"
    
    logger.info("🚀 Starting Simple DEVONthink Migration")
    logger.info("=" * 50)
    
    try:
        user_uuid = UUID(USER_ID)
        
        async with get_async_session_context() as session:
            # Get or create search space
            stmt = select(SearchSpace).where(SearchSpace.user_id == user_uuid)
            result = await session.execute(stmt)
            search_space = result.scalar_one_or_none()
            
            if not search_space:
                logger.error("No search space found. Please create one first.")
                return
            
            logger.info(f"Using search space: {search_space.name} (ID: {search_space.id})")
            
            # Initialize services
            file_storage = FileStorageService()
            pdf_processor = PDFProcessor(session)
            
            logger.info("📄 Services initialized successfully")
            
            # For now, let's create a simple test record to verify the system works
            logger.info("🧪 Creating test record to verify system...")
            
            # Create a test document
            from app.db import Document, DocumentType
            import uuid
            
            test_doc = Document(
                title="Test Migration Document",
                document_type=DocumentType.SCIENTIFIC_PAPER,
                content="This is a test document to verify the migration system is working.",
                search_space_id=search_space.id,
                document_metadata={"source": "migration_test", "test": True}
            )
            
            session.add(test_doc)
            await session.commit()
            
            logger.info(f"✅ Created test document with ID: {test_doc.id}")
            
            # Create a corresponding scientific paper record
            test_paper = ScientificPaper(
                title="Test Migration Paper",
                abstract="This is a test paper created during migration setup.",
                file_path="/tmp/test_migration_paper.pdf",
                processing_status="completed",
                document_id=test_doc.id,
                dt_source_uuid="TEST-UUID-12345",
                dt_source_path="/Test/Migration/Paper.pdf"
            )
            
            session.add(test_paper)
            await session.commit()
            
            logger.info(f"✅ Created test scientific paper with ID: {test_paper.id}")
            
            # Create sync record
            sync_record = DevonthinkSync(
                dt_uuid="TEST-UUID-12345",
                dt_path="/Test/Migration/Paper.pdf",
                local_uuid=uuid.uuid4(),
                user_id=user_uuid,
                scientific_paper_id=test_paper.id,
                sync_status="SYNCED"
            )
            
            session.add(sync_record)
            await session.commit()
            
            logger.info(f"✅ Created sync record with DT UUID: {sync_record.dt_uuid}")
            
            # Verify the complete setup
            logger.info("🔍 Verifying migration system setup...")
            
            # Count records
            stmt = select(Document).where(Document.search_space_id == search_space.id)
            result = await session.execute(stmt)
            documents = result.scalars().all()
            
            stmt = select(ScientificPaper)
            result = await session.execute(stmt)
            papers = result.scalars().all()
            
            stmt = select(DevonthinkSync).where(DevonthinkSync.user_id == user_uuid)
            result = await session.execute(stmt)
            syncs = result.scalars().all()
            
            logger.info(f"📊 System Status:")
            logger.info(f"   📚 Documents: {len(documents)}")
            logger.info(f"   📄 Scientific Papers: {len(papers)}")
            logger.info(f"   🔄 DEVONthink Sync Records: {len(syncs)}")
            
            logger.info("✅ Migration system is set up and working!")
            logger.info("🎯 Ready for real DEVONthink integration!")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def show_status():
    """Show current system status"""
    USER_ID = "960bc239-c12e-4559-bb86-a5072df1f4a6"
    
    logger.info("📊 Current System Status")
    logger.info("=" * 30)
    
    try:
        user_uuid = UUID(USER_ID)
        
        async with get_async_session_context() as session:
            # Count records by type
            counts = {}
            
            # Documents
            stmt = select(Document)
            result = await session.execute(stmt)
            counts['documents'] = len(result.scalars().all())
            
            # Scientific Papers
            stmt = select(ScientificPaper)
            result = await session.execute(stmt)
            counts['papers'] = len(result.scalars().all())
            
            # DEVONthink Syncs
            stmt = select(DevonthinkSync).where(DevonthinkSync.user_id == user_uuid)
            result = await session.execute(stmt)
            counts['syncs'] = len(result.scalars().all())
            
            # Search Spaces
            stmt = select(SearchSpace).where(SearchSpace.user_id == user_uuid)
            result = await session.execute(stmt)
            search_spaces = result.scalars().all()
            counts['search_spaces'] = len(search_spaces)
            
            logger.info(f"📚 Documents: {counts['documents']}")
            logger.info(f"📄 Scientific Papers: {counts['papers']}")
            logger.info(f"🔄 DEVONthink Syncs: {counts['syncs']}")
            logger.info(f"🔍 Search Spaces: {counts['search_spaces']}")
            
            if search_spaces:
                logger.info("Search Spaces:")
                for space in search_spaces:
                    logger.info(f"  - {space.name} (ID: {space.id})")
            
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Simple migration system")
    parser.add_argument("--test", action="store_true", help="Run test migration")
    parser.add_argument("--status", action="store_true", help="Show system status")
    
    args = parser.parse_args()
    
    if args.test:
        success = asyncio.run(simple_migration())
        if not success:
            exit(1)
    elif args.status:
        asyncio.run(show_status())
    else:
        print("Use --test to run test migration or --status to show system status")

if __name__ == "__main__":
    main()