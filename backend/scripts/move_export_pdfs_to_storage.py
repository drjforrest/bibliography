#!/usr/bin/env python3
"""
Move PDFs from export folder to proper storage location.

This script:
1. Finds papers with missing PDF files
2. Looks for PDFs in the export folder by DEVONthink UUID
3. Copies them to proper storage using FileStorageService
4. Updates database file_path if needed

Usage:
    python backend/scripts/move_export_pdfs_to_storage.py [--dry-run]
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

# Load .env before importing config
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Set dummy CLERK vars to avoid config errors
if not os.getenv("CLERK_ISSUER"):
    os.environ["CLERK_ISSUER"] = "https://dummy.clerk.accounts.dev"
if not os.getenv("CLERK_JWKS_URL"):
    os.environ["CLERK_JWKS_URL"] = "https://dummy.clerk.accounts.dev/.well-known/jwks.json"

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.db import ScientificPaper, get_async_session_context
from app.services.file_storage import FileStorageService


async def find_missing_files(session: AsyncSession, file_storage: FileStorageService):
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


async def find_pdf_in_export_folder(dt_uuid: str, export_dir: Path) -> Optional[Path]:
    """Find PDF file in export folder by DEVONthink UUID."""
    # Try with .pdf extension
    pdf_path = export_dir / f"{dt_uuid}.pdf"
    if pdf_path.exists():
        return pdf_path
    
    # Try without extension
    pdf_path = export_dir / dt_uuid
    if pdf_path.exists() and pdf_path.is_file():
        return pdf_path
    
    return None


async def move_pdfs_to_storage(dry_run: bool = False):
    """Move missing PDFs from export folder to storage."""
    from app.config import config
    
    export_dir = Path.home() / "PDFs/Evidence_Library_Sync"
    if not export_dir.exists():
        print(f"❌ Export folder not found: {export_dir}")
        return
    
    file_storage = FileStorageService()
    engine = create_async_engine(config.DATABASE_URL)
    
    try:
        async with get_async_session_context() as session:
            missing = await find_missing_files(session, file_storage)
            print(f"📊 Found {len(missing)} papers with missing files")
            
            moved = 0
            not_found = 0
            errors = 0
            
            for paper in missing:
                if not paper.dt_source_uuid:
                    continue
                
                # Find PDF in export folder
                pdf_path = await find_pdf_in_export_folder(paper.dt_source_uuid, export_dir)
                
                if not pdf_path:
                    not_found += 1
                    if not_found <= 5:  # Show first 5
                        print(f"⚠️  PDF not found in export folder: {paper.dt_source_uuid} (Paper {paper.id})")
                    continue
                
                if dry_run:
                    print(f"🔍 Would move: {pdf_path.name} → storage (Paper {paper.id})")
                    moved += 1
                    continue
                
                try:
                    # Store PDF using FileStorageService (creates proper YYYY/MM/{uuid}.pdf structure)
                    new_relative_path, file_uuid = file_storage.store_pdf(str(pdf_path))
                    
                    # Update database
                    paper.file_path = new_relative_path
                    await session.commit()
                    
                    moved += 1
                    if moved % 10 == 0:
                        print(f"✓ Moved {moved} files...")
                
                except Exception as e:
                    errors += 1
                    print(f"❌ Error moving {pdf_path.name}: {e}")
            
            print(f"\n{'=' * 70}")
            print(f"Summary:")
            print(f"  Moved: {moved}")
            print(f"  Not found in export folder: {not_found}")
            print(f"  Errors: {errors}")
            print(f"{'=' * 70}")
    
    finally:
        await engine.dispose()


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Move PDFs from export folder to storage")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    
    await move_pdfs_to_storage(dry_run=args.dry_run)


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

