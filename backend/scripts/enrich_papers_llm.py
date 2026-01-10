#!/usr/bin/env python3
"""
LLM-based enrichment pipeline for scientific papers.

Generates:
1. Lay summaries (accessible language for non-experts)
2. Short descriptions (1-2 sentence overview)
3. Key insights (main findings and implications)
4. Citations (multiple formats: APA, MLA, Chicago, etc.)

Usage:
    python scripts/enrich_papers_llm.py [--limit N] [--skip-existing] [--batch-size N]
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from app.db import ScientificPaper
from app.services.citation_formatter import CitationFormatter
from app.config import config
import os
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LLMEnrichmentPipeline:
    """LLM-based enrichment pipeline for scientific papers."""

    def __init__(self, session_maker, batch_size: int = 5):
        self.session_maker = session_maker
        self.batch_size = batch_size

        # Use LM Studio (OpenAI-compatible API)
        self.llm_base = os.getenv("FAST_LLM_API_BASE") or os.getenv("LLM_API_BASE", "http://192.168.1.88:1234/v1")
        # Default to mistral-7b-v0.1 if FAST_LLM not set
        # Set FAST_LLM in .env to match your LMStudio model name
        self.llm_model = os.getenv("FAST_LLM", "mistral-7b-v0.1")
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5 min timeout

        logger.info(f"Using LLM at {self.llm_base} with model {self.llm_model}")

        # Stats
        self.processed_count = 0
        self.enriched_count = 0
        self.error_count = 0
        self.skipped_count = 0
        self.errors = []

    async def enrich_all_papers(
        self,
        limit: Optional[int] = None,
        skip_existing: bool = False
    ):
        """
        Enrich all papers with LLM-generated content.

        Args:
            limit: Maximum number of papers to process
            skip_existing: Skip papers that already have lay_summary
        """
        logger.info("Starting LLM enrichment pipeline...")

        async with self.session_maker() as session:
            # Get papers that need enrichment
            query = select(ScientificPaper)

            if skip_existing:
                # Skip papers that already have lay summary
                query = query.where(
                    (ScientificPaper.lay_summary == None) |
                    (ScientificPaper.lay_summary == "")
                )

            # Only enrich papers that have abstract or full_text
            query = query.where(
                (ScientificPaper.abstract != None) |
                (ScientificPaper.full_text != None)
            )

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            papers = result.scalars().all()

            total_papers = len(papers)
            logger.info(f"Found {total_papers} papers to enrich with LLM")

            if total_papers == 0:
                logger.info("No papers to enrich")
                return

        # Process papers in batches (smaller batches for LLM to avoid timeouts)
        for i in range(0, total_papers, self.batch_size):
            batch = papers[i:i + self.batch_size]
            logger.info(
                f"Processing batch {i // self.batch_size + 1}/"
                f"{(total_papers + self.batch_size - 1) // self.batch_size}"
            )

            for paper in batch:
                # Each paper gets its own session
                async with self.session_maker() as session:
                    try:
                        await self._enrich_paper(session, paper.id)
                        self.enriched_count += 1
                    except Exception as e:
                        self.error_count += 1
                        error_msg = f"Error enriching paper {paper.id}: {str(e)}"
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

        # Close the HTTP session
        if self.session:
            await self.session.close()

        # Final summary
        self.print_summary()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
        return self.session

    async def _call_llm(self, messages: list, max_tokens: int = 500, temperature: float = 0.7) -> Optional[str]:
        """Call OpenAI-compatible LLM API."""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.llm_base}/chat/completions",
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    error_text = await response.text()
                    logger.warning(f"LLM API error ({response.status}): {error_text}")
                    return None
        except Exception as e:
            logger.warning(f"Failed to call LLM: {str(e)}")
            return None

    async def _enrich_paper(self, session: AsyncSession, paper_id: int):
        """
        Enrich a single paper with LLM-generated content.

        Args:
            session: Database session
            paper_id: ID of paper to enrich
        """
        # Get paper
        stmt = select(ScientificPaper).where(ScientificPaper.id == paper_id)
        result = await session.execute(stmt)
        paper = result.scalar_one()

        logger.debug(f"Enriching paper {paper_id}: {paper.title[:60]}...")

        # Initialize or get existing extraction_metadata
        metadata = paper.extraction_metadata or {}

        # 1. Generate lay summary (if not exists)
        if not paper.lay_summary or len(paper.lay_summary.strip()) == 0:
            lay_summary = await self._generate_lay_summary(paper)
            if lay_summary:
                paper.lay_summary = lay_summary
                logger.debug(f"Generated lay summary ({len(lay_summary)} chars)")

        # 2. Generate short description (1-2 sentences)
        if not metadata.get("short_description"):
            logger.info(f"Generating short description for paper {paper_id}...")
            short_desc = await self._generate_short_description(paper)
            if short_desc:
                metadata["short_description"] = short_desc
                logger.info(f"Generated short description: {short_desc[:80]}...")
            else:
                logger.warning(f"Short description generation returned None for paper {paper_id}")

        # 3. Generate key insights
        if not metadata.get("insights"):
            logger.info(f"Generating insights for paper {paper_id}...")
            insights = await self._generate_insights(paper)
            if insights:
                metadata["insights"] = insights
                logger.info(f"Generated {len(insights)} insights")
            else:
                logger.warning(f"Insights generation returned None for paper {paper_id}")

        # 4. Generate citations in multiple formats
        if not metadata.get("citations"):
            citations = self._generate_citations(paper)
            if citations:
                metadata["citations"] = citations
                logger.debug(f"Generated {len(citations)} citation formats")

        # Update extraction_metadata
        paper.extraction_metadata = metadata
        flag_modified(paper, "extraction_metadata")

        # Commit changes
        await session.commit()
        logger.debug(f"Completed enrichment for paper {paper_id}")

    async def _generate_lay_summary(self, paper: ScientificPaper) -> Optional[str]:
        """Generate a lay summary using LM Studio."""
        try:
            # Prepare input text
            input_text = paper.title
            if paper.abstract:
                input_text = f"{paper.title}\n\n{paper.abstract}"
            elif paper.full_text:
                input_text = f"{paper.title}\n\n{paper.full_text[:3000]}"

            messages = [
                {
                    "role": "system",
                    "content": "You are a science communicator who explains complex research in simple, accessible language for general audiences."
                },
                {
                    "role": "user",
                    "content": f"""Write a clear, engaging summary of this research paper in about 200-250 words for a general audience. Use simple language and avoid jargon. Focus on:
1. What the research is about
2. Why it matters
3. The main findings

Paper:
{input_text}

Summary:"""
                }
            ]

            summary = await self._call_llm(messages, max_tokens=500, temperature=0.7)
            return summary if summary and len(summary) > 50 else None

        except Exception as e:
            logger.warning(f"Failed to generate lay summary: {str(e)}")
            return None

    async def _generate_short_description(self, paper: ScientificPaper) -> Optional[str]:
        """Generate a 1-2 sentence description using LM Studio."""
        try:
            # Use lay_summary if available (generated first), otherwise fall back to abstract/full_text
            if paper.lay_summary and len(paper.lay_summary) > 50:
                input_text = paper.lay_summary
            elif paper.abstract:
                input_text = paper.abstract[:1000]
            elif paper.full_text:
                input_text = paper.full_text[:1000]
            else:
                input_text = paper.title

            messages = [
                {
                    "role": "user",
                    "content": f"Summarize this in one sentence: {input_text}"
                }
            ]

            description = await self._call_llm(messages, max_tokens=200, temperature=0.7)
            logger.info(f"Short desc LLM response: [{description}] ({len(description) if description else 0} chars)")
            if description:
                # Clean up the response
                description = description.replace("\n", " ").strip()
                if len(description) > 10:
                    return description
                else:
                    logger.warning(f"Short description too short: {len(description)} chars")
                    return None

            return None

        except Exception as e:
            logger.warning(f"Failed to generate short description: {str(e)}")
            return None

    async def _generate_insights(self, paper: ScientificPaper) -> Optional[list]:
        """Generate key insights using LM Studio."""
        try:
            # Prepare input
            input_text = paper.title
            if paper.abstract:
                input_text = f"{paper.title}\n\n{paper.abstract}"
            elif paper.full_text:
                # Use first 2000 chars of full text
                input_text = f"{paper.title}\n\n{paper.full_text[:2000]}"

            messages = [
                {
                    "role": "user",
                    "content": f"""Extract 3-5 key insights from this research. Return as a JSON array of strings:

{input_text}

Format: ["Insight 1", "Insight 2", "Insight 3"]"""
                }
            ]

            insights_text = await self._call_llm(messages, max_tokens=1200, temperature=0.7)
            logger.info(f"Insights LLM response: [{insights_text[:200] if insights_text else None}...] ({len(insights_text) if insights_text else 0} chars)")
            if insights_text:
                # Try to parse as JSON
                try:
                    # Extract JSON array from response (may have extra text)
                    import re
                    json_match = re.search(r'\[.*\]', insights_text, re.DOTALL)
                    if json_match:
                        insights = json.loads(json_match.group(0))
                        if isinstance(insights, list) and len(insights) > 0:
                            return insights
                        else:
                            logger.warning(f"Insights parsed but invalid: {insights}")
                    else:
                        logger.warning("No JSON array found in insights response")
                except Exception as parse_error:
                    logger.warning(f"Failed to parse insights JSON: {str(parse_error)}")

            return None

        except Exception as e:
            logger.warning(f"Failed to generate insights: {str(e)}")
            return None

    def _generate_citations(self, paper: ScientificPaper) -> Optional[Dict[str, str]]:
        """Generate citations in multiple formats."""
        try:
            citations = {}

            # Generate all major citation styles
            styles = ["apa", "mla", "chicago", "ieee", "harvard"]

            for style in styles:
                try:
                    citation = CitationFormatter.format_citation(paper, style)
                    if citation:
                        citations[style] = citation
                except Exception as e:
                    logger.debug(f"Failed to generate {style} citation: {str(e)}")
                    continue

            return citations if len(citations) > 0 else None

        except Exception as e:
            logger.warning(f"Failed to generate citations: {str(e)}")
            return None

    def print_summary(self):
        """Print enrichment summary."""
        logger.info("\n" + "=" * 60)
        logger.info("LLM ENRICHMENT PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total processed: {self.processed_count}")
        logger.info(f"Successfully enriched: {self.enriched_count}")
        logger.info(f"Errors: {self.error_count}")

        if self.errors:
            logger.info("\nErrors encountered:")
            for error in self.errors[:10]:  # Show first 10 errors
                logger.info(f"  - {error}")
            if len(self.errors) > 10:
                logger.info(f"  ... and {len(self.errors) - 10} more errors")

        logger.info("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Enrich papers with LLM-generated content")
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of papers to process"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip papers that already have lay_summary"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of papers to process in batch (default: 5)"
    )

    args = parser.parse_args()

    # Create async engine
    engine = create_async_engine(config.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Run enrichment pipeline
    pipeline = LLMEnrichmentPipeline(async_session, batch_size=args.batch_size)

    try:
        await pipeline.enrich_all_papers(
            limit=args.limit,
            skip_existing=args.skip_existing
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
