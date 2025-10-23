"""
Import DEVONthink CSV data into Bibliography database.

This script reads the thumbnail_index.csv file and creates ScientificPaper records
for each entry, linking to thumbnails and preserving DEVONthink metadata.
"""
import asyncio
import csv
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session_context, ScientificPaper, Document, SearchSpace, User
from app.db import DocumentType
from app.config import config


async def get_or_create_search_space(session: AsyncSession, user_id: str) -> SearchSpace:
    """Get or create a search space for imported papers."""
    stmt = select(SearchSpace).where(
        SearchSpace.user_id == user_id,
        SearchSpace.name == "DEVONthink Import"
    )
    result = await session.execute(stmt)
    search_space = result.scalar_one_or_none()

    if not search_space:
        search_space = SearchSpace(
            name="DEVONthink Import",
            description="Papers imported from DEVONthink thumbnail index",
            user_id=user_id
        )
        session.add(search_space)
        await session.commit()
        await session.refresh(search_space)

    return search_space


async def paper_exists(session: AsyncSession, dt_uuid: str) -> bool:
    """Check if a paper with this DEVONthink UUID already exists."""
    stmt = select(ScientificPaper).where(ScientificPaper.dt_source_uuid == dt_uuid)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def import_record(
    session: AsyncSession,
    row: dict,
    search_space_id: int,
    thumbnail_base_path: Path,
    dry_run: bool = False
) -> Optional[ScientificPaper]:
    """Import a single record from the CSV."""
    dt_uuid = row['DEVONthink UUID'].strip()
    name = row['Name'].strip()
    description = row['Single Sentence Description'].strip()
    thumbnail_path = row.get('Thumbnail Path', '').strip()

    # Skip if already exists
    if await paper_exists(session, dt_uuid):
        print(f"  ⏩ Skipping {name[:50]} - already exists")
        return None

    # Build thumbnail path if provided
    thumbnail_rel_path = None
    if thumbnail_path:
        # Construct path relative to data directory
        thumbnail_rel_path = f"DEVONthink_Thumbnails/{dt_uuid}.png"
        full_thumbnail_path = thumbnail_base_path / f"{dt_uuid}.png"
        if not full_thumbnail_path.exists():
            print(f"  ⚠️  Thumbnail not found: {full_thumbnail_path}")
            thumbnail_rel_path = None

    if dry_run:
        print(f"  [DRY RUN] Would import: {name[:60]}")
        return None

    # Create Document first (required for ScientificPaper)
    document = Document(
        title=name,
        document_type=DocumentType.SCIENTIFIC_PAPER,
        document_metadata={
            "source": "devonthink_csv_import",
            "devonthink_uuid": dt_uuid,
            "has_thumbnail": thumbnail_rel_path is not None
        },
        content=description if description else name,  # Use description as content
        search_space_id=search_space_id
    )
    session.add(document)
    await session.flush()  # Get document ID

    # Create ScientificPaper
    paper = ScientificPaper(
        title=name,
        authors=[],  # Will need to be extracted/added later
        abstract=description if description else None,
        processing_status="completed",  # Mark as completed since we have the data
        file_path=f"devonthink_import/{dt_uuid}",  # Placeholder path
        dt_source_uuid=dt_uuid,
        dt_source_path=thumbnail_rel_path,  # Store thumbnail path here
        document_id=document.id,
        confidence_score=0.9 if description else 0.5  # Higher confidence if we have description
    )

    session.add(paper)
    await session.commit()
    await session.refresh(paper)

    print(f"  ✓ Imported: {name[:60]}")
    return paper


async def main():
    """Main import function."""
    print("=" * 70)
    print("📚 DEVONthink CSV Import Tool")
    print("=" * 70)

    # Configuration
    csv_path = Path(__file__).parent.parent.parent / "data" / "thumbnail_index.csv"
    thumbnail_base = Path(__file__).parent.parent.parent / "data" / "DEVONthink_Thumbnails"

    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return

    if not thumbnail_base.exists():
        print(f"⚠️  Thumbnail directory not found: {thumbnail_base}")
        print("   Continuing without thumbnails...")

    # Parse command line args
    dry_run = "--dry-run" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")

    # Read CSV
    print(f"\n📄 Reading CSV: {csv_path}")
    records = []
    with open(csv_path, 'r', encoding='latin-1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
            if limit and len(records) >= limit:
                break

    print(f"   Found {len(records)} records to process")

    # Get database session
    async with get_async_session_context() as session:
        # Get first user (for demo purposes)
        stmt = select(User).limit(1)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            print("❌ No users found in database. Please create a user first.")
            print("   Run: cd backend && python -c 'from app.db import *; import asyncio; asyncio.run(create_db_and_tables())'")
            return

        print(f"   Using user: {user.email}")

        # Get or create search space
        search_space = await get_or_create_search_space(session, str(user.id))
        print(f"   Using search space: {search_space.name} (ID: {search_space.id})")

        # Import records
        print(f"\n📥 Importing records...")
        print("-" * 70)

        imported_count = 0
        skipped_count = 0
        error_count = 0

        for i, row in enumerate(records, 1):
            try:
                result = await import_record(
                    session,
                    row,
                    search_space.id,
                    thumbnail_base,
                    dry_run=dry_run
                )
                if result:
                    imported_count += 1
                else:
                    skipped_count += 1

                # Progress indicator
                if i % 10 == 0:
                    print(f"   Progress: {i}/{len(records)} records processed")

            except Exception as e:
                error_count += 1
                print(f"  ❌ Error importing record {i}: {e}")
                if "--verbose" in sys.argv:
                    import traceback
                    traceback.print_exc()

        print("-" * 70)
        print(f"\n✅ Import complete!")
        print(f"   Imported: {imported_count}")
        print(f"   Skipped:  {skipped_count}")
        print(f"   Errors:   {error_count}")
        print(f"   Total:    {len(records)}")

        if dry_run:
            print(f"\n💡 This was a dry run. Run without --dry-run to actually import.")
        else:
            print(f"\n🎉 Successfully imported {imported_count} papers!")
            print(f"   View them at: http://localhost:3000")


if __name__ == "__main__":
    print("\nUsage:")
    print("  python import_devonthink_csv.py              # Import all records")
    print("  python import_devonthink_csv.py --dry-run    # Test without importing")
    print("  python import_devonthink_csv.py --limit 10   # Import only first 10")
    print("  python import_devonthink_csv.py --verbose    # Show detailed errors")
    print()

    asyncio.run(main())
