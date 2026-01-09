#!/usr/bin/env python3
"""
Unified enrichment pipeline for scientific papers.

This script coordinates ALL enrichment steps:
1. DOI metadata enrichment (Crossref/Semantic Scholar)
2. PDF processing (text extraction, metadata from PDF)
3. Vectorization (embeddings and chunks)
4. LLM enrichment (lay summaries, insights, citations)

Usage:
    python scripts/enrich_papers_unified.py [--limit N] [--skip-existing] [--batch-size N]
    python scripts/enrich_papers_unified.py --skip-doi --skip-pdf  # Only LLM + vectorization
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db import ScientificPaper
from app.services.unified_enrichment_service import UnifiedEnrichmentService
from app.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UnifiedEnrichmentPipeline:
    """Unified enrichment pipeline that coordinates all enrichment steps."""

    def __init__(self, session_maker, batch_size: int = 5):
        self.session_maker = session_maker
        self.batch_size = batch_size

        # Stats
        self.processed_count = 0
        self.enriched_count = 0
        self.error_count = 0
        self.skipped_count = 0
        self.errors = []

    async def enrich_paper_by_id(
        self,
        paper_id: int,
        skip_doi: bool = False,
        skip_pdf: bool = False,
        skip_vectorization: bool = False,
        skip_llm: bool = False,
    ) -> bool:
        """
        Enrich a specific paper by ID.

        Args:
            paper_id: ID of paper to enrich
            skip_doi: Skip DOI metadata enrichment
            skip_pdf: Skip PDF processing
            skip_vectorization: Skip vectorization
            skip_llm: Skip LLM enrichment

        Returns:
            True if enrichment succeeded, False otherwise
        """
        async with self.session_maker() as session:
            try:
                enrichment_service = UnifiedEnrichmentService(session)
                success = await enrichment_service.enrich_paper_complete(
                    paper_id,
                    skip_doi_enrichment=skip_doi,
                    skip_pdf_processing=skip_pdf,
                    skip_vectorization=skip_vectorization,
                    skip_llm_enrichment=skip_llm,
                )
                await enrichment_service.close()
                return success
            except Exception as e:
                logger.error(f"Error enriching paper {paper_id}: {str(e)}")
                return False

    async def enrich_all_papers(
        self,
        limit: int = None,
        skip_existing: bool = False,
        skip_doi: bool = False,
        skip_pdf: bool = False,
        skip_vectorization: bool = False,
        skip_llm: bool = False,
    ):
        """
        Enrich all papers with complete pipeline.

        Args:
            limit: Maximum number of papers to process
            skip_existing: Skip papers that already have lay_summary
            skip_doi: Skip DOI metadata enrichment
            skip_pdf: Skip PDF processing
            skip_vectorization: Skip vectorization
            skip_llm: Skip LLM enrichment
        """
        logger.info("Starting unified enrichment pipeline...")
        logger.info(f"  Skip DOI: {skip_doi}, Skip PDF: {skip_pdf}, Skip Vectorization: {skip_vectorization}, Skip LLM: {skip_llm}")

        async with self.session_maker() as session:
            # Get papers that need enrichment
            query = select(ScientificPaper)

            if skip_existing:
                # Skip papers that already have lay_summary (assuming they're fully enriched)
                query = query.where(
                    (ScientificPaper.lay_summary == None) |
                    (ScientificPaper.lay_summary == "")
                )

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            papers = result.scalars().all()

            total_papers = len(papers)
            logger.info(f"Found {total_papers} papers to enrich")

            if total_papers == 0:
                logger.info("No papers to enrich")
                return

        # Process papers in batches
        for i in range(0, total_papers, self.batch_size):
            batch = papers[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total_papers + self.batch_size - 1) // self.batch_size
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} papers)")

            for paper in batch:
                # Each paper gets its own session
                async with self.session_maker() as session:
                    try:
                        enrichment_service = UnifiedEnrichmentService(session)
                        success = await enrichment_service.enrich_paper_complete(
                            paper.id,
                            skip_doi_enrichment=skip_doi,
                            skip_pdf_processing=skip_pdf,
                            skip_vectorization=skip_vectorization,
                            skip_llm_enrichment=skip_llm,
                        )
                        await enrichment_service.close()

                        if success:
                            self.enriched_count += 1
                        else:
                            self.error_count += 1
                            error_msg = f"Enrichment returned False for paper {paper.id}"
                            self.errors.append(error_msg)

                    except Exception as e:
                        self.error_count += 1
                        error_msg = f"Error enriching paper {paper.id} ({paper.title[:50] if paper.title else 'Untitled'}): {str(e)}"
                        logger.error(error_msg)
                        self.errors.append(error_msg)

                    self.processed_count += 1

                    # Progress update
                    if self.processed_count % 10 == 0:
                        logger.info(
                            f"Progress: {self.processed_count}/{total_papers} "
                            f"({100 * self.processed_count / total_papers:.1f}%) - "
                            f"Enriched: {self.enriched_count}, Errors: {self.error_count}"
                        )

        # Final summary
        self.print_summary()

    def print_summary(self):
        """Print enrichment summary."""
        logger.info("=" * 60)
        logger.info("UNIFIED ENRICHMENT PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total processed: {self.processed_count}")
        logger.info(f"Successfully enriched: {self.enriched_count}")
        logger.info(f"Errors: {self.error_count}")
        logger.info(f"Skipped: {self.skipped_count}")

        if self.errors:
            logger.info("\nFirst 10 errors:")
            for error in self.errors[:10]:
                logger.info(f"  - {error}")
            if len(self.errors) > 10:
                logger.info(f"  ... and {len(self.errors) - 10} more errors")

        logger.info("=" * 60)


async def main():
    parser = argparse.ArgumentParser(
        description="Unified enrichment pipeline for scientific papers"
    )
    parser.add_argument(
        "--paper-id",
        type=int,
        help="Enrich a specific paper by ID (on-demand enrichment)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of papers to process (only used with --all)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Enrich all papers (default if --paper-id not specified)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip papers that already have lay_summary"
    )
    parser.add_argument(
        "--skip-doi",
        action="store_true",
        help="Skip DOI metadata enrichment"
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Skip PDF processing"
    )
    parser.add_argument(
        "--skip-vectorization",
        action="store_true",
        help="Skip vectorization"
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM enrichment"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of papers to process in batch (default: 5, only used with --all)"
    )

    args = parser.parse_args()

    # Create async engine
    engine = create_async_engine(config.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Run enrichment pipeline
    pipeline = UnifiedEnrichmentPipeline(async_session, batch_size=args.batch_size)

    try:
        # If paper-id specified, enrich just that paper
        if args.paper_id:
            logger.info(f"Enriching paper {args.paper_id} on demand...")
            success = await pipeline.enrich_paper_by_id(
                args.paper_id,
                skip_doi=args.skip_doi,
                skip_pdf=args.skip_pdf,
                skip_vectorization=args.skip_vectorization,
                skip_llm=args.skip_llm,
            )
            if success:
                logger.info(f"✅ Successfully enriched paper {args.paper_id}")
            else:
                logger.error(f"❌ Failed to enrich paper {args.paper_id}")
        else:
            # Enrich all papers
            await pipeline.enrich_all_papers(
                limit=args.limit,
                skip_existing=args.skip_existing,
                skip_doi=args.skip_doi,
                skip_pdf=args.skip_pdf,
                skip_vectorization=args.skip_vectorization,
                skip_llm=args.skip_llm,
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
