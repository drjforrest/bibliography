#!/usr/bin/env python3
"""
Handle papers with missing PDF files.

This script provides multiple options:
1. Report missing PDFs (default)
2. Clear file_path references (keeps paper metadata)
3. Attempt to re-download PDFs from DOI (if available)
4. Export to CSV for manual review

Usage:
    # Report only (safe, no changes)
    python scripts/handle_missing_pdfs.py --report

    # Clear file_path references (keeps papers, removes broken links)
    python scripts/handle_missing_pdfs.py --clear-paths

    # Attempt to re-download from DOIs (experimental)
    python scripts/handle_missing_pdfs.py --recover

    # Export to CSV for manual review
    python scripts/handle_missing_pdfs.py --export missing_papers.csv

    # Combine: export, then clear paths
    python scripts/handle_missing_pdfs.py --export missing.csv --clear-paths
"""

import asyncio
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

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
from app.db import (
    ScientificPaper,
    DevonthinkSync,
    Document,
    Chunk,
    get_async_session_context,
)
from app.services.file_storage import FileStorageService
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from uuid import uuid4


async def find_missing_pdfs(
    session: AsyncSession, file_storage: FileStorageService
) -> List[Tuple[ScientificPaper, str]]:
    """
    Find papers with missing PDF files.
    
    Returns:
        List of (paper, reason) tuples
    """
    result = await session.execute(
        select(ScientificPaper).where(ScientificPaper.file_path.isnot(None))
    )
    papers = result.scalars().all()

    missing = []
    for paper in papers:
        try:
            full_path = file_storage.get_full_path(paper.file_path)
            if not full_path.exists():
                missing.append((paper, "file_not_found"))
        except Exception as e:
            missing.append((paper, f"path_error: {str(e)}"))

    return missing


async def report_missing_pdfs(missing: List[Tuple[ScientificPaper, str]]):
    """Print a report of missing PDFs."""
    print(f"{'=' * 80}")
    print(f"Missing PDF Report")
    print(f"{'=' * 80}")
    print(f"\nTotal papers with missing PDFs: {len(missing)}")
    
    if not missing:
        print("✅ No missing PDFs found!")
        return

    # Group by reason
    by_reason = {}
    has_doi = 0
    no_doi = 0

    for paper, reason in missing:
        if reason not in by_reason:
            by_reason[reason] = []
        by_reason[reason].append(paper)
        
        if paper.doi:
            has_doi += 1
        else:
            no_doi += 1

    print(f"\nBreakdown:")
    print(f"  📄 Papers with DOI (potentially recoverable): {has_doi}")
    print(f"  📄 Papers without DOI: {no_doi}")

    print(f"\nReasons:")
    for reason, papers_list in by_reason.items():
        print(f"  • {reason}: {len(papers_list)} papers")

    # Show sample papers
    print(f"\n{'=' * 80}")
    print(f"Sample missing PDFs (first 10):")
    print(f"{'=' * 80}")
    for paper, reason in missing[:10]:
        print(f"\n  Paper ID: {paper.id}")
        print(f"  Title: {paper.title[:70] if paper.title else '(no title)'}")
        print(f"  File Path: {paper.file_path}")
        print(f"  DOI: {paper.doi or '(no DOI)'}")
        print(f"  Reason: {reason}")


async def clear_file_paths(
    session: AsyncSession, missing: List[Tuple[ScientificPaper, str]]
):
    """Clear file_path references for missing PDFs (keeps paper metadata)."""
    print(f"\n🧹 Marking file_path as missing for {len(missing)} papers...")
    print(f"   ⚠️  Note: file_path is currently NOT NULL in schema")
    print(f"   Prefixing with 'MISSING:' to preserve original path for recovery")
    print(f"   Consider making file_path nullable in a migration: ALTER TABLE scientific_papers ALTER COLUMN file_path DROP NOT NULL;")
    
    cleared = 0
    for paper, _ in missing:
        old_path = paper.file_path
        # Prefix with MISSING: to mark as missing but preserve original path
        # This allows recovery if PDF is found later
        if not old_path.startswith("MISSING:"):
            paper.file_path = f"MISSING:{old_path}"
        cleared += 1
    
    await session.commit()
    print(f"✅ Marked {cleared} papers as missing (file_path prefixed with 'MISSING:')")
    print(f"   Papers remain in database with their metadata")
    print(f"   Original paths preserved for potential recovery")


async def export_to_csv(
    missing: List[Tuple[ScientificPaper, str]], output_path: Path
):
    """Export missing PDF information to CSV."""
    print(f"\n📝 Exporting {len(missing)} papers to {output_path}...")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "paper_id",
                "title",
                "file_path",
                "doi",
                "dt_source_uuid",
                "reason",
                "has_doi",
                "created_at",
            ]
        )

        for paper, reason in missing:
            writer.writerow(
                [
                    paper.id,
                    paper.title or "",
                    paper.file_path or "",
                    paper.doi or "",
                    paper.dt_source_uuid or "",
                    reason,
                    "yes" if paper.doi else "no",
                    paper.created_at.isoformat() if paper.created_at else "",
                ]
            )

    print(f"✅ Exported {len(missing)} papers to {output_path}")


async def attempt_recovery(
    session: AsyncSession, missing: List[Tuple[ScientificPaper, str]]
):
    """
    Attempt to recover PDFs by downloading from DOI.
    
    Note: This is experimental and may not work for all DOIs.
    """
    print(f"\n🔄 Attempting to recover PDFs from DOIs...")
    
    recoverable = [(p, r) for p, r in missing if p.doi]
    
    if not recoverable:
        print("⚠️  No papers with DOIs to recover")
        return
    
    print(f"   Found {len(recoverable)} papers with DOIs")
    print(f"   ⚠️  PDF recovery from DOI is not yet implemented")
    print(f"   This feature would require:")
    print(f"     - Integration with Unpaywall, Sci-Hub, or similar services")
    print(f"     - Or manual download and re-upload workflow")
    
    # TODO: Implement DOI-based PDF recovery
    # This could integrate with:
    # - Unpaywall API for open access PDFs
    # - DOI resolver services
    # - Manual download script


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Handle papers with missing PDF files"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show report of missing PDFs (default action if no other specified)",
    )
    parser.add_argument(
        "--clear-paths",
        action="store_true",
        help="Clear file_path references for missing PDFs (keeps papers)",
    )
    parser.add_argument(
        "--recover",
        action="store_true",
        help="Attempt to recover PDFs from DOIs (experimental)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete papers and mark DEVONthink UUIDs as excluded (prevents re-sync)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (use with --delete or --clear-paths)",
    )
    parser.add_argument(
        "--export",
        type=Path,
        help="Export missing PDF info to CSV file",
    )
    
    args = parser.parse_args()

    # Default to report if nothing specified
    if not any([args.report, args.clear_paths, args.recover, args.export, args.delete]):
        args.report = True

    file_storage = FileStorageService()

    async with get_async_session_context() as session:
        # Find missing files
        print("🔍 Finding papers with missing PDF files...")
        missing = await find_missing_pdfs(session, file_storage)
        print(f"📊 Found {len(missing)} papers with missing files\n")

        if len(missing) == 0:
            print("✅ No papers with missing files found")
            return

        # Export if requested
        if args.export:
            await export_to_csv(missing, args.export)

        # Report if requested
        if args.report:
            await report_missing_pdfs(missing)

        # Clear paths if requested
        if args.clear_paths:
            print("\n" + "=" * 80)
            print("⚠️  WARNING: This will clear file_path references for missing PDFs")
            print(f"   {len(missing)} papers will be affected")
            if args.export:
                print(f"   Backup saved to: {args.export}")
            if args.yes:
                await clear_file_paths(session, missing)
            else:
                response = input("\nContinue? (yes/no): ").strip().lower()
                if response == "yes":
                    await clear_file_paths(session, missing)
                else:
                    print("❌ Operation cancelled")

        # Attempt recovery if requested
        if args.recover:
            await attempt_recovery(session, missing)
        
        # Delete and exclude if requested
        if args.delete:
            print("\n" + "=" * 80)
            print("⚠️  WARNING: This will DELETE papers and exclude them from DEVONthink sync")
            print(f"   {len(missing)} papers will be permanently deleted")
            print(f"   Their DEVONthink UUIDs will be marked as excluded (user_deleted=True)")
            print(f"   This prevents them from being re-synced from DEVONthink")
            if args.export:
                print(f"   Backup saved to: {args.export}")
            if args.yes:
                await delete_papers_and_mark_excluded(session, missing)
            else:
                response = input("\nContinue with deletion? (yes/no): ").strip().lower()
                if response == "yes":
                    await delete_papers_and_mark_excluded(session, missing)
                else:
                    print("❌ Deletion cancelled")

        print("\n✅ Done!")


async def delete_papers_and_mark_excluded(
    session: AsyncSession, missing: List[Tuple[ScientificPaper, str]]
):
    """
    Delete papers with missing PDFs and mark their DEVONthink sync records as excluded.
    
    This prevents them from being re-synced from DEVONthink.
    """
    print(f"\n🗑️  Deleting {len(missing)} papers and marking as excluded from sync...")
    
    papers_to_delete = [paper for paper, _ in missing]
    paper_ids = [paper.id for paper in papers_to_delete]
    document_ids = [paper.document_id for paper in papers_to_delete if paper.document_id]
    
    # Get DEVONthink UUIDs before deletion
    dt_uuids = [paper.dt_source_uuid for paper in papers_to_delete if paper.dt_source_uuid]
    
    print(f"   Papers to delete: {len(paper_ids)}")
    print(f"   DEVONthink UUIDs to exclude: {len(dt_uuids)}")
    
    deleted_count = 0
    excluded_count = 0
    
    try:
        # 1. Mark DEVONthink sync records as user_deleted (prevents re-sync)
        if dt_uuids:
            print(f"\n   Attempting to mark {len(dt_uuids)} sync records as excluded...")
            
            # Check if user_deleted column exists using raw SQL
            try:
                check_column_stmt = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'devonthink_sync' AND column_name = 'user_deleted'
                """)
                result = await session.execute(check_column_stmt)
                column_exists = result.scalar_one_or_none() is not None
                
                if column_exists:
                    # Column exists, mark records as deleted using raw SQL
                    update_stmt = text("""
                        UPDATE devonthink_sync 
                        SET user_deleted = TRUE, user_deleted_at = :deleted_at
                        WHERE dt_uuid = ANY(:uuids)
                    """)
                    result = await session.execute(
                        update_stmt,
                        {"deleted_at": datetime.now(timezone.utc), "uuids": dt_uuids}
                    )
                    excluded_count = result.rowcount
                    await session.flush()
                    print(f"   ✅ Marked {excluded_count} sync records as excluded")
                else:
                    print(f"   ⚠️  user_deleted column not found in devonthink_sync table")
                    print(f"   ⚠️  Skipping exclusion marking (papers will still be deleted)")
                    print(f"   ⚠️  To enable exclusion, run migration:")
                    print(f"       ALTER TABLE devonthink_sync ADD COLUMN user_deleted BOOLEAN DEFAULT FALSE;")
                    print(f"       ALTER TABLE devonthink_sync ADD COLUMN user_deleted_at TIMESTAMP WITH TIME ZONE;")
            except Exception as e:
                # Error checking column
                print(f"   ⚠️  Cannot mark sync records as excluded: {e}")
                print(f"   ⚠️  Papers will be deleted, but may be re-synced from DEVONthink")
                print(f"   ⚠️  Consider running migration to add user_deleted column")
        
        # 2. Delete chunks first (they reference documents)
        if document_ids:
            result = await session.execute(
                text("DELETE FROM chunks WHERE document_id = ANY(:ids)"),
                {"ids": document_ids},
            )
            print(f"   Deleted {result.rowcount} chunks")
        
        # 3. Delete documents
        if document_ids:
            result = await session.execute(
                text("DELETE FROM documents WHERE id = ANY(:ids)"),
                {"ids": document_ids},
            )
            print(f"   Deleted {result.rowcount} documents")
        
        # 4. Delete paper annotations
        result = await session.execute(
            text("DELETE FROM paper_annotations WHERE paper_id = ANY(:ids)"),
            {"ids": paper_ids},
        )
        print(f"   Deleted {result.rowcount} annotations")
        
        # 5. Delete user favorites
        try:
            result = await session.execute(
                text("DELETE FROM user_favorites WHERE paper_id = ANY(:ids)"),
                {"ids": paper_ids},
            )
            print(f"   Deleted {result.rowcount} favorites")
        except Exception:
            # Table might not exist, continue
            pass
        
        # 6. Delete paper_tags relationships
        try:
            result = await session.execute(
                text("DELETE FROM paper_tags WHERE paper_id = ANY(:ids)"),
                {"ids": paper_ids},
            )
            print(f"   Deleted {result.rowcount} tag relationships")
        except Exception:
            pass
        
        # 7. Delete papers (sync records remain with user_deleted=True)
        result = await session.execute(
            text("DELETE FROM scientific_papers WHERE id = ANY(:ids)"),
            {"ids": paper_ids},
        )
        deleted_count = result.rowcount
        
        await session.commit()
        print(f"\n✅ Successfully deleted {deleted_count} papers")
        print(f"✅ Excluded {excluded_count} DEVONthink UUIDs from future syncs")
        
    except Exception as e:
        await session.rollback()
        print(f"❌ Error deleting papers: {e}")
        import traceback
        traceback.print_exc()
        raise


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
