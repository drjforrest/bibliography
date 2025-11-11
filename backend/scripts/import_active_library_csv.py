#!/usr/bin/env python3
"""
Import active_library.csv from DEVONthink export
This script processes the CSV with metadata alongside the PDFs
"""

import asyncio
import csv
import sys
from pathlib import Path
from uuid import UUID
import logging

from sqlalchemy import select
from app.db import get_async_session_context, ScientificPaper, DevonthinkSync, DevonthinkSyncStatus
from app.services.file_storage import FileStorageService
from app.services.pdf_processor import PDFProcessor
from app.services.semantic_search_service import SemanticSearchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def import_csv_records(csv_path: Path, user_id: UUID, search_space_id: int):
    """Import records from active_library.csv"""

    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return

    logger.info(f"Reading CSV from: {csv_path}")

    async with get_async_session_context() as session:
        file_storage = FileStorageService()
        pdf_processor = PDFProcessor(session)
        semantic_search = SemanticSearchService(session)

        processed = 0
        skipped = 0
        errors = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    dt_uuid = row['DEVONthink UUID']
                    name = row['Name']
                    description = row['Single Sentence Description']
                    label = row['RecordLabel']
                    finder_comment = row['Finder Comment']
                    pdf_path = row['PDF Path']

                    # Check if already synced
                    stmt = select(DevonthinkSync).where(DevonthinkSync.dt_source_uuid == dt_uuid)
                    result = await session.execute(stmt)
                    existing_sync = result.scalar_one_or_none()

                    if existing_sync:
                        logger.info(f"Skipping {name} - already synced")
                        skipped += 1
                        continue

                    # Check if PDF file exists
                    pdf_file = Path(pdf_path)
                    if not pdf_file.exists():
                        logger.warning(f"PDF not found: {pdf_path}")
                        errors += 1
                        continue

                    logger.info(f"Processing: {name}")

                    # Store PDF with UUID-based storage
                    stored_path, file_uuid = file_storage.store_pdf(str(pdf_file))

                    # Extract PDF metadata
                    pdf_metadata = pdf_processor.extract_metadata(str(pdf_file))

                    # Create paper record
                    paper = ScientificPaper(
                        title=name or pdf_metadata.get('title', 'Untitled'),
                        authors=pdf_metadata.get('authors'),
                        abstract=description or pdf_metadata.get('abstract'),
                        publication_year=pdf_metadata.get('year'),
                        doi=pdf_metadata.get('doi'),
                        file_path=stored_path,
                        file_uuid=file_uuid,
                        dt_source_uuid=dt_uuid,
                        dt_source_path=finder_comment,  # Store finder comment as source path
                        user_id=user_id,
                        search_space_id=search_space_id,
                        metadata_={
                            'devonthink_label': label,
                            'finder_comment': finder_comment,
                            'original_name': name
                        }
                    )

                    session.add(paper)
                    await session.flush()

                    # Create sync record
                    sync_record = DevonthinkSync(
                        dt_source_uuid=dt_uuid,
                        dt_source_path=finder_comment,
                        local_paper_id=paper.id,
                        user_id=user_id,
                        sync_status=DevonthinkSyncStatus.SYNCED
                    )
                    session.add(sync_record)

                    # Vectorize for semantic search
                    try:
                        await semantic_search.add_paper_to_index(paper)
                    except Exception as e:
                        logger.warning(f"Vectorization failed for {name}: {e}")

                    await session.commit()
                    processed += 1

                    logger.info(f"✓ Imported: {name}")

                except Exception as e:
                    logger.error(f"Error processing record {row.get('Name', 'unknown')}: {e}")
                    errors += 1
                    await session.rollback()
                    continue

        logger.info(f"\nImport complete:")
        logger.info(f"  Processed: {processed}")
        logger.info(f"  Skipped: {skipped}")
        logger.info(f"  Errors: {errors}")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Import active_library.csv from DEVONthink')
    parser.add_argument('csv_path', nargs='?',
                       default='../data/incoming/active_library.csv',
                       help='Path to active_library.csv')
    parser.add_argument('--user-id', default='960bc239-c12e-4559-bb86-a5072df1f4a6',
                       help='User UUID for ownership')
    parser.add_argument('--search-space-id', type=int, default=1,
                       help='Search space ID')

    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    user_id = UUID(args.user_id)

    await import_csv_records(csv_path, user_id, args.search_space_id)


if __name__ == '__main__':
    asyncio.run(main())
