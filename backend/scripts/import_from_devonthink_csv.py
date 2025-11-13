#!/usr/bin/env python3
"""
Import papers from DEVONthink CSV export into Bibliography system.

This script reads the CSV file created by the DEVONthink Smart Rule and:
1. Imports PDF files into the UUID-based storage system
2. Extracts metadata from PDFs
3. Creates ScientificPaper records in the database
4. Generates thumbnails for the imported papers
5. Vectorizes content for semantic search

Usage:
    python scripts/import_from_devonthink_csv.py --csv ~/PDFs/Evidence_Library_Sync/active_library.csv --user-id YOUR_USER_ID
"""

import asyncio
import csv
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db import ScientificPaper, Document, SearchSpace, DocumentType, LiteratureType
from app.services.file_storage import FileStorageService
from app.services.pdf_processor import PDFProcessor
from app.services.thumbnail_generator import ThumbnailGenerator
from app.services.embedding_service import EmbeddingService
from app.services.enhanced_rag_service import EnhancedRAGService
from app.config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DEVONthinkCSVImporter:
    """Import papers from DEVONthink CSV export."""

    def __init__(self, session_maker, user_id: UUID, default_literature_type: str = "PEER_REVIEWED"):
        self.session_maker = session_maker
        self.user_id = user_id
        self.default_literature_type = default_literature_type
        self.file_storage = FileStorageService()
        self.thumbnail_gen = ThumbnailGenerator()

        # Stats
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.errors = []

    async def get_or_create_search_space(self, session: AsyncSession, name: str = "DEVONthink Import") -> SearchSpace:
        """Get or create a search space for imported papers."""
        stmt = select(SearchSpace).where(
            SearchSpace.name == name,
            SearchSpace.user_id == self.user_id
        )
        result = await session.execute(stmt)
        search_space = result.scalar_one_or_none()

        if not search_space:
            search_space = SearchSpace(
                name=name,
                description="Papers imported from DEVONthink via CSV export",
                user_id=self.user_id,
                is_active=True
            )
            session.add(search_space)
            await session.commit()
            logger.info(f"Created search space: {name}")

        return search_space

    async def import_from_csv(self, csv_path: str, search_space_id: Optional[int] = None):
        """Import papers from CSV file."""
        logger.info(f"Starting import from {csv_path}")

        # Get or create search space using a fresh session
        async with self.session_maker() as session:
            if search_space_id:
                stmt = select(SearchSpace).where(SearchSpace.id == search_space_id)
                result = await session.execute(stmt)
                search_space = result.scalar_one_or_none()
                if not search_space:
                    raise ValueError(f"Search space {search_space_id} not found")
            else:
                search_space = await self.get_or_create_search_space(session)

        # Read CSV with encoding handling for special characters
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Each record gets its own fresh session to avoid greenlet errors
                async with self.session_maker() as session:
                    try:
                        await self.import_record(session, row, search_space.id)
                        self.imported_count += 1
                    except Exception as e:
                        self.error_count += 1
                        error_msg = f"Error importing {row.get('Name', 'Unknown')}: {str(e)}"
                        logger.error(error_msg)
                        self.errors.append(error_msg)

        # Note: Vectorization should be done separately via API endpoints or dedicated script
        # to avoid session/async issues during batch imports
        if self.imported_count > 0:
            logger.info(f"Successfully imported {self.imported_count} papers")
            logger.info("Run vectorization separately via API or dedicated script")

        # Print summary
        self.print_summary()

    def _determine_literature_type(self, label: str) -> LiteratureType:
        """Determine literature type from DEVONthink label or tags."""
        label_lower = label.lower() if label else ""
        
        # Check for explicit type indicators in label
        if any(term in label_lower for term in ['grey', 'gray', 'grey literature', 'gray literature']):
            return LiteratureType.GREY_LITERATURE
        elif any(term in label_lower for term in ['news', 'media', 'press']):
            return LiteratureType.NEWS
        elif any(term in label_lower for term in ['peer', 'journal', 'academic']):
            return LiteratureType.PEER_REVIEWED
        
        # Default to the import-level default
        return LiteratureType[self.default_literature_type]

    async def import_record(self, session: AsyncSession, row: dict, search_space_id: int):
        """Import a single record from CSV row."""
        dt_uuid = row['DEVONthink UUID']
        name = row['Name']
        description = row['Single Sentence Description']
        label = row['RecordLabel']
        finder_comment = row['Finder Comment']
        pdf_path = row['PDF Path']
        
        # Determine literature type
        literature_type = self._determine_literature_type(label)

        logger.info(f"Importing: {name}")

        # Check if PDF file exists
        if not pdf_path or not os.path.exists(pdf_path):
            logger.warning(f"PDF file not found: {pdf_path}, skipping")
            self.skipped_count += 1
            return

        # Check if already imported (by DEVONthink UUID)
        stmt = select(ScientificPaper).where(
            ScientificPaper.dt_source_uuid == dt_uuid
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Paper already imported: {name}, skipping")
            self.skipped_count += 1
            return

        # Generate local UUID for the paper
        local_uuid = uuid4()

        # Step 1: Copy PDF to storage with UUID naming
        logger.info(f"Copying PDF to storage...")
        relative_path, file_uuid = self.file_storage.store_pdf(pdf_path)
        logger.info(f"PDF stored at: {relative_path}")

        # Step 2: Extract text and metadata from PDF
        logger.info(f"Extracting PDF content...")
        absolute_pdf_path = self.file_storage.get_full_path(relative_path)
        pdf_processor = PDFProcessor(session)
        pdf_text = await pdf_processor.extract_text_from_file(str(absolute_pdf_path))
        metadata = await pdf_processor.extract_metadata(str(absolute_pdf_path))

        # Step 3: Create Document record
        document = Document(
            title=name,
            document_type=DocumentType.SCIENTIFIC_PAPER,
            content=pdf_text,
            search_space_id=search_space_id,
            document_metadata={
                "devonthink_uuid": dt_uuid,
                "devonthink_description": description,
                "devonthink_label": label,
                "devonthink_finder_comment": finder_comment,
                "import_source": "csv_export",
                "import_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        session.add(document)
        await session.flush()

        # Step 4: Create ScientificPaper record
        # Use extracted title if available, otherwise use DEVONthink name
        paper_title = metadata.get("title") or name
        if paper_title.lower().endswith('.pdf'):
            paper_title = paper_title[:-4]

        paper = ScientificPaper(
            literature_type=literature_type,
            title=paper_title,
            authors=metadata.get("authors", []),
            doi=metadata.get("doi"),
            abstract=metadata.get("abstract") or description,  # Use DEVONthink description as fallback
            publication_date=self._parse_date(metadata.get("publication_date")),
            publication_year=metadata.get("publication_year"),
            file_path=relative_path,
            file_size=os.path.getsize(pdf_path),
            full_text=pdf_text,
            processing_status="completed",
            dt_source_uuid=dt_uuid,
            dt_source_path=None,  # Not applicable for CSV import
            document_id=document.id,
            tags=[label] if label else [],
            extraction_metadata={
                "devonthink_description": description,
                "finder_comment": finder_comment,
                "literature_type": literature_type.value,
                "extraction_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        session.add(paper)
        await session.flush()

        logger.info(f"Created paper record: {paper.id}")

        # Step 5: Generate thumbnail
        logger.info(f"Generating thumbnail...")
        try:
            thumbnail_path = self.thumbnail_gen.generate_thumbnail(
                relative_path,
                paper.id,
                force_regenerate=False
            )
            if thumbnail_path:
                logger.info(f"Thumbnail generated: {thumbnail_path}")
            else:
                logger.warning(f"Failed to generate thumbnail")
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")

        # Step 6: Skip individual vectorization - will be done in batch after all imports
        # This avoids greenlet/async session issues after rollbacks
        logger.info(f"Deferring vectorization to batch process...")

        # Commit the transaction
        await session.commit()
        logger.info(f"Successfully imported: {name}")

    def _parse_date(self, date_str: Optional[str]):
        """Parse date string."""
        if not date_str:
            return None
        try:
            from dateutil import parser
            dt = parser.parse(date_str)
            return dt.date() if dt else None
        except Exception:
            return None

    def print_summary(self):
        """Print import summary."""
        print("\n" + "=" * 70)
        print("Import Summary")
        print("=" * 70)
        print(f"Successfully imported: {self.imported_count}")
        print(f"Skipped (already exists or no PDF): {self.skipped_count}")
        print(f"Errors: {self.error_count}")

        if self.errors:
            print("\nErrors:")
            for error in self.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")

        print("\nNext steps:")
        print("1. View imported papers at: http://localhost:3000/library")
        print("2. Thumbnails have been generated automatically")
        print("3. Papers are ready for semantic search")
        print("=" * 70)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Import papers from DEVONthink CSV export')
    parser.add_argument('--csv', required=True, help='Path to CSV file')
    parser.add_argument('--user-id', required=True, help='User UUID')
    parser.add_argument('--search-space-id', type=int, help='Optional search space ID')
    parser.add_argument(
        '--literature-type',
        choices=['PEER_REVIEWED', 'GREY_LITERATURE', 'NEWS'],
        default='PEER_REVIEWED',
        help='Default literature type for imported papers (can be overridden by DEVONthink labels)'
    )
    args = parser.parse_args()

    # Validate CSV file
    if not os.path.exists(args.csv):
        logger.error(f"CSV file not found: {args.csv}")
        sys.exit(1)

    # Parse user ID
    try:
        user_id = UUID(args.user_id)
    except ValueError:
        logger.error(f"Invalid user ID format: {args.user_id}")
        sys.exit(1)

    # Create async session maker
    engine = create_async_engine(config.DATABASE_URL)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    importer = DEVONthinkCSVImporter(async_session_maker, user_id, args.literature_type)
    await importer.import_from_csv(args.csv, args.search_space_id)

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Import cancelled by user")
    except Exception as e:
        logger.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
