#!/usr/bin/env python3
"""
Test pgvector embeddings with Ollama nomic-text-embed
"""

import asyncio
import logging
import os
import sys
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sys.path.append('/Users/drjforrest/dev/devprojects/bibliography/backend')

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db import User, SearchSpace, Document, Chunk, ScientificPaper
from app.config import config
from app.services.embedding_service import EmbeddingService
from app.services.devonthink_sync_service import DevonthinkSyncService

logger = logging.getLogger(__name__)

async def test_embedding_config():
    """Test the new embedding configuration"""
    
    print("🔧 Testing Ollama nomic-text-embed Configuration")
    print("=" * 60)
    
    try:
        print(f"✅ Embedding Model: {config.EMBEDDING_MODEL}")
        print(f"✅ Embedding Dimension: {getattr(config.embedding_model_instance, 'dimension', 'unknown')}")
        print(f"✅ Chunker Type: {type(config.chunker_instance).__name__}")
        
        # Test basic embedding generation
        print("\n🧪 Testing embedding generation...")
        test_text = "This is a test document about artificial intelligence and machine learning."
        
        # Use the correct method for Chonkie SentenceTransformerEmbeddings
        embedding = await asyncio.to_thread(
            config.embedding_model_instance.embed,
            test_text
        )
        
        print(f"✅ Generated embedding with {len(embedding)} dimensions")
        print(f"   Sample values: {embedding[:5]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding configuration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_embedding_service():
    """Test the embedding service"""
    
    print("\n🔧 Testing Embedding Service")
    print("=" * 60)
    
    try:
        # Database setup
        engine = create_async_engine(config.DATABASE_URL, echo=False)
        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        
        async with async_session_maker() as session:
            embedding_service = EmbeddingService(session)
            
            # Test embedding service stats
            stats = embedding_service.get_embedding_stats()
            print(f"✅ Embedding Service Stats:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
            
            # Test single text embedding
            test_text = "Neural networks are computational models inspired by biological neural networks."
            embedding = await embedding_service.embed_text(test_text)
            
            if embedding:
                print(f"✅ Single text embedding: {len(embedding)} dimensions")
                print(f"   Sample: {embedding[:3]}...")
            else:
                print("❌ Failed to generate single text embedding")
                return False
            
            # Test batch embedding
            test_texts = [
                "Machine learning is a subset of artificial intelligence.",
                "Deep learning uses neural networks with multiple layers.",
                "Natural language processing enables computers to understand text."
            ]
            
            embeddings = await embedding_service.embed_texts(test_texts)
            
            if embeddings is not None and len(embeddings) == len(test_texts):
                print(f"✅ Batch embedding: {len(embeddings)} embeddings generated")
                print(f"   Each with {len(embeddings[0])} dimensions")
            else:
                print(f"❌ Batch embedding failed: got {len(embeddings) if embeddings else 0} embeddings")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ Embedding service test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_populate_missing_embeddings():
    """Test populating embeddings for existing documents"""
    
    print("\n🔧 Testing Embedding Population for Existing Documents")
    print("=" * 60)
    
    try:
        # Database setup
        engine = create_async_engine(config.DATABASE_URL, echo=False)
        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        
        async with async_session_maker() as session:
            # Check current embedding status
            docs_without_embeddings = await session.scalar(
                select(func.count(Document.id)).where(Document.embedding.is_(None))
            )
            
            chunks_without_embeddings = await session.scalar(
                select(func.count(Chunk.id)).where(Chunk.embedding.is_(None))
            )
            
            print(f"📊 Current Status:")
            print(f"   Documents without embeddings: {docs_without_embeddings}")
            print(f"   Chunks without embeddings: {chunks_without_embeddings}")
            
            if docs_without_embeddings == 0:
                print("✅ All documents already have embeddings!")
                return True
            
            # Test embedding population (limit to 3 documents for testing)
            embedding_service = EmbeddingService(session)
            print(f"\n🚀 Populating embeddings for up to 3 documents...")
            
            stats = await embedding_service.populate_missing_embeddings(limit=3)
            
            print(f"\n📊 Embedding Population Results:")
            print(f"   Documents processed: {stats['documents_processed']}")
            print(f"   Documents embedded: {stats['documents_embedded']}")
            print(f"   Chunks created: {stats['chunks_created']}")
            print(f"   Chunks embedded: {stats['chunks_embedded']}")
            print(f"   Errors: {stats['errors']}")
            
            # Check updated status
            docs_with_embeddings = await session.scalar(
                select(func.count(Document.id)).where(Document.embedding.isnot(None))
            )
            
            chunks_with_embeddings = await session.scalar(
                select(func.count(Chunk.id)).where(Chunk.embedding.isnot(None))
            )
            
            print(f"\n📊 Updated Status:")
            print(f"   Documents with embeddings: {docs_with_embeddings}")
            print(f"   Chunks with embeddings: {chunks_with_embeddings}")
            
            if stats['documents_embedded'] > 0 or stats['chunks_created'] > 0:
                print("✅ Successfully populated some embeddings!")
                return True
            else:
                print("⚠️  No new embeddings were created")
                return False
                
    except Exception as e:
        print(f"❌ Embedding population test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_new_sync_with_embeddings():
    """Test syncing a new document with embeddings"""
    
    print("\n🔧 Testing New Document Sync with Embeddings")
    print("=" * 60)
    
    response = input("Would you like to test syncing a new document from DEVONthink with embeddings? [y/N]: ")
    if response.lower() != 'y':
        print("Skipping new document sync test")
        return True
    
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
            
            # Create sync request
            from app.schemas.devonthink_schemas import DevonthinkSyncRequest
            sync_request = DevonthinkSyncRequest(
                database_name="Reference",
                search_space_id=search_space.id,
                folder_path=None,
                force_resync=False  # Don't duplicate existing documents
            )
            
            print(f"\n🚀 Starting sync with new embedding pipeline...")
            
            # Get count before sync
            docs_before = await session.scalar(select(func.count(Document.id)))
            chunks_before = await session.scalar(select(func.count(Chunk.id)))
            
            response = await sync_service.sync_database(sync_request, user.id)
            
            # Get count after sync
            docs_after = await session.scalar(select(func.count(Document.id)))
            chunks_after = await session.scalar(select(func.count(Chunk.id)))
            
            print(f"\n📊 Sync Results:")
            print(f"   Success: {response.success}")
            print(f"   Message: {response.message}")
            print(f"   Synced: {response.synced_count}")
            print(f"   Documents: {docs_before} -> {docs_after} (+{docs_after - docs_before})")
            print(f"   Chunks: {chunks_before} -> {chunks_after} (+{chunks_after - chunks_before})")
            
            # Check if new documents have embeddings
            if response.synced_count > 0:
                # Get the most recent documents
                recent_docs_stmt = (
                    select(Document)
                    .order_by(Document.created_at.desc())
                    .limit(response.synced_count)
                )
                recent_docs_result = await session.execute(recent_docs_stmt)
                recent_docs = recent_docs_result.scalars().all()
                
                embedded_docs = sum(1 for doc in recent_docs if doc.embedding)
                print(f"   New docs with embeddings: {embedded_docs}/{len(recent_docs)}")
                
                if embedded_docs > 0:
                    print("✅ New documents were successfully embedded with pgvector!")
                    return True
                else:
                    print("❌ New documents were not embedded")
                    return False
            else:
                print("ℹ️  No new documents were synced (likely all already exist)")
                return True
                
    except Exception as e:
        print(f"❌ New document sync test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all embedding tests"""
    
    print("🧪 pgvector + Ollama nomic-text-embed Integration Test")
    print("=" * 80)
    
    # Test 1: Configuration
    config_ok = await test_embedding_config()
    if not config_ok:
        print("❌ Configuration test failed - cannot continue")
        return
    
    # Test 2: Embedding Service
    service_ok = await test_embedding_service()
    if not service_ok:
        print("❌ Embedding service test failed - cannot continue")
        return
    
    # Test 3: Population of existing documents
    populate_ok = await test_populate_missing_embeddings()
    
    # Test 4: New document sync
    sync_ok = await test_new_sync_with_embeddings()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Test Summary:")
    print(f"   ✅ Configuration: {'PASS' if config_ok else 'FAIL'}")
    print(f"   ✅ Embedding Service: {'PASS' if service_ok else 'FAIL'}")
    print(f"   ✅ Population: {'PASS' if populate_ok else 'FAIL'}")
    print(f"   ✅ New Sync: {'PASS' if sync_ok else 'FAIL'}")
    
    if config_ok and service_ok and (populate_ok or sync_ok):
        print("\n🎉 pgvector + Ollama integration is working!")
        print("   Your semantic search pipeline now uses nomic-text-embed")
        print("   Documents and chunks have persistent pgvector embeddings")
    else:
        print("\n⚠️  Some tests failed - check the logs above")

if __name__ == "__main__":
    print("📝 Prerequisites:")
    print("   1. Ollama is running (ollama serve)")
    print("   2. nomic-embed-text model is available (ollama pull nomic-embed-text)")
    print("   3. PostgreSQL with pgvector extension")
    print("   4. DEVONthink is running (for new sync test)")
    print()
    
    asyncio.run(main())