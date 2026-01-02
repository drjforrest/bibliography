#!/usr/bin/env python3
"""
List papers that were uploaded by users but not synced to DEVONthink yet.
These papers have dt_source_uuid = NULL and can be exported back to DEVONthink.

Usage:
    python scripts/list_papers_for_devonthink_export.py
    python scripts/list_papers_for_devonthink_export.py --user-id YOUR_USER_ID
    python scripts/list_papers_for_devonthink_export.py --export-csv output.csv
"""

import asyncio
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db import ScientificPaper, Document, User, SearchSpace
from app.config import config


async def get_papers_for_export(
    session: AsyncSession, user_id: str = None, limit: int = None
) -> List[Dict]:
    """
    Get papers that need to be synced to DEVONthink.
    These are papers without dt_source_uuid (uploaded by users, not from DEVONthink).
    """
    stmt = (
        select(
            ScientificPaper.id,
            ScientificPaper.title,
            ScientificPaper.authors,
            ScientificPaper.doi,
            ScientificPaper.publication_year,
            ScientificPaper.file_path,
            ScientificPaper.created_at,
            Document.search_space_id,
            SearchSpace.name.label("search_space_name"),
        )
        .join(ScientificPaper.document)
        .join(Document.search_space)
        .where(ScientificPaper.dt_source_uuid.is_(None))  # Not from DEVONthink
    )

    if user_id:
        stmt = stmt.where(SearchSpace.user_id == user_id)

    stmt = stmt.order_by(ScientificPaper.created_at.desc())

    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    rows = result.all()

    papers = []
    for row in rows:
        papers.append(
            {
                "id": row.id,
                "title": row.title or "Untitled",
                "authors": ", ".join(row.authors) if row.authors else "Unknown",
                "doi": row.doi or "",
                "year": row.publication_year or "",
                "file_path": row.file_path,
                "created_at": row.created_at.isoformat() if row.created_at else "",
                "search_space": row.search_space_name or f"ID: {row.search_space_id}",
            }
        )

    return papers


async def export_to_csv(papers: List[Dict], output_path: str):
    """Export papers list to CSV file for easy review"""
    if not papers:
        print("No papers to export")
        return

    fieldnames = [
        "id",
        "title",
        "authors",
        "doi",
        "year",
        "created_at",
        "search_space",
        "file_path",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for paper in papers:
            writer.writerow(paper)

    print(f"✓ Exported {len(papers)} papers to {output_path}")


async def main():
    parser = argparse.ArgumentParser(
        description="List papers that need to be synced to DEVONthink"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="Filter by user ID (UUID)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of results",
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        help="Export results to CSV file",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        help="Override DATABASE_URL from config",
    )

    args = parser.parse_args()

    # Get database URL
    db_url = args.database_url or config.DATABASE_URL
    if not db_url:
        print("ERROR: DATABASE_URL not set. Set it as environment variable or use --database-url")
        sys.exit(1)

    # Create database connection
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get user info if filtering
        if args.user_id:
            user_result = await session.execute(
                select(User).where(User.id == args.user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                print(f"ERROR: User {args.user_id} not found")
                sys.exit(1)
            print(f"User: {user.email} ({user.id})")
            print()

        # Get papers
        papers = await get_papers_for_export(session, args.user_id, args.limit)

        if not papers:
            print("✓ No papers found that need to be synced to DEVONthink")
            print("  (All papers already have dt_source_uuid set)")
            return

        print(f"Found {len(papers)} paper(s) that need to be synced to DEVONthink:\n")

        # Display results
        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper['title']}")
            if paper["authors"]:
                print(f"   Authors: {paper['authors']}")
            if paper["doi"]:
                print(f"   DOI: {paper['doi']}")
            if paper["year"]:
                print(f"   Year: {paper['year']}")
            print(f"   Created: {paper['created_at']}")
            print(f"   Search Space: {paper['search_space']}")
            print(f"   File: {paper['file_path']}")
            print()

        # Export to CSV if requested
        if args.export_csv:
            await export_to_csv(papers, args.export_csv)

        # Summary
        print("=" * 60)
        print(f"Total: {len(papers)} paper(s) ready for DEVONthink export")
        print()
        print("Next steps:")
        print("1. Review the papers above")
        print("2. Export PDFs and metadata to DEVONthink")
        print("3. After importing to DEVONthink, update dt_source_uuid in the database")
        print()
        print("To export to CSV:")
        print(f"  python {sys.argv[0]} --export-csv papers_to_sync.csv")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

