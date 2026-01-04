#!/usr/bin/env python3
"""
Export papers with missing PDF files to CSV and optionally delete them.

This script:
1. Finds all papers with missing PDF files
2. Exports them to a CSV file
3. Optionally deletes them from the database

Usage:
    # Export to CSV only (dry-run)
    python backend/scripts/export_and_delete_missing_papers.py --export-only

    # Export to CSV and delete
    python backend/scripts/export_and_delete_missing_papers.py

    # Custom CSV output path
    python backend/scripts/export_and_delete_missing_papers.py --output missing_papers.csv
"""

import asyncio
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Load .env before importing config
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Set dummy CLERK vars to avoid config errors
if not os.getenv("CLERK_ISSUER"):
    os.environ["CLERK_ISSUER"] = "https://dummy.clerk.accounts.dev"
if not os.getenv("CLERK_JWKS_URL"):
    os.environ["CLERK_JWKS_URL"] = (
        "https://dummy.clerk.accounts.dev/.well-known/jwks.json"
    )

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config
from app.db import Document, ScientificPaper, get_async_session_context
from app.services.file_storage import FileStorageService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


async def find_missing_files(
    session: AsyncSession, file_storage: FileStorageService
) -> List[ScientificPaper]:
    """Find papers with missing PDF files."""
    result = await session.execute(
        select(ScientificPaper).where(ScientificPaper.file_path.isnot(None))
    )
    papers = result.scalars().all()

    missing = []
    for paper in papers:
        try:
            full_path = file_storage.get_full_path(paper.file_path)
            if not full_path.exists():
                missing.append(paper)
        except Exception:
            missing.append(paper)

    return missing


async def export_to_csv(papers: List[ScientificPaper], output_path: Path):
    """Export papers to CSV file."""
    print(f"📝 Exporting {len(papers)} papers to {output_path}...")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "paper_id",
                "title",
                "file_path",
                "dt_source_uuid",
                "doi",
                "created_at",
            ]
        )

        for paper in papers:
            writer.writerow(
                [
                    paper.id,
                    paper.title or "",
                    paper.file_path or "",
                    paper.dt_source_uuid or "",
                    paper.doi or "",
                    paper.created_at.isoformat() if paper.created_at else "",
                ]
            )

    print(f"✅ Exported {len(papers)} papers to {output_path}")


async def delete_papers(session: AsyncSession, papers: List[ScientificPaper]):
    """Delete papers and their associated documents from the database using raw SQL."""
    from sqlalchemy import text

    print(f"🗑️  Deleting {len(papers)} papers from database...")

    paper_ids = [paper.id for paper in papers]
    document_ids = [paper.document_id for paper in papers if paper.document_id]

    deleted_count = 0

    try:
        # Delete chunks first (they reference documents)
        if document_ids:
            result = await session.execute(
                text("DELETE FROM chunks WHERE document_id = ANY(:ids)"),
                {"ids": document_ids},
            )
            print(f"  Deleted {result.rowcount} chunks")

        # Delete documents
        if document_ids:
            result = await session.execute(
                text("DELETE FROM documents WHERE id = ANY(:ids)"),
                {"ids": document_ids},
            )
            print(f"  Deleted {result.rowcount} documents")

        # Delete paper annotations
        result = await session.execute(
            text("DELETE FROM paper_annotations WHERE paper_id = ANY(:ids)"),
            {"ids": paper_ids},
        )
        print(f"  Deleted {result.rowcount} annotations")

        # Delete user favorites (if table exists)
        try:
            result = await session.execute(
                text("DELETE FROM user_favorites WHERE paper_id = ANY(:ids)"),
                {"ids": paper_ids},
            )
            print(f"  Deleted {result.rowcount} favorites")
        except Exception:
            # Table might not exist, continue
            pass

        # Delete papers
        result = await session.execute(
            text("DELETE FROM scientific_papers WHERE id = ANY(:ids)"),
            {"ids": paper_ids},
        )
        deleted_count = result.rowcount

        await session.commit()
        print(f"✅ Deleted {deleted_count} papers from database")

    except Exception as e:
        await session.rollback()
        print(f"❌ Error deleting papers: {e}")
        import traceback

        traceback.print_exc()
        raise


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Export and delete papers with missing PDF files"
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Only export to CSV, don't delete",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("missing_papers_export.csv"),
        help="Output CSV file path (default: missing_papers_export.csv)",
    )
    args = parser.parse_args()

    # Create output directory if needed
    args.output.parent.mkdir(parents=True, exist_ok=True)

    file_storage = FileStorageService()
    engine = create_async_engine(config.DATABASE_URL)

    try:
        async with get_async_session_context() as session:
            # Find missing files
            print("🔍 Finding papers with missing PDF files...")
            missing = await find_missing_files(session, file_storage)
            print(f"📊 Found {len(missing)} papers with missing files")

            if len(missing) == 0:
                print("✅ No papers with missing files found")
                return

            # Export to CSV
            await export_to_csv(missing, args.output)

            # Delete if not export-only
            if not args.export_only:
                print()
                print(f"⚠️  About to delete {len(missing)} papers from the database")
                print(f"   CSV backup saved to: {args.output}")
                print()
                response = input("Continue with deletion? (yes/no): ").strip().lower()
                if response == "yes":
                    await delete_papers(session, missing)
                else:
                    print("❌ Deletion cancelled")
            else:
                print(f"\n✅ Export complete. Papers saved to: {args.output}")
                print("   Run without --export-only to delete them from the database")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
