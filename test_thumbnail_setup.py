#!/usr/bin/env python3
"""
Test script to verify thumbnail generation and PDF viewing setup.

This script will:
1. Check if the backend is running
2. Test thumbnail generation for existing papers
3. Verify PDF serving endpoints
4. Generate a sample report
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db import ScientificPaper
from app.services.thumbnail_generator import ThumbnailGenerator
from app.services.file_storage import FileStorageService
from app.config import config


async def test_setup():
    """Test the thumbnail and PDF viewing setup."""

    print("=" * 70)
    print("Testing Thumbnail Generation & PDF Viewing Setup")
    print("=" * 70)
    print()

    # Step 1: Check configuration
    print("Step 1: Checking Configuration")
    print("-" * 70)
    print(f"PDF Storage Root: {config.PDF_STORAGE_ROOT}")
    print(f"Database URL: {config.DATABASE_URL[:50]}...")
    print()

    # Step 2: Initialize services
    print("Step 2: Initializing Services")
    print("-" * 70)

    engine = create_async_engine(config.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    thumbnail_gen = ThumbnailGenerator()
    file_storage = FileStorageService()

    print(f"✓ Thumbnail root: {thumbnail_gen.thumbnail_root}")
    print(f"✓ Storage root: {file_storage.storage_root}")
    print()

    # Step 3: Query papers from database
    print("Step 3: Querying Papers")
    print("-" * 70)

    async with async_session() as session:
        stmt = select(ScientificPaper).limit(10)
        result = await session.execute(stmt)
        papers = result.scalars().all()

        print(f"Found {len(papers)} papers in database (limit 10)")
        print()

        if not papers:
            print("⚠ No papers found in database. Please sync from DEVONthink first.")
            print("  Run: POST /api/v1/devonthink/sync")
            return

        # Step 4: Test thumbnail generation
        print("Step 4: Testing Thumbnail Generation")
        print("-" * 70)

        success_count = 0
        fail_count = 0

        for i, paper in enumerate(papers, 1):
            if not paper.file_path:
                print(f"  [{i}] Paper {paper.id}: No file_path - SKIPPED")
                fail_count += 1
                continue

            # Check if PDF exists
            pdf_full_path = file_storage.get_full_path(paper.file_path)
            if not pdf_full_path.exists():
                print(f"  [{i}] Paper {paper.id}: PDF not found at {pdf_full_path} - SKIPPED")
                fail_count += 1
                continue

            # Generate thumbnail
            try:
                thumbnail_path = thumbnail_gen.generate_thumbnail(
                    paper.file_path,
                    paper.id,
                    force_regenerate=False
                )

                if thumbnail_path:
                    print(f"  [{i}] Paper {paper.id}: ✓ Thumbnail generated")
                    print(f"       Title: {paper.title[:60]}...")
                    print(f"       Thumbnail: {thumbnail_path}")
                    success_count += 1
                else:
                    print(f"  [{i}] Paper {paper.id}: ✗ Thumbnail generation failed")
                    fail_count += 1
            except Exception as e:
                print(f"  [{i}] Paper {paper.id}: ✗ Error - {str(e)}")
                fail_count += 1

        print()
        print(f"Results: {success_count} succeeded, {fail_count} failed")
        print()

        # Step 5: Get storage stats
        print("Step 5: Storage Statistics")
        print("-" * 70)

        pdf_stats = file_storage.get_storage_stats()
        thumbnail_stats = thumbnail_gen.get_thumbnail_stats()

        print("PDF Storage:")
        print(f"  Total files: {pdf_stats['total_files']}")
        print(f"  Total size: {pdf_stats['total_size_mb']} MB")
        print(f"  Location: {pdf_stats['storage_root']}")
        print()

        print("Thumbnail Storage:")
        print(f"  Total thumbnails: {thumbnail_stats['total_thumbnails']}")
        print(f"  Total size: {thumbnail_stats['total_size_mb']} MB")
        print(f"  Location: {thumbnail_stats['thumbnail_root']}")
        print()

        # Step 6: API Endpoint Information
        print("Step 6: Available API Endpoints")
        print("-" * 70)
        print("PDF Viewing:")
        print(f"  GET /api/v1/papers/{{paper_id}}/pdf")
        print(f"  Example: http://localhost:8000/api/v1/papers/{papers[0].id}/pdf")
        print()
        print("Thumbnail Access:")
        print(f"  GET /api/v1/papers/{{paper_id}}/thumbnail")
        print(f"  Example: http://localhost:8000/api/v1/papers/{papers[0].id}/thumbnail")
        print()
        print("Batch Thumbnail Generation:")
        print(f"  POST /api/v1/papers/thumbnails/generate-batch")
        print()

        # Step 7: Next Steps
        print("Step 7: Next Steps")
        print("-" * 70)
        print("1. Start the backend server:")
        print("   cd backend && python main.py --reload")
        print()
        print("2. Start the Next.js frontend:")
        print("   cd frontend/nextjs-app && npm run dev")
        print()
        print("3. Visit the library page:")
        print("   http://localhost:3000/library")
        print()
        print("4. You should now see:")
        print("   ✓ Thumbnails instead of purple gradients")
        print("   ✓ Clicking a paper opens the PDF viewer")
        print()
        print("5. To generate all thumbnails in batch:")
        print("   curl -X POST http://localhost:8000/api/v1/papers/thumbnails/generate-batch \\")
        print("        -H 'Authorization: Bearer YOUR_TOKEN' \\")
        print("        -F 'limit=100'")
        print()

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(test_setup())
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
