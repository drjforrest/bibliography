#!/usr/bin/env python3
"""
Check the current status of PDF imports and migrations.

This script shows:
- How many papers are in the database
- How many are synced from DEVONthink
- CSV file status
- What still needs to be imported

Supports checking both local development and production databases.
"""

import argparse
import asyncio
import csv
import logging
import os
import sys
from pathlib import Path
from uuid import UUID

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config
from app.db import DevonthinkSync, Document, ScientificPaper, SearchSpace, User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def check_database_status(database_url: str = None, label: str = "DATABASE"):
    """Check what's currently in the database."""
    db_url = database_url or config.DATABASE_URL
    engine = create_async_engine(db_url, echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        print("\n" + "=" * 60)
        print(f"{label} STATUS")
        print("=" * 60)

        # Count total papers
        papers_count = await session.scalar(select(func.count(ScientificPaper.id)))
        print(f"\n📄 Scientific Papers: {papers_count}")

        # Count papers with DEVONthink UUID (imported from DEVONthink)
        dt_papers = await session.scalar(
            select(func.count(ScientificPaper.id)).where(
                ScientificPaper.dt_source_uuid.isnot(None)
            )
        )
        print(f"   └─ From DEVONthink: {dt_papers}")

        # Count documents
        docs_count = await session.scalar(select(func.count(Document.id)))
        print(f"\n📚 Documents: {docs_count}")

        # Count documents with embeddings
        docs_with_embeddings = await session.scalar(
            select(func.count(Document.id)).where(Document.embedding.isnot(None))
        )
        print(f"   └─ With embeddings: {docs_with_embeddings}")

        # Count DEVONthink sync records
        sync_count = await session.scalar(select(func.count(DevonthinkSync.id)))
        print(f"\n🔄 DEVONthink Sync Records: {sync_count}")

        # Count by sync status
        from app.db import DevonthinkSyncStatus

        synced_count = await session.scalar(
            select(func.count(DevonthinkSync.id)).where(
                DevonthinkSync.sync_status == DevonthinkSyncStatus.SYNCED
            )
        )
        print(f"   └─ Synced: {synced_count}")

        # Count users
        users_count = await session.scalar(select(func.count(User.id)))
        print(f"\n👤 Users: {users_count}")

        if users_count > 0:
            result = await session.execute(select(User))
            users = result.scalars().all()
            print("   User IDs:")
            for user in users:
                print(f"   └─ {user.email}: {user.id}")

        # Count search spaces
        spaces_count = await session.scalar(select(func.count(SearchSpace.id)))
        print(f"\n🔍 Search Spaces: {spaces_count}")

        if spaces_count > 0:
            result = await session.execute(select(SearchSpace))
            spaces = result.scalars().all()
            for space in spaces:
                print(f"   └─ {space.name} (ID: {space.id})")

    await engine.dispose()


def check_csv_status(csv_path: str):
    """Check CSV file status."""
    print("\n" + "=" * 60)
    print("CSV FILE STATUS")
    print("=" * 60)

    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"\n❌ CSV file not found: {csv_path}")
        print(f"\n💡 Expected locations:")
        print(f"   - ~/PDFs/Evidence_Library_Sync/active_library.csv")
        print(f"   - /data/thumbnail_index.csv")
        return None

    print(f"\n✅ CSV file found: {csv_file}")
    print(f"   Size: {csv_file.stat().st_size / 1024:.1f} KB")

    # Count records in CSV
    try:
        with open(csv_file, "r", encoding="latin-1") as f:
            reader = csv.DictReader(f)
            records = list(reader)
            print(f"\n📊 CSV Records: {len(records)}")

            # Check for PDF paths
            pdf_paths = [r.get("PDF Path", "") for r in records]
            valid_pdfs = [p for p in pdf_paths if p and os.path.exists(p)]
            missing_pdfs = len(pdf_paths) - len(valid_pdfs)

            print(f"   └─ Valid PDF paths: {len(valid_pdfs)}")
            if missing_pdfs > 0:
                print(f"   └─ Missing PDF paths: {missing_pdfs}")

            return len(records)

    except Exception as e:
        print(f"\n❌ Error reading CSV: {e}")
        return None


async def check_pdf_storage():
    """Check PDF storage directory."""
    print("\n" + "=" * 60)
    print("PDF STORAGE STATUS")
    print("=" * 60)

    storage_root = config.PDF_STORAGE_ROOT or "./data/pdfs"
    storage_path = Path(storage_root)

    if not storage_path.exists():
        print(f"\n❌ PDF storage directory not found: {storage_path}")
        return

    # Count PDFs in storage
    pdf_files = list(storage_path.rglob("*.pdf"))
    print(f"\n📁 PDF Storage: {storage_path}")
    print(f"   PDF files: {len(pdf_files)}")

    # Check by year/month
    if pdf_files:
        years = {}
        for pdf in pdf_files:
            parts = pdf.parts
            if len(parts) >= 3:
                year_month = f"{parts[-3]}/{parts[-2]}"
                years[year_month] = years.get(year_month, 0) + 1

        if years:
            print("\n   By year/month:")
            for ym, count in sorted(years.items()):
                print(f"   └─ {ym}: {count} PDFs")


async def check_production_database():
    """Check production database via SSH command."""
    print("\n" + "=" * 60)
    print("PRODUCTION DATABASE STATUS (via SSH)")
    print("=" * 60)

    import subprocess

    try:
        # Use properly escaped command strings for zsh (prevents glob expansion of *)
        # Count scientific papers
        sql = "SELECT COUNT(*) FROM scientific_papers;"
        cmd_str = f"ssh mac-mini '/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod -t -c \"{sql}\"'"
        result = subprocess.run(
            cmd_str, shell=True, capture_output=True, text=True, check=True
        )
        papers_count = int(result.stdout.strip())
        print(f"\n📄 Scientific Papers: {papers_count}")

        # Count DEVONthink papers
        sql = "SELECT COUNT(*) FROM scientific_papers WHERE dt_source_uuid IS NOT NULL;"
        cmd_str = f"ssh mac-mini '/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod -t -c \"{sql}\"'"
        result = subprocess.run(
            cmd_str, shell=True, capture_output=True, text=True, check=True
        )
        dt_papers = int(result.stdout.strip())
        print(f"   └─ From DEVONthink: {dt_papers}")

        # Count documents
        sql = "SELECT COUNT(*) FROM documents;"
        cmd_str = f"ssh mac-mini '/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod -t -c \"{sql}\"'"
        result = subprocess.run(
            cmd_str, shell=True, capture_output=True, text=True, check=True
        )
        docs_count = int(result.stdout.strip())
        print(f"\n📚 Documents: {docs_count}")

        # Count DEVONthink sync records
        sql = "SELECT COUNT(*) FROM devonthink_sync;"
        cmd_str = f"ssh mac-mini '/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod -t -c \"{sql}\"'"
        result = subprocess.run(
            cmd_str, shell=True, capture_output=True, text=True, check=True
        )
        sync_count = int(result.stdout.strip())
        print(f"\n🔄 DEVONthink Sync Records: {sync_count}")

        return {
            "papers": papers_count,
            "dt_papers": dt_papers,
            "documents": docs_count,
            "syncs": sync_count,
        }

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error connecting to production database: {e}")
        print(f"   stderr: {e.stderr}")
        return None
    except FileNotFoundError:
        print(f"\n❌ SSH not available or mac-mini not accessible")
        return None


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Check PDF import status")
    parser.add_argument(
        "--production",
        "-p",
        action="store_true",
        help="Check production database (via SSH)",
    )
    parser.add_argument(
        "--both",
        "-b",
        action="store_true",
        help="Check both local and production databases",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("PDF IMPORT STATUS CHECK")
    print("=" * 60)

    production_stats = None
    local_stats = None

    # Check databases
    if args.both:
        await check_database_status(label="LOCAL DATABASE")
        production_stats = await check_production_database()
    elif args.production:
        production_stats = await check_production_database()
    else:
        # Default: check local database
        await check_database_status(label="LOCAL DATABASE")

    # Check CSV files
    csv_paths = [
        Path.home() / "PDFs" / "Evidence_Library_Sync" / "active_library.csv",
        Path(__file__).parent.parent.parent / "data" / "thumbnail_index.csv",
    ]

    csv_record_count = None
    for csv_path in csv_paths:
        if csv_path.exists():
            csv_record_count = check_csv_status(str(csv_path))
            break

    if csv_record_count is None:
        # Try checking if file exists in alternate locations
        print("\n💡 Tip: Check if CSV exists at:")
        for path in csv_paths:
            print(f"   - {path}")

    # Check PDF storage
    await check_pdf_storage()

    # Get local stats if not already fetched
    if not args.production:
        engine = create_async_engine(config.DATABASE_URL, echo=False)
        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session_maker() as session:
            papers_count = await session.scalar(select(func.count(ScientificPaper.id)))
            dt_papers = await session.scalar(
                select(func.count(ScientificPaper.id)).where(
                    ScientificPaper.dt_source_uuid.isnot(None)
                )
            )
            local_stats = {"papers": papers_count, "dt_papers": dt_papers}
        await engine.dispose()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 60)

    # CSV has ~5288 lines (header + records), so ~5287 records
    expected_total = 4000  # User stated ~4000 records in DEVONthink

    if production_stats:
        print(f"\n📊 Production Database:")
        print(f"   - Papers in database: {production_stats['papers']}")
        print(f"   - From DEVONthink: {production_stats['dt_papers']}")

        remaining_prod = expected_total - production_stats["dt_papers"]
        if remaining_prod > 0:
            print(f"   - Remaining to import: ~{remaining_prod} records")
        else:
            print(f"   ✅ All records imported!")

    if local_stats:
        print(f"\n📊 Local Development Database:")
        print(f"   - Papers in database: {local_stats['papers']}")
        print(f"   - From DEVONthink: {local_stats['dt_papers']}")

        if csv_record_count:
            remaining_local = csv_record_count - local_stats["dt_papers"]
            print(f"   - CSV records: {csv_record_count}")
            print(f"   - Remaining to import: {remaining_local} records")

            if remaining_local > 0:
                print(
                    f"\n✅ Next Step (Local): Import remaining {remaining_local} records from CSV"
                )
                print(
                    f"   Run: python backend/scripts/import_from_devonthink_csv.py \\"
                )
                print(
                    f"     --csv ../../data/thumbnail_index.csv --user-id <your-user-id>"
                )

    # Recommendations
    print(f"\n💡 Recommendations:")

    if production_stats and production_stats["dt_papers"] < expected_total:
        print(
            f"   1. Complete DEVONthink sync on production (~{expected_total - production_stats['dt_papers']} remaining)"
        )
        print(f"      SSH to mac-mini and run sync via API or migration CLI")

    if csv_record_count and csv_record_count > 0:
        print(f"   2. CSV file has {csv_record_count} records (including header)")
        print(f"      Consider importing via CSV for better control")

    print(f"\n   3. For full DEVONthink database sync (~4000 records):")
    print(f"      - Production: Use API endpoint or migration CLI on mac-mini")
    print(f"      - Local: python backend/start_migration_cli.py \\")
    print(f'              --database "BIBLIOGRAPHY" --user-id <your-user-id>')

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
