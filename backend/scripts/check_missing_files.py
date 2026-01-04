#!/usr/bin/env python3
"""Check for papers with missing PDF files."""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

if not os.getenv("CLERK_ISSUER"):
    os.environ["CLERK_ISSUER"] = "https://dummy.clerk.accounts.dev"
if not os.getenv("CLERK_JWKS_URL"):
    os.environ["CLERK_JWKS_URL"] = "https://dummy.clerk.accounts.dev/.well-known/jwks.json"

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import config
from app.services.file_storage import FileStorageService


async def main():
    engine = create_async_engine(config.DATABASE_URL)
    file_storage = FileStorageService()
    
    async with engine.begin() as conn:
        # Get all papers with file_paths
        result = await conn.execute(text("""
            SELECT id, file_path, dt_source_uuid, title 
            FROM scientific_papers 
            WHERE file_path IS NOT NULL
            ORDER BY id
        """))
        papers = result.fetchall()
        
        missing = []
        devonthink_import = []
        found = []
        
        for paper in papers:
            paper_id, file_path, dt_uuid, title = paper
            try:
                full_path = file_storage.get_full_path(file_path)
                if full_path.exists():
                    found.append(paper_id)
                else:
                    if file_path.startswith("devonthink_import/"):
                        devonthink_import.append((paper_id, file_path, dt_uuid, title))
                    else:
                        missing.append((paper_id, file_path, dt_uuid, title))
            except Exception as e:
                missing.append((paper_id, file_path, dt_uuid, title))
        
        print(f"{'=' * 70}")
        print(f"PDF File Status Report")
        print(f"{'=' * 70}")
        print(f"\nTotal papers with file_path: {len(papers)}")
        print(f"✅ Files found: {len(found)}")
        print(f"❌ Files missing: {len(missing)}")
        print(f"⚠️  devonthink_import/ paths: {len(devonthink_import)}")
        
        if devonthink_import:
            print(f"\n{'=' * 70}")
            print(f"Papers with devonthink_import/ paths (first 10):")
            print(f"{'=' * 70}")
            for paper_id, file_path, dt_uuid, title in devonthink_import[:10]:
                print(f"  Paper {paper_id}: {title[:60] if title else '(no title)'}")
                print(f"    Path: {file_path}")
                print(f"    UUID: {dt_uuid}")
        
        if missing and not all(m[1].startswith("devonthink_import/") for m in missing):
            print(f"\n{'=' * 70}")
            print(f"Papers with other missing paths (first 10):")
            print(f"{'=' * 70}")
            other_missing = [m for m in missing if not m[1].startswith("devonthink_import/")]
            for paper_id, file_path, dt_uuid, title in other_missing[:10]:
                print(f"  Paper {paper_id}: {title[:60] if title else '(no title)'}")
                print(f"    Path: {file_path}")
                print(f"    UUID: {dt_uuid}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

