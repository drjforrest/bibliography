#!/usr/bin/env python3
"""
Backfill missing metadata for scientific papers using DOI enrichment.

This script:
1. Finds papers with missing metadata (abstract, journal, publication_year, etc.)
2. Checks if DOI exists (in database or extractable from PDF)
3. Uses Semantic Scholar API to fetch metadata by DOI
4. Updates papers with enriched metadata

Usage:
    python scripts/backfill_metadata_from_doi.py [--limit N] [--dry-run] [--check-all]
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from app.config import config
from app.db import Document, ScientificPaper
from app.services.crossref_service import CrossrefService
from app.services.llm_enrichment_service import LLMEnrichmentService
from app.services.pdf_processor import PDFProcessor
from app.services.semantic_scholar_service import GRAPH_API, SemanticScholarService
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MetadataBackfillPipeline:
    """Backfill missing metadata for scientific papers using DOI enrichment."""

    def __init__(
        self, session_maker, dry_run: bool = False, force_overwrite: bool = True
    ):
        self.session_maker = session_maker
        self.dry_run = dry_run
        self.force_overwrite = (
            force_overwrite  # If True, overwrite existing fields with better data
        )

        # Initialize services
        api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
        self.s2_service = SemanticScholarService(api_key=api_key)
        self.crossref_service = CrossrefService()

        # Stats
        self.processed_count = 0
        self.enriched_count = 0
        self.skipped_no_doi = 0
        self.skipped_no_pdf = 0
        self.error_count = 0
        self.not_found_count = 0
        self.crossref_success = 0
        self.semantic_scholar_success = 0
        self.llm_success = 0
        self.errors = []
        # Track successes and failures
        self.successful_papers = []  # List of (paper_id, title, fields_updated)
        self.failed_papers = []  # List of (paper_id, title, reason)
        self.skipped_papers = []  # List of (paper_id, title, reason)

    async def close(self):
        """Close resources."""
        await self.s2_service.close()
        await self.crossref_service.close()

    def _is_metadata_complete(self, paper: ScientificPaper) -> bool:
        """
        Check if paper has sufficient metadata.

        A paper is considered complete if it has all critical fields:
        - abstract (at least 50 chars)
        - journal
        - publication_year
        - authors (non-empty list)
        - doi

        Args:
            paper: ScientificPaper record

        Returns:
            True if metadata is complete, False otherwise
        """
        has_abstract = paper.abstract and len(paper.abstract.strip()) > 50
        has_journal = paper.journal and len(paper.journal.strip()) > 0
        has_year = paper.publication_year is not None
        has_authors = paper.authors and len(paper.authors) > 0
        has_doi = paper.doi and len(paper.doi.strip()) > 0

        # Paper is complete if it has abstract, journal, year, authors, and DOI
        return has_abstract and has_journal and has_year and has_authors and has_doi

    def _already_enriched_with_doi(self, paper: ScientificPaper) -> bool:
        """
        Check if paper was already enriched using DOI.

        Args:
            paper: ScientificPaper record

        Returns:
            True if already enriched with DOI, False otherwise
        """
        if not paper.extraction_metadata:
            return False

        return "doi_enrichment" in paper.extraction_metadata

    async def find_papers_needing_enrichment(
        self,
        check_all: bool = True,  # Default to True since most fields are wrong/incomplete
        limit: Optional[int] = None,
    ) -> List[ScientificPaper]:
        """
        Find papers that need metadata enrichment.

        Args:
            check_all: If True, check all papers; if False, only check incomplete ones
            limit: Maximum number of papers to return

        Returns:
            List of ScientificPaper records needing enrichment
        """
        async with self.session_maker() as session:
            query = select(ScientificPaper).join(Document)

            if not check_all:
                # Only find papers missing metadata
                # Papers are incomplete if they're missing key fields we care about
                query = query.where(
                    or_(
                        # Missing abstract or very short
                        ScientificPaper.abstract.is_(None),
                        ScientificPaper.abstract == "",
                        # Missing journal
                        ScientificPaper.journal.is_(None),
                        ScientificPaper.journal == "",
                        # Missing publication year
                        ScientificPaper.publication_year.is_(None),
                        # Missing authors or empty list
                        ScientificPaper.authors.is_(None),
                        # Missing volume
                        ScientificPaper.volume.is_(None),
                        ScientificPaper.volume == "",
                        # Missing issue
                        ScientificPaper.issue.is_(None),
                        ScientificPaper.issue == "",
                        # Missing pages
                        ScientificPaper.pages.is_(None),
                        ScientificPaper.pages == "",
                        # Missing DOI
                        ScientificPaper.doi.is_(None),
                        ScientificPaper.doi == "",
                        # Missing keywords or empty list
                        ScientificPaper.keywords.is_(None),
                        # Missing lay_summary
                        ScientificPaper.lay_summary.is_(None),
                        ScientificPaper.lay_summary == "",
                    )
                )

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            papers = result.scalars().all()

            # If check_all is False, filter to only include incomplete papers
            # If check_all is True, return all papers (for fixing incorrect data)
            if not check_all:
                papers = [p for p in papers if not self._is_metadata_complete(p)]

            return papers

    def _get_pdf_path(self, file_path: str) -> str:
        """
        Build full PDF path from relative file_path.

        Args:
            file_path: Relative path from database (e.g., "2024/01/uuid")

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
        if not file_path.endswith(".pdf"):
            file_path = f"{file_path}.pdf"

        full_path = storage_root / file_path
        return str(full_path)

    async def _extract_doi_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract DOI from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            DOI string or None
        """
        try:
            if not os.path.exists(pdf_path):
                return None

            async with self.session_maker() as session:
                pdf_processor = PDFProcessor(session)
                pdf_data = await pdf_processor.process_pdf(pdf_path)
                return pdf_data.get("doi")
        except Exception as e:
            logger.debug(f"Error extracting DOI from PDF {pdf_path}: {e}")
            return None

    async def _fetch_from_crossref(self, doi: str) -> Optional[Dict]:
        """
        Fetch paper metadata from Crossref API.

        Crossref has the best metadata for volume, issue, pages, journal.

        Args:
            doi: DOI string

        Returns:
            Normalized paper data dict or None if not found
        """
        try:
            logger.debug(f"Fetching from Crossref for DOI: {doi}")
            data = await self.crossref_service.get_paper_by_doi(doi)
            if data:
                logger.debug(f"✓ Found in Crossref: {len(data)} fields")
                self.crossref_success += 1
            return data
        except Exception as e:
            logger.warning(f"Error fetching from Crossref: {e}")
            return None

    async def _fetch_from_semantic_scholar(self, doi: str) -> Optional[Dict]:
        """
        Fetch paper metadata from Semantic Scholar API with extended fields.

        Args:
            doi: DOI string

        Returns:
            Paper data dict or None if not found
        """
        try:
            # Request extended fields from Semantic Scholar API
            url = f"{GRAPH_API}/paper/DOI:{doi}"
            fields = [
                "paperId",
                "title",
                "abstract",
                "year",
                "authors",
                "url",
                "citationCount",
                "venue",
                "volume",
                "issue",
                "pages",
                "fieldsOfStudy",
                "keywords",
                "isOpenAccess",
            ]
            params = {"fields": ",".join(fields)}

            api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
            headers = {}
            if api_key:
                headers["x-api-key"] = api_key

            timeout = httpx.Timeout(30.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(f"Fetching from Semantic Scholar for DOI: {doi}")
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                if data:
                    # Normalize Semantic Scholar data
                    normalized = self._normalize_semantic_scholar_data(data)
                    if normalized:
                        logger.debug(
                            f"✓ Found in Semantic Scholar: {len(normalized)} fields"
                        )
                        self.semantic_scholar_success += 1
                    return normalized
                return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"⚠️ Paper not found in Semantic Scholar: {doi}")
                return None
            logger.warning(f"Error fetching from Semantic Scholar: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching from Semantic Scholar: {e}")
            return None

    def _normalize_semantic_scholar_data(self, s2_data: Dict) -> Dict:
        """Normalize Semantic Scholar API response to our schema."""
        normalized = {}

        if s2_data.get("title"):
            normalized["title"] = s2_data["title"]

        if s2_data.get("abstract"):
            normalized["abstract"] = s2_data["abstract"]

        if s2_data.get("venue"):
            normalized["journal"] = s2_data["venue"]

        if s2_data.get("volume"):
            normalized["volume"] = str(s2_data["volume"])

        if s2_data.get("issue"):
            normalized["issue"] = str(s2_data["issue"])

        if s2_data.get("pages"):
            normalized["pages"] = s2_data["pages"]

        if s2_data.get("year"):
            normalized["publication_year"] = int(s2_data["year"])

        # Authors
        authors = []
        if s2_data.get("authors"):
            for author in s2_data["authors"]:
                if isinstance(author, dict):
                    name = author.get("name")
                    if not name:
                        first = author.get("firstName", "")
                        last = author.get("lastName", "")
                        name = f"{first} {last}".strip()
                    if name:
                        authors.append(name)
                elif isinstance(author, str):
                    authors.append(author)
        if authors:
            normalized["authors"] = authors

        # Keywords
        keywords = []
        if s2_data.get("keywords"):
            for kw in s2_data["keywords"]:
                if isinstance(kw, str) and kw not in keywords:
                    keywords.append(kw)
                elif isinstance(kw, dict):
                    phrase = kw.get("phrase") or kw.get("word")
                    if phrase and phrase not in keywords:
                        keywords.append(phrase)

        # Use fieldsOfStudy as fallback for keywords
        if not keywords and s2_data.get("fieldsOfStudy"):
            keywords = [f for f in s2_data["fieldsOfStudy"] if f and isinstance(f, str)]

        if keywords:
            normalized["keywords"] = keywords

        # Subject areas
        if s2_data.get("fieldsOfStudy"):
            subject_areas = [
                f for f in s2_data["fieldsOfStudy"] if f and isinstance(f, str)
            ]
            if subject_areas:
                normalized["subject_areas"] = subject_areas

        if s2_data.get("citationCount") is not None:
            normalized["citation_count"] = int(s2_data["citationCount"])

        if s2_data.get("isOpenAccess") is not None:
            normalized["is_open_access"] = bool(s2_data["isOpenAccess"])

        return normalized

    def _merge_metadata(self, primary: Dict, fallback: Dict) -> Dict:
        """
        Merge metadata from two sources, preferring primary but using fallback for missing fields.

        Args:
            primary: Primary metadata source (Crossref - preferred for volume, issue, pages)
            fallback: Fallback metadata source (Semantic Scholar)

        Returns:
            Merged metadata dictionary
        """
        merged = primary.copy() if primary else {}
        fallback = fallback or {}

        # Fields where Crossref is preferred (volume, issue, pages, journal)
        preferred_from_primary = ["volume", "issue", "pages", "journal"]
        for field in preferred_from_primary:
            if not merged.get(field) and fallback.get(field):
                merged[field] = fallback[field]

        # Other fields: use fallback if primary doesn't have them
        for field, value in fallback.items():
            if field not in merged or not merged[field]:
                merged[field] = value

        return merged

    async def _enrich_paper_from_doi(
        self, session: AsyncSession, paper: ScientificPaper, doi: str
    ) -> bool:
        """
        Enrich paper metadata using DOI via Crossref and Semantic Scholar APIs.

        Strategy:
        1. First try Crossref (best for volume, issue, pages, journal)
        2. Fall back to Semantic Scholar for missing fields
        3. Generate lay_summary using LLM if missing

        Populates all fields user cares about:
        - authors, journal, volume, issue, pages, publication_year, doi, abstract,
          lay_summary (generated via LLM), keywords

        Args:
            session: Database session
            paper: ScientificPaper record to enrich
            doi: DOI string

        Returns:
            True if enrichment succeeded, False otherwise
        """
        try:
            logger.info(f"Fetching metadata for DOI: {doi}")

            # Step 1: Try Crossref first (best metadata quality)
            crossref_data = await self._fetch_from_crossref(doi)

            # Step 2: Try Semantic Scholar as fallback
            s2_data = await self._fetch_from_semantic_scholar(doi)

            # Step 3: Merge metadata (prefer Crossref, use S2 for missing)
            merged_data = self._merge_metadata(crossref_data, s2_data)

            if not merged_data:
                paper_title = paper.title[:60] if paper.title else "Untitled"
                logger.warning(f"  ⚠️ NOT FOUND - Paper {paper.id}: '{paper_title}'")
                logger.warning(
                    f"     DOI {doi} not found in Crossref or Semantic Scholar"
                )

                # Track as failed
                self.failed_papers.append(
                    {
                        "paper_id": paper.id,
                        "title": paper.title,
                        "doi": doi,
                        "error": "Not found in any API",
                    }
                )

                self.not_found_count += 1
                return False

            # Update paper with merged metadata
            # With force_overwrite=True, we update fields even if they exist (to fix incorrect data)
            updated_fields = []

            # Title (update if better/more complete, or if force_overwrite)
            if merged_data.get("title"):
                should_update = (
                    self.force_overwrite
                    or not paper.title
                    or len(merged_data["title"]) > len(paper.title)
                )
                if should_update:
                    if not self.dry_run:
                        paper.title = merged_data["title"]
                    updated_fields.append("title")

            # Abstract (update if missing/short, or if force_overwrite and better)
            if merged_data.get("abstract"):
                should_update = (
                    self.force_overwrite
                    or not paper.abstract
                    or len(paper.abstract) < 50
                    or (
                        len(merged_data["abstract"]) > len(paper.abstract) + 100
                    )  # Significantly better
                )
                if should_update:
                    if not self.dry_run:
                        paper.abstract = merged_data["abstract"]
                    updated_fields.append("abstract")

            # Journal (update if missing, or if force_overwrite)
            if merged_data.get("journal"):
                should_update = (
                    self.force_overwrite
                    or not paper.journal
                    or len(paper.journal.strip()) == 0
                )
                if should_update:
                    if not self.dry_run:
                        paper.journal = merged_data["journal"]
                    updated_fields.append("journal")

            # Volume (update if missing, or if force_overwrite)
            if merged_data.get("volume"):
                should_update = (
                    self.force_overwrite
                    or not paper.volume
                    or len(paper.volume.strip()) == 0
                )
                if should_update:
                    if not self.dry_run:
                        paper.volume = str(merged_data["volume"])
                    updated_fields.append("volume")

            # Issue (update if missing, or if force_overwrite)
            if merged_data.get("issue"):
                should_update = (
                    self.force_overwrite
                    or not paper.issue
                    or len(paper.issue.strip()) == 0
                )
                if should_update:
                    if not self.dry_run:
                        paper.issue = str(merged_data["issue"])
                    updated_fields.append("issue")

            # Pages (update if missing, or if force_overwrite)
            if merged_data.get("pages"):
                should_update = (
                    self.force_overwrite
                    or not paper.pages
                    or len(paper.pages.strip()) == 0
                )
                if should_update:
                    if not self.dry_run:
                        paper.pages = str(merged_data["pages"])
                    updated_fields.append("pages")

            # Publication year (update if missing, or if force_overwrite)
            if merged_data.get("publication_year"):
                should_update = self.force_overwrite or not paper.publication_year
                if should_update:
                    if not self.dry_run:
                        paper.publication_year = int(merged_data["publication_year"])
                    updated_fields.append("publication_year")

            # Authors (update if missing, or if force_overwrite and we have more authors)
            if merged_data.get("authors"):
                authors = merged_data["authors"]
                if isinstance(authors, list) and authors:
                    should_update = (
                        self.force_overwrite
                        or not paper.authors
                        or len(paper.authors) == 0
                        or len(authors) > len(paper.authors)  # More authors available
                    )
                    if should_update:
                        if not self.dry_run:
                            paper.authors = authors
                        updated_fields.append("authors")

            # Keywords (update if missing, or if force_overwrite and we have more keywords)
            if merged_data.get("keywords"):
                keywords = merged_data["keywords"]
                if isinstance(keywords, list) and keywords:
                    should_update = (
                        self.force_overwrite
                        or not paper.keywords
                        or len(paper.keywords) == 0
                        or len(keywords)
                        > len(paper.keywords)  # More keywords available
                    )
                    if should_update:
                        if not self.dry_run:
                            paper.keywords = keywords
                        updated_fields.append("keywords")

            # Subject areas (update if missing, or if force_overwrite)
            if merged_data.get("subject_areas"):
                subject_areas = merged_data["subject_areas"]
                if isinstance(subject_areas, list) and subject_areas:
                    should_update = (
                        self.force_overwrite
                        or not paper.subject_areas
                        or len(paper.subject_areas) == 0
                    )
                    if should_update:
                        if not self.dry_run:
                            paper.subject_areas = subject_areas
                        updated_fields.append("subject_areas")

            # DOI (always ensure it's set correctly)
            if (
                not paper.doi
                or paper.doi.strip() == ""
                or (self.force_overwrite and merged_data.get("doi"))
            ):
                if merged_data.get("doi"):
                    if not self.dry_run:
                        paper.doi = merged_data["doi"]
                    updated_fields.append("doi")

            # Citation count (update if force_overwrite or if we don't have it)
            if merged_data.get("citation_count") is not None:
                should_update = (
                    self.force_overwrite
                    or paper.citation_count is None
                    or paper.citation_count == 0
                )
                if should_update:
                    if not self.dry_run:
                        paper.citation_count = int(merged_data["citation_count"])
                    updated_fields.append("citation_count")

            # Open access status (update if force_overwrite or if we don't have it)
            if merged_data.get("is_open_access") is not None:
                should_update = self.force_overwrite or paper.is_open_access is None
                if should_update:
                    if not self.dry_run:
                        paper.is_open_access = bool(merged_data["is_open_access"])
                    updated_fields.append("is_open_access")

            # Generate lay_summary using LLM if missing or if force_overwrite
            should_generate_lay_summary = (
                not paper.lay_summary
                or len(paper.lay_summary.strip()) == 0
                or (
                    self.force_overwrite and merged_data.get("abstract")
                )  # Re-generate if we have better abstract
            )
            if should_generate_lay_summary and not self.dry_run:
                logger.info(f"  Generating lay_summary using LLM...")
                try:
                    llm_service = LLMEnrichmentService(session)
                    lay_summary = await llm_service._generate_lay_summary(paper)
                    if lay_summary:
                        paper.lay_summary = lay_summary
                        updated_fields.append("lay_summary")
                        self.llm_success += 1
                        logger.info(
                            f"  ✓ Generated lay_summary ({len(lay_summary)} chars)"
                        )
                    else:
                        logger.warning(f"  ⚠ LLM lay_summary generation returned None")
                except Exception as e:
                    logger.warning(f"  ⚠ LLM lay_summary generation failed: {e}")
                    # Don't fail the whole enrichment if LLM fails

            # Determine sources used
            sources_used = []
            if crossref_data:
                sources_used.append("crossref")
            if s2_data:
                sources_used.append("semantic_scholar")

            # Update extraction_metadata to track enrichment
            if not self.dry_run:
                metadata = paper.extraction_metadata or {}
                metadata["doi_enrichment"] = {
                    "sources": sources_used,
                    "doi": doi,
                    "enriched_at": datetime.utcnow().isoformat(),
                    "fields_updated": updated_fields,
                }
                paper.extraction_metadata = metadata

            if not self.dry_run:
                await session.commit()
                await session.refresh(paper)

            # Log success with detailed field information
            paper_title = paper.title[:60] if paper.title else "Untitled"
            logger.info(f"  ✅ SUCCESS - Paper {paper.id}: '{paper_title}'")
            if updated_fields:
                logger.info(
                    f"     Updated {len(updated_fields)} field(s): {', '.join(updated_fields)}"
                )
                # Log field details
                if "abstract" in updated_fields:
                    abstract_len = len(merged_data.get("abstract", ""))
                    logger.info(f"       - abstract: {abstract_len} chars")
                if "authors" in updated_fields:
                    author_count = len(merged_data.get("authors", []))
                    logger.info(f"       - authors: {author_count} author(s)")
                if "keywords" in updated_fields:
                    keyword_count = len(merged_data.get("keywords", []))
                    logger.info(f"       - keywords: {keyword_count} keyword(s)")
                if sources_used:
                    logger.info(f"     Data sources: {', '.join(sources_used)}")
            else:
                logger.info(f"     No fields updated (all data already present)")

            # Track successful paper
            self.successful_papers.append(
                {
                    "paper_id": paper.id,
                    "title": paper.title,
                    "doi": doi,
                    "fields_updated": updated_fields,
                    "sources": sources_used,
                }
            )

            return True

        except Exception as e:
            # Log failure with details
            paper_title = paper.title[:60] if paper.title else "Untitled"
            error_msg = str(e)
            logger.error(f"  ❌ FAILED - Paper {paper.id}: '{paper_title}'")
            logger.error(f"     Error: {error_msg}")

            # Track failed paper
            self.failed_papers.append(
                {
                    "paper_id": paper.id,
                    "title": paper.title,
                    "doi": doi,
                    "error": error_msg,
                }
            )

            self.error_count += 1
            self.errors.append(f"Paper {paper.id} (DOI: {doi}): {error_msg}")
            return False

    async def enrich_all_papers(
        self,
        check_all: bool = True,  # Default to True - check all papers
        limit: Optional[int] = None,
    ):
        """
        Enrich all papers that need metadata backfill.

        Args:
            check_all: If True, check all papers (default); if False, only check incomplete ones
            limit: Maximum number of papers to process
        """
        logger.info("Starting metadata backfill pipeline...")

        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be saved")

        if self.force_overwrite:
            logger.info(
                "⚡ FORCE OVERWRITE MODE - Will update existing fields with better data"
            )

        # Find papers needing enrichment
        papers = await self.find_papers_needing_enrichment(
            check_all=check_all, limit=limit
        )

        total_papers = len(papers)
        logger.info(f"Found {total_papers} papers needing enrichment")

        if total_papers == 0:
            logger.info("No papers need enrichment")
            return

            # Process each paper
        for i, paper in enumerate(papers, 1):
            self.processed_count += 1

            logger.info(
                f"\n[{i}/{total_papers}] Processing paper {paper.id}: "
                f"{paper.title[:60] if paper.title else 'Untitled'}"
            )

            # Skip already enriched papers only if force_overwrite is False
            if not self.force_overwrite and self._already_enriched_with_doi(paper):
                paper_title = paper.title[:60] if paper.title else "Untitled"
                logger.info(f"  ⏭️ SKIPPED - Paper {paper.id}: '{paper_title}'")
                logger.info(
                    f"     Reason: Already enriched with DOI (use --no-overwrite=false to force)"
                )
                self.skipped_papers.append(
                    {
                        "paper_id": paper.id,
                        "title": paper.title,
                        "reason": "Already enriched",
                    }
                )
                continue

            # Get or extract DOI
            doi = None

            if paper.doi:
                doi = paper.doi
                logger.info(f"  DOI: {doi} (from database)")
            else:
                # Try to extract DOI from PDF
                logger.info(f"  Extracting DOI from PDF...")

                # Guard against None file_path
                if not paper.file_path:
                    paper_title = paper.title[:60] if paper.title else "Untitled"
                    logger.warning(f"  ⚠️ SKIPPED - Paper {paper.id}: '{paper_title}'")
                    logger.warning(f"     Reason: PDF file path not available")
                    self.skipped_papers.append(
                        {
                            "paper_id": paper.id,
                            "title": paper.title,
                            "reason": "PDF file path not available",
                        }
                    )
                    self.skipped_no_pdf += 1
                    continue

                pdf_path = self._get_pdf_path(paper.file_path)

                if not os.path.exists(pdf_path):
                    paper_title = paper.title[:60] if paper.title else "Untitled"
                    logger.warning(f"  ⚠️ SKIPPED - Paper {paper.id}: '{paper_title}'")
                    logger.warning(f"     Reason: PDF not found at {pdf_path}")
                    self.skipped_papers.append(
                        {
                            "paper_id": paper.id,
                            "title": paper.title,
                            "reason": f"PDF not found: {pdf_path}",
                        }
                    )
                    self.skipped_no_pdf += 1
                    continue

                doi = await self._extract_doi_from_pdf(pdf_path)

                if not doi:
                    paper_title = paper.title[:60] if paper.title else "Untitled"
                    logger.warning(f"  ⚠️ SKIPPED - Paper {paper.id}: '{paper_title}'")
                    logger.warning(f"     Reason: Could not extract DOI from PDF")
                    self.skipped_papers.append(
                        {
                            "paper_id": paper.id,
                            "title": paper.title,
                            "reason": "Could not extract DOI from PDF",
                        }
                    )
                    self.skipped_no_doi += 1
                    continue

                logger.info(f"  ✓ Extracted DOI from PDF: {doi}")

            # Enrich paper using DOI
            async with self.session_maker() as session:
                # Refresh paper in this session
                result = await session.execute(
                    select(ScientificPaper).where(ScientificPaper.id == paper.id)
                )
                paper = result.scalar_one()

                success = await self._enrich_paper_from_doi(session, paper, doi)

                if success:
                    self.enriched_count += 1

                # Rate limiting: wait a bit between requests to avoid hitting limits
                # Semantic Scholar free tier: 100 requests per 5 minutes
                # Crossref: no rate limits but be respectful
                # Wait 2 seconds between requests to stay well under limit
                if i < total_papers:  # Don't wait after last paper
                    await asyncio.sleep(2)

            # Progress update every 10 papers
            if i % 10 == 0:
                success_count = len(self.successful_papers)
                failed_count = len(self.failed_papers)
                skipped_count = len(self.skipped_papers)
                logger.info(
                    f"\n{'=' * 60}\n"
                    f"Progress: {i}/{total_papers} ({100 * i / total_papers:.1f}%)\n"
                    f"  ✅ Successful: {success_count}\n"
                    f"  ❌ Failed: {failed_count}\n"
                    f"  ⏭️  Skipped: {skipped_count}\n"
                    f"{'=' * 60}\n"
                )

        # Final summary
        self.print_summary()

    def print_summary(self):
        """Print comprehensive enrichment summary."""
        logger.info("\n" + "=" * 80)
        logger.info("METADATA BACKFILL SUMMARY")
        logger.info("=" * 80)

        # Overall statistics
        logger.info(f"\n📊 OVERALL STATISTICS:")
        logger.info(f"  Total processed: {self.processed_count}")
        logger.info(f"  ✅ Successfully enriched: {len(self.successful_papers)}")
        logger.info(f"  ❌ Failed: {len(self.failed_papers)}")
        logger.info(f"  ⏭️  Skipped: {len(self.skipped_papers)}")

        # Breakdown of skips
        if self.skipped_papers:
            logger.info(f"\n  Skip reasons:")
            logger.info(f"    - No DOI found: {self.skipped_no_doi}")
            logger.info(f"    - No PDF found: {self.skipped_no_pdf}")
            logger.info(
                f"    - Already enriched: {len([p for p in self.skipped_papers if p['reason'] == 'Already enriched'])}"
            )

        # API usage statistics
        logger.info(f"\n📡 API USAGE:")
        logger.info(f"  Crossref successes: {self.crossref_success}")
        logger.info(f"  Semantic Scholar successes: {self.semantic_scholar_success}")
        logger.info(f"  LLM lay_summary generated: {self.llm_success}")
        logger.info(f"  Not found in any API: {self.not_found_count}")

        # Successful papers details
        if self.successful_papers:
            logger.info(f"\n✅ SUCCESSFUL PAPERS ({len(self.successful_papers)}):")
            for paper in self.successful_papers[:20]:  # Show first 20
                title = paper["title"][:50] if paper["title"] else "Untitled"
                fields = (
                    ", ".join(paper["fields_updated"])
                    if paper["fields_updated"]
                    else "none"
                )
                logger.info(f"  • Paper {paper['paper_id']}: '{title}'")
                logger.info(f"    DOI: {paper['doi']}")
                logger.info(f"    Fields updated: {fields}")
                if paper.get("sources"):
                    logger.info(f"    Sources: {', '.join(paper['sources'])}")
            if len(self.successful_papers) > 20:
                logger.info(
                    f"  ... and {len(self.successful_papers) - 20} more successful papers"
                )

        # Failed papers details
        if self.failed_papers:
            logger.info(f"\n❌ FAILED PAPERS ({len(self.failed_papers)}):")
            for paper in self.failed_papers[:20]:  # Show first 20
                title = paper["title"][:50] if paper["title"] else "Untitled"
                logger.info(f"  • Paper {paper['paper_id']}: '{title}'")
                logger.info(f"    DOI: {paper.get('doi', 'N/A')}")
                logger.info(f"    Error: {paper['error']}")
            if len(self.failed_papers) > 20:
                logger.info(
                    f"  ... and {len(self.failed_papers) - 20} more failed papers"
                )

        # Skipped papers details
        if self.skipped_papers:
            logger.info(f"\n⏭️  SKIPPED PAPERS ({len(self.skipped_papers)}):")
            for paper in self.skipped_papers[:10]:  # Show first 10
                title = paper["title"][:50] if paper["title"] else "Untitled"
                logger.info(f"  • Paper {paper['paper_id']}: '{title}'")
                logger.info(f"    Reason: {paper['reason']}")
            if len(self.skipped_papers) > 10:
                logger.info(
                    f"  ... and {len(self.skipped_papers) - 10} more skipped papers"
                )

        # Field update statistics
        if self.successful_papers:
            field_counts = {}
            for paper in self.successful_papers:
                for field in paper.get("fields_updated", []):
                    field_counts[field] = field_counts.get(field, 0) + 1

            if field_counts:
                logger.info(f"\n📝 FIELD UPDATE STATISTICS:")
                for field, count in sorted(
                    field_counts.items(), key=lambda x: x[1], reverse=True
                ):
                    logger.info(f"  • {field}: {count} papers")

        logger.info("\n" + "=" * 80)

        # Save detailed report to file
        self._save_detailed_report()

    def _save_detailed_report(self):
        """Save detailed report to a file for later review."""
        try:
            import json
            from pathlib import Path

            report_dir = Path(__file__).parent.parent / "logs"
            report_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = report_dir / f"backfill_report_{timestamp}.json"

            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "total_processed": self.processed_count,
                    "successful": len(self.successful_papers),
                    "failed": len(self.failed_papers),
                    "skipped": len(self.skipped_papers),
                    "crossref_success": self.crossref_success,
                    "semantic_scholar_success": self.semantic_scholar_success,
                    "llm_success": self.llm_success,
                    "not_found": self.not_found_count,
                },
                "successful_papers": self.successful_papers,
                "failed_papers": self.failed_papers,
                "skipped_papers": self.skipped_papers,
            }

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"\n📄 Detailed report saved to: {report_file}")
        except Exception as e:
            logger.warning(f"Failed to save detailed report: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Backfill missing metadata for scientific papers using DOI enrichment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check all papers and overwrite existing fields (recommended for fixing incorrect data)
  python scripts/backfill_metadata_from_doi.py
  
  # Dry run to see what would be changed
  python scripts/backfill_metadata_from_doi.py --dry-run
  
  # Process only first 50 papers
  python scripts/backfill_metadata_from_doi.py --limit 50
  
  # Only process incomplete papers (skip already-enriched)
  python scripts/backfill_metadata_from_doi.py --skip-enriched
  
  # Don't overwrite existing fields (only fill missing)
  python scripts/backfill_metadata_from_doi.py --no-overwrite
        """,
    )
    parser.add_argument("--limit", type=int, help="Maximum number of papers to process")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making any database changes (dry run mode)",
    )
    parser.add_argument(
        "--skip-enriched",
        action="store_true",
        help="Skip papers already enriched with DOI (default: process all)",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Don't overwrite existing fields, only fill missing ones (default: overwrite with better data)",
    )

    args = parser.parse_args()

    # Create async engine
    engine = create_async_engine(config.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Determine behavior: by default check all and overwrite (since most data is wrong)
    check_all = not args.skip_enriched  # Default True, unless --skip-enriched
    force_overwrite = not args.no_overwrite  # Default True, unless --no-overwrite

    # Run backfill pipeline
    pipeline = MetadataBackfillPipeline(
        async_session, dry_run=args.dry_run, force_overwrite=force_overwrite
    )

    try:
        await pipeline.enrich_all_papers(check_all=check_all, limit=args.limit)
    finally:
        await pipeline.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
