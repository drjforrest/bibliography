#!/usr/bin/env python3
"""
Fix PDF file paths for papers imported with devonthink_import placeholder paths.

This script:
1. Finds all papers with devonthink_import/{uuid} file paths
2. Locates the actual PDF files
3. Either moves them to the fallback location OR re-stores them properly

Usage:
    # Quick fix: Move PDFs to fallback location
    python backend/scripts/fix_devonthink_import_paths.py --mode move

    # Better fix: Re-store PDFs in proper YYYY/MM/{uuid}.pdf format
    python backend/scripts/fix_devonthink_import_paths.py --mode restore

    # Dry run to see what would happen
    python backend/scripts/fix_devonthink_import_paths.py --mode move --dry-run
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Get config lazily to avoid loading rerankers/torch
import os

# Import only what we need - avoid importing config which loads heavy dependencies
from app.db import ScientificPaper, get_async_session_context
from app.services.file_storage import FileStorageService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def get_pdf_storage_root():
    """Get PDF_STORAGE_ROOT from environment or default."""
    return os.getenv("PDF_STORAGE_ROOT", "./data/pdfs")


async def find_papers_with_placeholder_paths(
    session: AsyncSession,
) -> List[ScientificPaper]:
    """Find all papers with devonthink_import placeholder paths."""
    stmt = select(ScientificPaper).where(
        ScientificPaper.file_path.like("devonthink_import/%")
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def find_pdf_file(uuid: str, search_paths: List[Path]) -> Optional[Path]:
    """Try to find a PDF file by UUID in various locations."""
    potential_names = [
        f"{uuid}.pdf",
        f"{uuid}",
        f"{uuid}.PDF",
    ]

    for search_path in search_paths:
        # Check if path exists and is accessible (handle mount errors)
        try:
            if not search_path.exists():
                continue
        except (OSError, PermissionError) as e:
            # Mount might be broken or inaccessible
            print(f"  ⚠️  Cannot access {search_path}: {e}")
            continue

        # Check directly in search_path
        for name in potential_names:
            try:
                potential_file = search_path / name
                if potential_file.exists() and potential_file.is_file():
                    return potential_file
            except (OSError, PermissionError):
                continue

        # Check in devonthink_import subdirectory
        try:
            devonthink_dir = search_path / "devonthink_import"
            if devonthink_dir.exists():
                for name in potential_names:
                    try:
                        potential_file = devonthink_dir / name
                        if potential_file.exists() and potential_file.is_file():
                            return potential_file
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            continue

        # Recursively search (limit depth to avoid too much scanning)
        try:
            for root, dirs, files in os.walk(search_path, followlinks=True):
                # Limit depth to 3 levels
                depth = root[len(str(search_path)) :].count(os.sep)
                if depth > 3:
                    dirs[:] = []  # Don't recurse deeper
                    continue

                for name in potential_names:
                    if name in files:
                        try:
                            file_path = Path(root) / name
                            if file_path.exists() and file_path.is_file():
                                return file_path
                        except (OSError, PermissionError):
                            continue
        except (OSError, PermissionError) as e:
            # Mount might be broken, skip this path
            print(f"  ⚠️  Cannot walk {search_path}: {e}")
            continue

    return None


async def move_to_fallback_location(
    session: AsyncSession,
    paper: ScientificPaper,
    pdf_file: Path,
    storage_root: Path,
    dry_run: bool = False,
) -> bool:
    """Move PDF to fallback devonthink_import location."""
    uuid = paper.file_path.replace("devonthink_import/", "")
    target_dir = storage_root / "devonthink_import"
    target_file = target_dir / f"{uuid}.pdf"

    if target_file.exists():
        print(f"  ⚠️  Target already exists: {target_file}")
        return False

    if dry_run:
        print(f"  [DRY RUN] Would move: {pdf_file} -> {target_file}")
        return True

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_file, target_file)
        print(f"  ✓ Moved: {target_file}")
        return True
    except Exception as e:
        print(f"  ❌ Error moving file: {e}")
        return False


async def restore_to_proper_location(
    session: AsyncSession,
    paper: ScientificPaper,
    pdf_file: Path,
    file_storage: FileStorageService,
    dry_run: bool = False,
) -> bool:
    """Re-store PDF in proper YYYY/MM/{uuid}.pdf format and update database."""
    if dry_run:
        print(f"  [DRY RUN] Would re-store: {pdf_file} -> proper storage location")
        return True

    try:
        # Store using proper storage service
        relative_path, file_uuid = file_storage.store_pdf(str(pdf_file))

        # Update database
        paper.file_path = relative_path
        await session.commit()

        print(f"  ✓ Re-stored: {relative_path} (updated database)")
        return True
    except Exception as e:
        print(f"  ❌ Error re-storing file: {e}")
        await session.rollback()
        return False


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix devonthink_import placeholder paths"
    )
    parser.add_argument(
        "--mode",
        choices=["move", "restore"],
        default="move",
        help="Mode: 'move' to fallback location, 'restore' to proper storage",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--search-paths",
        nargs="+",
        help="Additional paths to search for PDFs (default: PDF_STORAGE_ROOT and common locations)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("🔧 Fix DEVONthink Import PDF Paths")
    print("=" * 70)
    print(f"Mode: {args.mode}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Get storage root (avoid importing config which loads heavy dependencies)
    storage_root = Path(get_pdf_storage_root())
    print(f"📁 Storage root: {storage_root}")

    # Build search paths
    search_paths = [storage_root]
    if args.search_paths:
        search_paths.extend([Path(p) for p in args.search_paths])

    # Add common locations (check accessibility, not just existence)
    common_paths = [
        Path.home() / "PDFs" / "Evidence_Library_Sync",
        Path("/tmp/dev-pdfs"),
        Path("/Users/jforrest/production/hero-evidence-library/data/pdfs"),
    ]
    accessible_paths = []
    for p in common_paths:
        try:
            if p.exists():
                accessible_paths.append(p)
        except (OSError, PermissionError):
            # Mount might be broken, skip silently
            pass
    search_paths.extend(accessible_paths)

    print(f"🔍 Searching in: {[str(p) for p in search_paths]}")
    if len(search_paths) == 0:
        print("⚠️  WARNING: No accessible search paths found!")
        print("   Make sure PDF_STORAGE_ROOT is set or provide --search-paths")
    print()

    async with get_async_session_context() as session:
        # Find papers with placeholder paths
        papers = await find_papers_with_placeholder_paths(session)
        print(f"Found {len(papers)} papers with devonthink_import paths")
        print()

        if not papers:
            print("✅ No papers need fixing!")
            return

        file_storage = FileStorageService()
        fixed_count = 0
        not_found_count = 0
        error_count = 0

        for i, paper in enumerate(papers, 1):
            uuid = paper.file_path.replace("devonthink_import/", "")
            print(f"[{i}/{len(papers)}] Paper {paper.id}: {paper.title[:50]}")
            print(f"  UUID: {uuid}")

            # Find the PDF file
            pdf_file = await find_pdf_file(uuid, search_paths)

            if not pdf_file:
                print(f"  ❌ PDF not found for UUID: {uuid}")
                not_found_count += 1
                print()
                continue

            print(f"  📄 Found PDF: {pdf_file}")

            # Fix based on mode
            if args.mode == "move":
                success = await move_to_fallback_location(
                    session, paper, pdf_file, storage_root, args.dry_run
                )
            else:  # restore
                success = await restore_to_proper_location(
                    session, paper, pdf_file, file_storage, args.dry_run
                )

            if success:
                fixed_count += 1
            else:
                error_count += 1

            print()

        print("=" * 70)
        print("📊 Summary")
        print("=" * 70)
        print(f"Total papers: {len(papers)}")
        print(f"Fixed: {fixed_count}")
        print(f"Not found: {not_found_count}")
        print(f"Errors: {error_count}")

        if args.dry_run:
            print()
            print("💡 This was a dry run. Run without --dry-run to apply changes.")


if __name__ == "__main__":
    asyncio.run(main())
