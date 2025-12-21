#!/usr/bin/env python3
"""
Comprehensive enrichment pipeline for scientific papers.

This script performs:
1. PDF text extraction (full_text extraction)
2. Metadata extraction (DOI, dates, journal, authors)
3. File hash and size calculation
4. Document content update
5. Text chunking
6. Embedding generation for documents and chunks

Usage:
    python scripts/enrich_papers_full_pipeline.py [--limit N] [--skip-existing] [--batch-size N]
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import fitz  # PyMuPDF

from app.db import ScientificPaper, Document, Chunk
from app.services.pdf_processor import PDFProcessor
from app.services.embedding_service import EmbeddingService
from app.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PaperEnrichmentPipeline:
    """Comprehensive enrichment pipeline for scientific papers."""

    def __init__(self, session_maker, batch_size: int = 10):
        self.session_maker = session_maker
        self.batch_size = batch_size

        # Stats
        self.processed_count = 0
        self.enriched_count = 0
        self.vectorized_count = 0
        self.error_count = 0
        self.skipped_count = 0
        self.errors = []

    async def enrich_all_papers(
        self,
        limit: Optional[int] = None,
        skip_existing: bool = False
    ):
        """
        Enrich all papers in the database.

        Args:
            limit: Maximum number of papers to process
            skip_existing: Skip papers that already have full_text
        """
        logger.info("Starting paper enrichment pipeline...")

        async with self.session_maker() as session:
            # Get papers that need enrichment
            query = select(ScientificPaper).join(Document)

            if skip_existing:
                # Skip papers that already have full text
                query = query.where(
                    (ScientificPaper.full_text == None) |
                    (ScientificPaper.full_text == "")
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
            logger.info(f"Processing batch {i // self.batch_size + 1}/{(total_papers + self.batch_size - 1) // self.batch_size}")

            for paper in batch:
                # Each paper gets its own session to avoid issues
                async with self.session_maker() as session:
                    try:
                        await self._enrich_paper(session, paper.id)
                        self.enriched_count += 1
                    except Exception as e:
                        self.error_count += 1
                        error_msg = f"Error enriching paper {paper.id} ({paper.title[:50]}): {str(e)}"
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

    async def _enrich_paper(self, session: AsyncSession, paper_id: int):
        """
        Enrich a single paper with full pipeline.

        Args:
            session: Database session
            paper_id: ID of paper to enrich
        """
        # Get paper with document
        stmt = select(ScientificPaper).where(ScientificPaper.id == paper_id)
        result = await session.execute(stmt)
        paper = result.scalar_one()

        # Get document
        doc_stmt = select(Document).where(Document.id == paper.document_id)
        doc_result = await session.execute(doc_stmt)
        document = doc_result.scalar_one()

        # Step 1: Build full PDF path
        pdf_path = self._get_pdf_path(paper.file_path)

        if not os.path.exists(pdf_path):
            logger.warning(f"PDF not found: {pdf_path} for paper {paper_id}")
            self.skipped_count += 1
            return

        # Step 2: Extract text and metadata from PDF
        logger.debug(f"Extracting from {pdf_path}")
        pdf_processor = PDFProcessor(session)

        try:
            # Process PDF - this returns all extracted data including hash, metadata, and text
            pdf_data = await pdf_processor.process_pdf(pdf_path)

            if pdf_data.get("processing_status") == "failed":
                raise Exception(f"PDF processing failed: {pdf_data.get('extraction_metadata', {}).get('error')}")

            full_text = pdf_data.get("full_text", "")
            file_hash = pdf_data.get("file_hash")
            file_size = pdf_data.get("file_size")
            metadata = pdf_data.get("extraction_metadata", {})

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise

        # Step 3: Update paper record with extracted data
        if full_text and len(full_text.strip()) > 0:
            paper.full_text = full_text

        # Update metadata fields if available
        if pdf_data.get("doi"):
            paper.doi = pdf_data["doi"]
        if pdf_data.get("publication_year"):
            paper.publication_year = pdf_data["publication_year"]
        if pdf_data.get("journal"):
            paper.journal = pdf_data["journal"]
        if pdf_data.get("authors"):
            paper.authors = pdf_data["authors"]
        if pdf_data.get("abstract") and not paper.abstract:
            paper.abstract = pdf_data["abstract"]
        if pdf_data.get("keywords"):
            paper.keywords = pdf_data["keywords"]

        # Update file info
        paper.file_hash = file_hash
        paper.file_size = file_size
        paper.extraction_metadata = metadata

        # Step 4: Update document content with full text
        if full_text and len(full_text.strip()) > 0:
            document.content = full_text
        elif paper.abstract:
            # Fall back to abstract if full text extraction failed
            document.content = paper.abstract

        # Commit paper and document updates
        await session.commit()
        await session.refresh(paper)
        await session.refresh(document)

        logger.debug(f"Updated paper {paper_id} with text length: {len(full_text) if full_text else 0}")

        # Step 5: Generate embeddings and chunks
        await self._vectorize_document(session, document)

        self.vectorized_count += 1

    async def _vectorize_document(self, session: AsyncSession, document: Document):
        """
        Vectorize a document: chunk it and generate embeddings.

        Args:
            session: Database session
            document: Document to vectorize
        """
        embedding_service = EmbeddingService(session)

        # Generate document-level embedding
        if document.content and len(document.content.strip()) > 0:
            doc_embedding = await embedding_service.embed_text(document.content[:5000])  # Limit to first 5000 chars

            if doc_embedding and len(doc_embedding) > 0:
                document.embedding = doc_embedding
                logger.debug(f"Generated document embedding: {len(doc_embedding)} dimensions")

        # Generate chunks and chunk embeddings
        if document.content and len(document.content.strip()) > 100:
            # Delete existing chunks for this document
            delete_stmt = select(Chunk).where(Chunk.document_id == document.id)
            result = await session.execute(delete_stmt)
            existing_chunks = result.scalars().all()
            for chunk in existing_chunks:
                await session.delete(chunk)

            # Create new chunks using the chunker
            chunks = embedding_service.chunker.chunk(document.content)

            logger.debug(f"Created {len(chunks)} chunks for document {document.id}")

            # Generate embeddings for each chunk
            for i, chunk_obj in enumerate(chunks):
                chunk_text = chunk_obj.text if hasattr(chunk_obj, 'text') else str(chunk_obj)
                chunk_embedding = await embedding_service.embed_text(chunk_text)

                if chunk_embedding and len(chunk_embedding) > 0:
                    chunk = Chunk(
                        document_id=document.id,
                        content=chunk_text,
                        embedding=chunk_embedding
                    )
                    session.add(chunk)

        # Commit all embeddings
        await session.commit()
        logger.debug(f"Vectorized document {document.id}")

    def _get_pdf_path(self, file_path: str) -> str:
        """
        Build full PDF path from relative file_path.

        Args:
            file_path: Relative path from database (e.g., "devonthink_import/UUID")

        Returns:
            Full absolute path to PDF
        """
        # Get PDF storage root from config
        storage_root = Path(config.PDF_STORAGE_ROOT)

        # Make it absolute relative to backend directory if it's relative
        if not storage_root.is_absolute():
            backend_dir = Path(__file__).parent.parent
            storage_root = backend_dir / storage_root

        # Append .pdf extension if not present
        if not file_path.endswith('.pdf'):
            file_path = f"{file_path}.pdf"

        full_path = storage_root / file_path
        return str(full_path)

    def print_summary(self):
        """Print enrichment summary."""
        logger.info("\n" + "=" * 60)
        logger.info("ENRICHMENT PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total processed: {self.processed_count}")
        logger.info(f"Successfully enriched: {self.enriched_count}")
        logger.info(f"Vectorized: {self.vectorized_count}")
        logger.info(f"Skipped (missing PDF): {self.skipped_count}")
        logger.info(f"Errors: {self.error_count}")

        if self.errors:
            logger.info("\nErrors encountered:")
            for error in self.errors[:10]:  # Show first 10 errors
                logger.info(f"  - {error}")
            if len(self.errors) > 10:
                logger.info(f"  ... and {len(self.errors) - 10} more errors")

        logger.info("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Enrich papers with full pipeline")
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of papers to process"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip papers that already have full_text"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of papers to process in parallel (default: 10)"
    )

    args = parser.parse_args()

    # Create async engine
    engine = create_async_engine(config.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Run enrichment pipeline
    pipeline = PaperEnrichmentPipeline(async_session, batch_size=args.batch_size)

    try:
        await pipeline.enrich_all_papers(
            limit=args.limit,
            skip_existing=args.skip_existing
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
