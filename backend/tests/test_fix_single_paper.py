#!/usr/bin/env python3
"""Test script to fix a single paper by ID."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent / ".env")
if not os.getenv("CLERK_ISSUER"):
    os.environ["CLERK_ISSUER"] = "https://dummy.clerk.accounts.dev"
if not os.getenv("CLERK_JWKS_URL"):
    os.environ["CLERK_JWKS_URL"] = "https://dummy.clerk.accounts.dev/.well-known/jwks.json"

from app.db import ScientificPaper, get_async_session_context
from app.services.file_storage import FileStorageService
from sqlalchemy import select


async def test_fix_paper(paper_id: int):
    """Test finding and fixing a single paper."""
    from backend.scripts.fix_devonthink_import_paths import find_pdf_file, restore_to_proper_location
    
    file_storage = FileStorageService()
    
    async with get_async_session_context() as session:
        stmt = select(ScientificPaper).where(ScientificPaper.id == paper_id)
        result = await session.execute(stmt)
        paper = result.scalar_one_or_none()
        
        if not paper:
            print(f"Paper {paper_id} not found")
            return
        
        print(f"Paper {paper_id}: {paper.title[:50] if paper.title else '(no title)'}")
        print(f"  Current file_path: {paper.file_path}")
        print(f"  dt_source_uuid: {paper.dt_source_uuid}")
        
        if not paper.file_path or not paper.file_path.startswith("devonthink_import/"):
            print("  ❌ Paper doesn't have devonthink_import/ path")
            return
        
        uuid = paper.file_path.replace("devonthink_import/", "")
        print(f"  UUID: {uuid}")
        
        # Search paths
        search_paths = [
            Path.home() / "PDFs" / "Evidence_Library_Sync",
            Path("/Users/drjforrest/PDFs/Evidence_Library_Sync"),
            file_storage.storage_root,
        ]
        
        print(f"\n  Searching in: {[str(p) for p in search_paths]}")
        
        pdf_file = await find_pdf_file(uuid, search_paths)
        
        if pdf_file:
            print(f"  ✅ Found PDF: {pdf_file}")
            print(f"  Would re-store to: {file_storage.storage_root}/YYYY/MM/{uuid}.pdf")
            return True
        else:
            print(f"  ❌ PDF not found")
            return False


if __name__ == "__main__":
    import sys
    paper_id = int(sys.argv[1]) if len(sys.argv) > 1 else 248
    asyncio.run(test_fix_paper(paper_id))

