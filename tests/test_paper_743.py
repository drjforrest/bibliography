#!/usr/bin/env python3
"""
Quick test to verify that paper 743's data (title and summary) is properly accessible
via the PaperResponse schema after our fixes.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.paper_manager import PaperManagerService
from app.schemas.papers import PaperResponse


async def test_paper_743():
    """Test that paper 743's data is properly loaded."""
    
    # Connect to database
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/bibliography_db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        paper_manager = PaperManagerService(session)
        
        # Get paper 743
        print("Fetching paper 743...")
        paper = await paper_manager.get_paper_by_id(743)
        
        if not paper:
            print("❌ Paper 743 not found!")
            return False
        
        print("\n✅ Paper found in database")
        print(f"   Database ID: {paper.id}")
        print(f"   Scientific Paper Title: {paper.title}")
        
        # Check if document is loaded
        if hasattr(paper, 'document') and paper.document:
            print(f"   Document Title: {paper.document.title}")
            print(f"   Document has metadata: {bool(paper.document.document_metadata)}")
            if paper.document.document_metadata:
                has_desc = 'devonthink_description' in paper.document.document_metadata
                print(f"   Has devonthink_description: {has_desc}")
                if has_desc:
                    desc_len = len(paper.document.document_metadata['devonthink_description'])
                    print(f"   Description length: {desc_len} chars")
        else:
            print("   ⚠️  Document relationship not loaded!")
        
        # Convert to API response
        print("\nConverting to PaperResponse...")
        try:
            response = PaperResponse.from_orm(paper)
            
            print("\n✅ PaperResponse created successfully")
            print(f"   Response Title: {response.title}")
            print(f"   Has Summary: {bool(response.summary)}")
            if response.summary:
                summary_len = len(response.summary)
                print(f"   Summary length: {summary_len} chars")
                print("\n   Summary preview (first 200 chars):")
                print(f"   {response.summary[:200]}...")
            else:
                print("   ❌ No summary in response!")
            
            return bool(response.summary) and response.title != "JOURNAL OF MEDICAL INTERNET RESEARCH"
            
        except Exception as e:
            print(f"❌ Error creating PaperResponse: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = asyncio.run(test_paper_743())
    sys.exit(0 if success else 1)
