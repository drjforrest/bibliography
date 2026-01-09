#!/usr/bin/env python3
"""
Test script to diagnose thumbnail endpoint issues.
This will help identify why thumbnails aren't loading.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, '.')

from app.db import get_async_session_context
from app.services.thumbnail_generator import ThumbnailGenerator
from app.services.paper_manager import PaperManagerService
from app.config import config


async def test_thumbnail():
    """Test thumbnail generation and access."""
    print("🖼️  Testing Thumbnail Service")
    print("=" * 50)
    
    try:
        async with get_async_session_context() as session:
            from sqlalchemy import select
            from app.db import ScientificPaper
            
            # Get first paper with a file_path
            result = await session.execute(
                select(ScientificPaper)
                .where(ScientificPaper.file_path.isnot(None))
                .limit(1)
            )
            paper = result.scalar_one_or_none()
            
            if not paper:
                print("❌ No papers with file_path found in database")
                return
            
            print(f"✅ Found paper: {paper.title} (ID: {paper.id})")
            print(f"   File Path: {paper.file_path}")
            print()
            
            # Test thumbnail generator
            print("🔧 Testing ThumbnailGenerator...")
            thumbnail_gen = ThumbnailGenerator()
            
            print(f"   Storage Root: {thumbnail_gen.storage_root}")
            print(f"   Thumbnail Root: {thumbnail_gen.thumbnail_root}")
            print(f"   Thumbnail Root Exists: {thumbnail_gen.thumbnail_root.exists()}")
            print()
            
            # Check if PDF exists
            pdf_path = thumbnail_gen.storage_root / paper.file_path
            print(f"📄 PDF File Check:")
            print(f"   Expected PDF Path: {pdf_path}")
            print(f"   PDF Exists: {pdf_path.exists()}")
            if pdf_path.exists():
                print(f"   PDF Size: {pdf_path.stat().st_size / 1024:.2f} KB")
            print()
            
            # Try to generate thumbnail
            print("🎨 Generating thumbnail...")
            try:
                thumbnail_relative_path = thumbnail_gen.generate_thumbnail(
                    paper.file_path, paper.id, force_regenerate=False
                )
                
                if thumbnail_relative_path:
                    print(f"✅ Thumbnail generated: {thumbnail_relative_path}")
                    
                    thumbnail_full_path = thumbnail_gen.get_thumbnail_path(thumbnail_relative_path)
                    print(f"   Full Path: {thumbnail_full_path}")
                    print(f"   Exists: {thumbnail_full_path.exists()}")
                    
                    if thumbnail_full_path.exists():
                        print(f"   Size: {thumbnail_full_path.stat().st_size / 1024:.2f} KB")
                        print()
                        print("✅ Thumbnail is accessible!")
                    else:
                        print("❌ Thumbnail file doesn't exist at expected path")
                else:
                    print("❌ Thumbnail generation returned None")
                    
            except Exception as e:
                print(f"❌ Error generating thumbnail: {str(e)}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_thumbnail())

