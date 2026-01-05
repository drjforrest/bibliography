#!/usr/bin/env python3
"""
Backfill devonthink_sync records and vectorize papers that haven't been processed.

This script:
1. Creates devonthink_sync records for existing papers that don't have them
2. Vectorizes papers that don't have chunks/embeddings

Usage:
    python backend/scripts/backfill_sync_and_vectorize.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os

from dotenv import load_dotenv

load_dotenv(".env")
if not os.getenv("CLERK_ISSUER"):
    os.environ["CLERK_ISSUER"] = "https://dummy.clerk.accounts.dev"
if not os.getenv("CLERK_JWKS_URL"):
    os.environ["CLERK_JWKS_URL"] = (
        "https://dummy.clerk.accounts.dev/.well-known/jwks.json"
    )

from uuid import uuid4

from app.config import config
from app.db import (
    DevonthinkSync,
    DevonthinkSyncStatus,
    Document,
    ScientificPaper,
    get_async_session_context,
)
from app.services.embedding_service import EmbeddingService
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine


async def backfill_sync_records(session):
    """Create devonthink_sync records for existing papers."""
    print("\n📋 Step 1: Backfilling devonthink_sync records...")

    # Find papers with dt_source_uuid but no sync record
    result = await session.execute(
        text(
            """
            SELECT sp.id, sp.dt_source_uuid, sp.dt_source_path, sp.created_at
            FROM scientific_papers sp
            WHERE sp.dt_source_uuid IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM devonthink_sync ds
                WHERE ds.dt_uuid = sp.dt_source_uuid
            )
            ORDER BY sp.id
        """
        )
    )
    papers = result.fetchall()

    if len(papers) == 0:
        print("  ✅ All papers already have sync records")
        return 0

    print(f"  Found {len(papers)} papers without sync records")

    # Get a user_id
    user_result = await session.execute(text('SELECT id FROM "user" LIMIT 1'))
    user_row = user_result.fetchone()

    if not user_row:
        print("  ❌ No users found in database. Cannot create sync records.")
        return 0

    user_id = user_row[0]
    print(f"  Using user_id: {user_id}")

    # Create sync records
    created = 0
    for paper_id, dt_uuid, dt_path, created_at in papers:
        try:
            sync_record = DevonthinkSync(
                dt_uuid=dt_uuid,
                dt_path=dt_path or "",
                local_uuid=uuid4(),
                scientific_paper_id=paper_id,
                user_id=user_id,
                sync_status=DevonthinkSyncStatus.SYNCED,  # Use SYNCED, not COMPLETED
                last_sync_date=created_at,
            )
            session.add(sync_record)
            created += 1
        except Exception as e:
            print(f"  ⚠️  Error creating sync record for paper {paper_id}: {e}")

    await session.commit()
    print(f"  ✅ Created {created} sync records")
    return created


async def vectorize_papers(session):
    """Vectorize papers that don't have chunks."""
    print("\n🔍 Step 2: Vectorizing papers...")

    # Find papers without chunks
    result = await session.execute(
        text(
            """
            SELECT DISTINCT sp.id, sp.document_id
            FROM scientific_papers sp
            JOIN documents d ON sp.document_id = d.id
            WHERE NOT EXISTS (
                SELECT 1 FROM chunks c
                WHERE c.document_id = d.id
            )
            ORDER BY sp.id
        """
        )
    )
    papers = result.fetchall()

    if len(papers) == 0:
        print("  ✅ All papers already have chunks")
        return 0

    print(f"  Found {len(papers)} papers without chunks")

    embedding_service = EmbeddingService(session)
    vectorized = 0
    errors = 0

    for paper_id, document_id in papers:
        try:
            # Get the document
            stmt = select(Document).where(Document.id == document_id)
            result = await session.execute(stmt)
            document = result.scalar_one_or_none()

            if not document or not document.content:
                print(f"  ⚠️  Paper {paper_id}: Document has no content, skipping")
                continue

            # Embed the document
            print(f"  Processing paper {paper_id} (document {document_id})...")
            doc_embedded = await embedding_service.embed_document(document_id)

            if doc_embedded:
                # Create and embed chunks
                chunks_created = await embedding_service.create_and_embed_chunks(
                    document
                )
                if chunks_created:
                    vectorized += 1
                    if vectorized % 10 == 0:
                        print(
                            f"    Progress: {vectorized}/{len(papers)} papers vectorized"
                        )
                else:
                    print(f"    ⚠️  Paper {paper_id}: Failed to create chunks")
                    errors += 1
            else:
                print(f"    ⚠️  Paper {paper_id}: Failed to embed document")
                errors += 1

        except Exception as e:
            print(f"    ❌ Error vectorizing paper {paper_id}: {e}")
            errors += 1

    await session.commit()
    print(f"  ✅ Vectorized {vectorized} papers")
    if errors > 0:
        print(f"  ⚠️  {errors} papers had errors")
    return vectorized


async def main():
    """Main function."""
    print("🚀 Starting backfill and vectorization process...")
    print("=" * 60)

    engine = create_async_engine(config.DATABASE_URL)

    try:
        async with get_async_session_context() as session:
            # Step 1: Backfill sync records
            sync_count = await backfill_sync_records(session)

            # Step 2: Vectorize papers
            vectorized_count = await vectorize_papers(session)

            print("\n" + "=" * 60)
            print("✅ Process complete!")
            print(f"  - Created {sync_count} sync records")
            print(f"  - Vectorized {vectorized_count} papers")

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
