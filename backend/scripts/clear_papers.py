#!/usr/bin/env python3
"""
Clear all papers from the database for fresh testing.

This script will:
1. Delete all ScientificPaper records
2. Delete all Document records
3. Delete all DevonthinkSync records (if any)
4. Optionally delete PDF files and thumbnails from disk

Usage:
    python scripts/clear_papers.py --user-id YOUR_USER_ID [--delete-files]
"""

import asyncio
import logging
import sys
import shutil
from pathlib import Path
from uuid import UUID

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db import ScientificPaper, Document, SearchSpace, DevonthinkSync
from app.services.file_storage import FileStorageService
from app.services.thumbnail_generator import ThumbnailGenerator
from app.config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def clear_papers(user_id: UUID, delete_files: bool = False):
    """Clear all papers for a user."""

    logger.info("=" * 70)
    logger.info("Clearing Papers from Database")
    logger.info("=" * 70)

    # Create async session
    engine = create_async_engine(config.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Step 1: Get search spaces for user
        logger.info(f"Finding search spaces for user {user_id}...")
        stmt = select(SearchSpace).where(SearchSpace.user_id == user_id)
        result = await session.execute(stmt)
        search_spaces = result.scalars().all()

        if not search_spaces:
            logger.warning("No search spaces found for user")
            return

        search_space_ids = [s.id for s in search_spaces]
        logger.info(f"Found {len(search_spaces)} search spaces: {[s.name for s in search_spaces]}")

        # Step 2: Count papers to be deleted
        stmt = select(ScientificPaper).join(
            Document, Document.id == ScientificPaper.document_id
        ).where(Document.search_space_id.in_(search_space_ids))
        result = await session.execute(stmt)
        papers = result.scalars().all()

        logger.info(f"Found {len(papers)} papers to delete")

        if len(papers) == 0:
            logger.info("No papers to delete")
            await engine.dispose()
            return

        # Confirm deletion
        print()
        response = input(f"Are you sure you want to delete {len(papers)} papers? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Deletion cancelled")
            await engine.dispose()
            return

        # Step 3: Delete papers (cascades to documents)
        logger.info("Deleting papers...")
        document_ids = [p.document_id for p in papers]

        # Delete ScientificPaper records
        stmt = delete(ScientificPaper).where(
            ScientificPaper.document_id.in_(document_ids)
        )
        result = await session.execute(stmt)
        logger.info(f"Deleted {result.rowcount} ScientificPaper records")

        # Delete Document records
        stmt = delete(Document).where(
            Document.id.in_(document_ids)
        )
        result = await session.execute(stmt)
        logger.info(f"Deleted {result.rowcount} Document records")

        # Delete DevonthinkSync records (if any)
        stmt = delete(DevonthinkSync).where(DevonthinkSync.user_id == user_id)
        result = await session.execute(stmt)
        if result.rowcount > 0:
            logger.info(f"Deleted {result.rowcount} DevonthinkSync records")

        await session.commit()
        logger.info("Database cleared successfully")

        # Step 4: Optionally delete files
        if delete_files:
            logger.info("\nDeleting PDF files and thumbnails from disk...")

            file_storage = FileStorageService()
            thumbnail_gen = ThumbnailGenerator()

            # Get stats before deletion
            pdf_stats = file_storage.get_storage_stats()
            thumb_stats = thumbnail_gen.get_thumbnail_stats()

            logger.info(f"Current storage: {pdf_stats['total_files']} PDFs ({pdf_stats['total_size_mb']} MB)")
            logger.info(f"Current storage: {thumb_stats['total_thumbnails']} thumbnails ({thumb_stats['total_size_mb']} MB)")

            # Confirm file deletion
            print()
            response = input("Are you sure you want to delete all PDF and thumbnail files? (yes/no): ")
            if response.lower() == 'yes':
                # Delete PDFs
                if file_storage.storage_root.exists():
                    shutil.rmtree(file_storage.storage_root)
                    file_storage.storage_root.mkdir(parents=True, exist_ok=True)
                    logger.info("Deleted all PDF files")

                # Delete thumbnails
                if thumbnail_gen.thumbnail_root.exists():
                    shutil.rmtree(thumbnail_gen.thumbnail_root)
                    thumbnail_gen.thumbnail_root.mkdir(parents=True, exist_ok=True)
                    logger.info("Deleted all thumbnail files")
            else:
                logger.info("File deletion cancelled - database cleared but files remain")

    await engine.dispose()

    logger.info("\n" + "=" * 70)
    logger.info("Clear Complete")
    logger.info("=" * 70)
    logger.info("\nNext steps:")
    logger.info("1. Run your DEVONthink Smart Rule on selected records")
    logger.info("2. Import papers:")
    logger.info(f"   python backend/scripts/import_from_devonthink_csv.py \\")
    logger.info(f"     --csv ~/PDFs/Evidence_Library_Sync/active_library.csv \\")
    logger.info(f"     --user-id {user_id}")
    logger.info("=" * 70)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Clear all papers from database')
    parser.add_argument('--user-id', required=True, help='User UUID')
    parser.add_argument('--delete-files', action='store_true',
                       help='Also delete PDF and thumbnail files from disk')
    args = parser.parse_args()

    # Parse user ID
    try:
        user_id = UUID(args.user_id)
    except ValueError:
        logger.error(f"Invalid user ID format: {args.user_id}")
        sys.exit(1)

    await clear_papers(user_id, args.delete_files)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
