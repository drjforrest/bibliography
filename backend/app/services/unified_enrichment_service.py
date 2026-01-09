"""
Unified enrichment service that coordinates all enrichment steps.

This service ensures papers get complete enrichment by coordinating:
1. DOI metadata enrichment (Crossref/Semantic Scholar)
2. PDF processing (text extraction, metadata from PDF)
3. Vectorization (embeddings and chunks)
4. LLM enrichment (lay summaries, insights, citations)

All steps are coordinated and run in the correct order.
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import ScientificPaper, Document
from app.services.crossref_service import CrossrefService
from app.services.embedding_service import EmbeddingService
from app.services.llm_enrichment_service import LLMEnrichmentService
from app.services.pdf_processor import PDFProcessor
from app.services.semantic_scholar_service import SemanticScholarService

logger = logging.getLogger(__name__)


class UnifiedEnrichmentService:
    """Unified service that coordinates all enrichment steps."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.crossref_service = CrossrefService()
        self.semantic_scholar_service = SemanticScholarService()
        self.pdf_processor = PDFProcessor(session)
        self.embedding_service = EmbeddingService(session)
        self.llm_enrichment = LLMEnrichmentService(session)

    async def enrich_paper_complete(
        self,
        paper_id: int,
        skip_doi_enrichment: bool = False,
        skip_pdf_processing: bool = False,
        skip_vectorization: bool = False,
        skip_llm_enrichment: bool = False,
    ) -> bool:
        """
        Run complete enrichment pipeline for a paper.

        Steps (in order):
        1. DOI metadata enrichment (if DOI exists and not skipped)
        2. PDF processing (if PDF exists and not skipped)
        3. Vectorization (if not skipped)
        4. LLM enrichment (if not skipped)

        Args:
            paper_id: ID of paper to enrich
            skip_doi_enrichment: Skip DOI metadata fetching
            skip_pdf_processing: Skip PDF text extraction
            skip_vectorization: Skip embedding generation
            skip_llm_enrichment: Skip LLM content generation

        Returns:
            True if enrichment succeeded, False otherwise
        """
        try:
            # Get paper
            stmt = select(ScientificPaper).where(ScientificPaper.id == paper_id)
            result = await self.session.execute(stmt)
            paper = result.scalar_one_or_none()

            if not paper:
                logger.error(f"Paper {paper_id} not found")
                return False

            logger.info(
                f"Starting complete enrichment for paper {paper_id}: {paper.title[:60] if paper.title else 'Untitled'}"
            )

            # Step 1: DOI metadata enrichment
            if not skip_doi_enrichment and paper.doi:
                logger.info(f"Step 1/4: DOI metadata enrichment for paper {paper_id}")
                await self._enrich_from_doi(paper)
            elif not paper.doi:
                logger.debug(f"Skipping DOI enrichment - no DOI for paper {paper_id}")
            else:
                logger.debug(f"Skipping DOI enrichment (skipped by flag)")

            # Refresh paper to get updated metadata
            await self.session.refresh(paper)

            # Step 2: PDF processing (extract full_text and metadata from PDF)
            if not skip_pdf_processing and paper.file_path:
                logger.info(f"Step 2/4: PDF processing for paper {paper_id}")
                await self._process_pdf(paper)
            elif not paper.file_path:
                logger.debug(f"Skipping PDF processing - no file_path for paper {paper_id}")
            else:
                logger.debug(f"Skipping PDF processing (skipped by flag)")

            # Refresh paper and document
            await self.session.refresh(paper)
            if paper.document_id:
                doc_stmt = select(Document).where(Document.id == paper.document_id)
                doc_result = await self.session.execute(doc_stmt)
                document = doc_result.scalar_one_or_none()
            else:
                document = None

            # Step 3: Vectorization (embeddings and chunks)
            if not skip_vectorization and document:
                logger.info(f"Step 3/4: Vectorization for paper {paper_id}")
                await self._vectorize_document(document)
            elif not document:
                logger.debug(f"Skipping vectorization - no document for paper {paper_id}")
            else:
                logger.debug(f"Skipping vectorization (skipped by flag)")

            # Step 4: LLM enrichment (lay summary, insights, citations)
            if not skip_llm_enrichment:
                logger.info(f"Step 4/4: LLM enrichment for paper {paper_id}")
                await self.llm_enrichment.enrich_paper(paper_id)
            else:
                logger.debug(f"Skipping LLM enrichment (skipped by flag)")

            logger.info(f"✅ Completed complete enrichment for paper {paper_id}")
            return True

        except Exception as e:
            logger.error(f"Error in complete enrichment for paper {paper_id}: {str(e)}")
            await self.session.rollback()
            return False

    async def _enrich_from_doi(self, paper: ScientificPaper):
        """Enrich paper metadata from DOI using Crossref and Semantic Scholar."""
        try:
            doi = paper.doi.strip() if paper.doi else None
            if not doi:
                return

            logger.debug(f"Fetching metadata for DOI: {doi}")

            # Try Crossref first (best for volume, issue, pages, journal)
            crossref_data = None
            try:
                crossref_data = await self.crossref_service.get_paper_by_doi(doi)
                if crossref_data:
                    logger.debug(f"✓ Found in Crossref: {len(crossref_data)} fields")
            except Exception as e:
                logger.warning(f"Crossref fetch failed: {e}")

            # Try Semantic Scholar as fallback
            s2_data = None
            try:
                s2_data = await self.semantic_scholar_service.get_paper_by_doi(doi)
                if s2_data:
                    logger.debug(f"✓ Found in Semantic Scholar: {len(s2_data)} fields")
            except Exception as e:
                logger.warning(f"Semantic Scholar fetch failed: {e}")

            # Merge metadata (prefer Crossref, use S2 for missing)
            merged_data = self._merge_metadata(crossref_data, s2_data)

            if not merged_data:
                logger.warning(f"DOI {doi} not found in any API")
                return

            # Update paper fields (only if missing or better)
            updated_fields = []

            if merged_data.get("title") and (not paper.title or len(merged_data["title"]) > len(paper.title)):
                paper.title = merged_data["title"]
                updated_fields.append("title")

            if merged_data.get("abstract") and (not paper.abstract or len(merged_data["abstract"]) > len(paper.abstract) + 100):
                paper.abstract = merged_data["abstract"]
                updated_fields.append("abstract")

            if merged_data.get("journal") and not paper.journal:
                paper.journal = merged_data["journal"]
                updated_fields.append("journal")

            if merged_data.get("volume") and not paper.volume:
                paper.volume = merged_data["volume"]
                updated_fields.append("volume")

            if merged_data.get("issue") and not paper.issue:
                paper.issue = merged_data["issue"]
                updated_fields.append("issue")

            if merged_data.get("pages") and not paper.pages:
                paper.pages = merged_data["pages"]
                updated_fields.append("pages")

            if merged_data.get("publication_year") and not paper.publication_year:
                paper.publication_year = merged_data["publication_year"]
                updated_fields.append("publication_year")

            if merged_data.get("authors") and not paper.authors:
                paper.authors = merged_data["authors"]
                updated_fields.append("authors")

            if merged_data.get("keywords") and not paper.keywords:
                paper.keywords = merged_data["keywords"]
                updated_fields.append("keywords")

            if updated_fields:
                logger.info(f"  Updated {len(updated_fields)} field(s): {', '.join(updated_fields)}")
                await self.session.commit()
            else:
                logger.debug("  No fields needed updating")

        except Exception as e:
            logger.error(f"Error enriching from DOI: {str(e)}")
            # Don't raise - continue with other enrichment steps

    def _merge_metadata(self, crossref_data: Optional[dict], s2_data: Optional[dict]) -> Optional[dict]:
        """Merge metadata from Crossref and Semantic Scholar (prefer Crossref)."""
        if not crossref_data and not s2_data:
            return None

        merged = {}

        # Prefer Crossref for structured fields
        if crossref_data:
            merged.update(crossref_data)

        # Fill in missing fields from Semantic Scholar
        if s2_data:
            for key, value in s2_data.items():
                if key not in merged or not merged[key]:
                    merged[key] = value

        return merged if merged else None

    async def _process_pdf(self, paper: ScientificPaper):
        """Process PDF to extract full_text and metadata."""
        try:
            if not paper.file_path:
                return

            # Build PDF path
            from pathlib import Path
            from app.config import config

            storage_root = Path(config.PDF_STORAGE_ROOT)
            pdf_path = storage_root / paper.file_path

            if not pdf_path.exists():
                logger.warning(f"PDF not found: {pdf_path}")
                return

            logger.debug(f"Processing PDF: {pdf_path}")

            # Process PDF
            pdf_data = await self.pdf_processor.process_pdf(str(pdf_path))

            if pdf_data.get("processing_status") == "failed":
                logger.warning(f"PDF processing failed: {pdf_data.get('extraction_metadata', {}).get('error')}")
                return

            # Update paper with extracted data
            updated_fields = []

            if pdf_data.get("full_text") and (not paper.full_text or len(pdf_data["full_text"]) > len(paper.full_text)):
                paper.full_text = pdf_data["full_text"]
                updated_fields.append("full_text")

            # Update document content
            if paper.document_id:
                doc_stmt = select(Document).where(Document.id == paper.document_id)
                doc_result = await self.session.execute(doc_stmt)
                document = doc_result.scalar_one_or_none()

                if document and pdf_data.get("full_text"):
                    document.content = pdf_data["full_text"]
                    updated_fields.append("document.content")

            # Update metadata fields if missing
            if pdf_data.get("doi") and not paper.doi:
                paper.doi = pdf_data["doi"]
                updated_fields.append("doi")

            if pdf_data.get("publication_year") and not paper.publication_year:
                paper.publication_year = pdf_data["publication_year"]
                updated_fields.append("publication_year")

            if pdf_data.get("journal") and not paper.journal:
                paper.journal = pdf_data["journal"]
                updated_fields.append("journal")

            if pdf_data.get("authors") and not paper.authors:
                paper.authors = pdf_data["authors"]
                updated_fields.append("authors")

            if pdf_data.get("abstract") and not paper.abstract:
                paper.abstract = pdf_data["abstract"]
                updated_fields.append("abstract")

            if pdf_data.get("keywords") and not paper.keywords:
                paper.keywords = pdf_data["keywords"]
                updated_fields.append("keywords")

            if pdf_data.get("file_hash") and not paper.file_hash:
                paper.file_hash = pdf_data["file_hash"]
                updated_fields.append("file_hash")

            if pdf_data.get("file_size") and not paper.file_size:
                paper.file_size = pdf_data["file_size"]
                updated_fields.append("file_size")

            if updated_fields:
                logger.info(f"  Updated {len(updated_fields)} field(s) from PDF")
                await self.session.commit()
            else:
                logger.debug("  No fields needed updating from PDF")

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            # Don't raise - continue with other enrichment steps

    async def _vectorize_document(self, document: Document):
        """Vectorize document: generate embeddings and chunks."""
        try:
            if not document.content or len(document.content.strip()) == 0:
                logger.warning(f"Document {document.id} has no content to vectorize")
                return

            # Generate document-level embedding
            doc_embedding = await self.embedding_service.embed_text(document.content[:5000])
            if doc_embedding and len(doc_embedding) > 0:
                document.embedding = doc_embedding
                logger.debug(f"  Generated document embedding: {len(doc_embedding)} dimensions")

            # Create and embed chunks
            if len(document.content.strip()) > 100:
                chunks = self.embedding_service.chunker.chunk(document.content)
                logger.debug(f"  Created {len(chunks)} chunks")

                # Delete existing chunks
                from app.db import Chunk
                from sqlalchemy import select

                delete_stmt = select(Chunk).where(Chunk.document_id == document.id)
                result = await self.session.execute(delete_stmt)
                existing_chunks = result.scalars().all()
                for chunk in existing_chunks:
                    await self.session.delete(chunk)

                # Generate embeddings for each chunk
                for chunk_obj in chunks:
                    chunk_text = chunk_obj.text if hasattr(chunk_obj, 'text') else str(chunk_obj)
                    chunk_embedding = await self.embedding_service.embed_text(chunk_text)

                    if chunk_embedding and len(chunk_embedding) > 0:
                        from app.db import Chunk
                        chunk = Chunk(
                            document_id=document.id,
                            content=chunk_text,
                            embedding=chunk_embedding
                        )
                        self.session.add(chunk)

            await self.session.commit()
            logger.info(f"  ✓ Vectorized document {document.id}")

        except Exception as e:
            logger.error(f"Error vectorizing document: {str(e)}")
            # Don't raise - continue with other enrichment steps

    async def close(self):
        """Clean up resources."""
        await self.crossref_service.close()
        await self.semantic_scholar_service.close()
        await self.llm_enrichment.close()
