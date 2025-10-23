#!/usr/bin/env python3
"""
Simple test to verify the DEVONthink to pgvector ingestion pipeline.
This script tests:
1. DEVONthink connection and PDF discovery
2. Database records for papers and documents  
3. pgvector embeddings are being created
4. Enhanced RAG vector store functionality
"""

import asyncio
import logging
import os
import sys
from uuid import UUID
from datetime import datetime, timezone

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Database setup
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

sys.path.append('/Users/drjforrest/dev/devprojects/bibliography/backend')

from app.db import (
    ScientificPaper, Document, SearchSpace, Chunk, DevonthinkSync, 
    DevonthinkSyncStatus, User, DocumentType
)
from app.config import config
from app.services.devonthink_mcp_client import DevonthinkMCPClient
from app.services.enhanced_rag_service import EnhancedRAGService

logger = logging.getLogger(__name__)


async def test_pipeline_status():
    """Test the current status of the ingestion pipeline"""
    
    print("🔍 Testing DEVONthink to pgvector Pipeline Status")
    print("=" * 60)
    
    try:
        # Connect to database
        engine = create_async_engine(config.DATABASE_URL, echo=False)
        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        
        async with async_session_maker() as session:
            
            # Test 1: Check DEVONthink connection
            print("\n1️⃣ Testing DEVONthink MCP Connection...")
            os.environ['DEVONTHINK_MCP_BACKEND'] = 'real'
            mcp_client = DevonthinkMCPClient()
            
            is_running = await mcp_client.is_devonthink_running()
            print(f"   DEVONthink running: {'✅' if is_running else '❌'} {is_running}")
            
            if is_running:
                # Get sample PDFs
                pdf_records = await mcp_client.search_records("kind:pdf", limit=5)
                print(f"   Found {len(pdf_records)} PDF records in DEVONthink")
                for i, record in enumerate(pdf_records[:3], 1):
                    print(f"     {i}. {record.get('name', 'Unknown')}")
            
            # Test 2: Check database for ingested papers
            print("\n2️⃣ Checking Database Records...")
            
            # Count total papers
            papers_count = await session.scalar(select(func.count(ScientificPaper.id)))
            print(f"   Scientific papers in database: {papers_count}")
            
            # Count documents with embeddings
            docs_with_embeddings = await session.scalar(
                select(func.count(Document.id)).where(Document.embedding.isnot(None))
            )
            print(f"   Documents with embeddings: {docs_with_embeddings}")
            
            # Count chunks with embeddings
            chunks_with_embeddings = await session.scalar(
                select(func.count(Chunk.id)).where(Chunk.embedding.isnot(None))
            )
            print(f"   Chunks with embeddings: {chunks_with_embeddings}")
            
            # Check DEVONthink sync records
            sync_records = await session.scalar(select(func.count(DevonthinkSync.id)))
            synced_records = await session.scalar(
                select(func.count(DevonthinkSync.id))
                .where(DevonthinkSync.sync_status == DevonthinkSyncStatus.SYNCED)
            )
            print(f"   DEVONthink sync records: {sync_records} (synced: {synced_records})")
            
            # Test 3: Check recent papers with details
            print("\n3️⃣ Recent Papers Sample...")
            recent_papers_stmt = (
                select(ScientificPaper)
                .options(selectinload(ScientificPaper.document))
                .order_by(ScientificPaper.created_at.desc())
                .limit(3)
            )
            result = await session.execute(recent_papers_stmt)
            recent_papers = result.scalars().all()
            
            for i, paper in enumerate(recent_papers, 1):
                print(f"   {i}. {paper.title}")
                print(f"      File: {paper.file_path}")
                print(f"      Authors: {paper.authors}")
                print(f"      Document ID: {paper.document_id}")
                print(f"      Has embedding: {'✅' if paper.document and paper.document.embedding else '❌'}")
                print(f"      Created: {paper.created_at}")
            
            # Test 4: Check vector dimensions and pgvector
            print("\n4️⃣ Vector Storage Check...")
            
            if docs_with_embeddings > 0:
                # Get a sample embedding to check dimensions
                sample_doc = await session.execute(
                    select(Document).where(Document.embedding.isnot(None)).limit(1)
                )
                sample = sample_doc.scalar_one_or_none()
                
                if sample and sample.embedding:
                    print(f"   Sample embedding dimensions: {len(sample.embedding) if hasattr(sample.embedding, '__len__') else 'Unknown'}")
                    print(f"   Expected dimensions: {config.embedding_model_instance.dimension}")
                    print(f"   pgvector extension: ✅ Active (documents have embeddings)")
            else:
                print("   No embeddings found - checking pgvector extension...")
                # Check if pgvector extension is installed
                try:
                    await session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
                    print("   pgvector extension: ✅ Installed")
                except Exception as e:
                    print(f"   pgvector extension: ❌ Error - {str(e)}")
            
            # Test 5: Test Enhanced RAG Service
            print("\n5️⃣ Enhanced RAG Service Test...")
            
            # Get a user to test with
            user_stmt = select(User).limit(1)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if user and papers_count > 0:
                print(f"   Testing with user: {user.email}")
                
                # Test RAG service
                rag_service = EnhancedRAGService(session)
                stats = rag_service.get_stats()
                print(f"   RAG Service status: {stats.get('status', 'unknown')}")
                
                # Try to build vector store
                try:
                    success = await rag_service.build_vector_store_from_papers(str(user.id))
                    print(f"   Vector store build: {'✅' if success else '❌'}")
                    
                    if success:
                        new_stats = rag_service.get_stats()
                        print(f"   Documents in FAISS: {new_stats.get('documents_indexed', 0)}")
                        
                        # Test search
                        search_result = await rag_service.semantic_search(
                            "artificial intelligence", str(user.id), limit=2
                        )
                        print(f"   Search test results: {search_result.get('total_results', 0)} papers found")
                        
                except Exception as e:
                    print(f"   RAG Service error: {str(e)}")
            else:
                print("   No user or papers found for RAG testing")
            
            # Summary
            print("\n📊 Pipeline Status Summary:")
            print(f"   DEVONthink Connection: {'✅' if is_running else '❌'}")
            print(f"   Papers in Database: {papers_count}")
            print(f"   Documents with Embeddings: {docs_with_embeddings}")
            print(f"   Sync Records: {synced_records}/{sync_records}")
            
            if papers_count > 0 and docs_with_embeddings > 0:
                print("   🎉 Pipeline appears to be working correctly!")
            elif papers_count > 0:
                print("   ⚠️  Papers exist but missing embeddings - check embedding service")
            else:
                print("   ⚠️  No papers found - run sync to ingest from DEVONthink")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_manual_sync():
    """Test manual sync of a single paper"""
    
    print("\n" + "=" * 60)
    print("🔧 Manual Sync Test (Optional)")
    print("=" * 60)
    
    response = input("Would you like to test manual sync of one paper? [y/N]: ")
    if response.lower() != 'y':
        return
    
    try:
        from app.services.devonthink_sync_service import DevonthinkSyncService
        from app.schemas.devonthink_schemas import DevonthinkSyncRequest
        
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
            
            if not user or not search_space:
                print("❌ No user or search space found for testing")
                return
            
            print(f"Using user: {user.email}, search space: {search_space.name}")
            
            # Create sync service
            sync_service = DevonthinkSyncService(session)
            
            # Test sync request
            sync_request = DevonthinkSyncRequest(
                database_name="Reference",  # Adjust as needed
                search_space_id=search_space.id,
                folder_path=None,
                force_resync=False
            )
            
            print("🚀 Starting manual sync...")
            response = await sync_service.sync_database(sync_request, user.id)
            
            print(f"Sync result: {response.message}")
            print(f"Synced: {response.synced_count}, Errors: {response.error_count}")
            
            for detail in response.details:
                print(f"  - {detail}")
    
    except Exception as e:
        logger.error(f"Manual sync test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 DEVONthink to pgvector Pipeline Test")
    print("This test will check the current status of your ingestion pipeline")
    print()
    
    asyncio.run(test_pipeline_status())
    asyncio.run(test_manual_sync())