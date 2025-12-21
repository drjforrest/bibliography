"""
LLM-based enrichment service for scientific papers.

Provides reusable methods for enriching papers with LLM-generated content:
- Lay summaries (accessible language for non-experts)
- Short descriptions (1-2 sentence overview)
- Key insights (main findings and implications)
- Citations (multiple formats: APA, MLA, Chicago, etc.)
"""

import asyncio
import logging
import os
from typing import Optional, Dict, List

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db import ScientificPaper
from app.services.citation_formatter import CitationFormatter

logger = logging.getLogger(__name__)


class LLMEnrichmentService:
    """Service for enriching papers with LLM-generated content."""

    def __init__(self, session: AsyncSession):
        self.session = session

        # Use LM Studio (OpenAI-compatible API)
        self.llm_base = os.getenv("FAST_LLM_API_BASE") or os.getenv("LLM_API_BASE", "http://localhost:1234/v1")
        self.llm_model = os.getenv("FAST_LLM", "gpt-3.5-turbo")
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5 min timeout

        logger.info(f"LLM Enrichment Service initialized: {self.llm_base} with model {self.llm_model}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.http_session is None or self.http_session.closed:
            self.http_session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
        return self.http_session

    async def _call_llm(
        self,
        messages: list,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Optional[str]:
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

    async def enrich_paper(self, paper_id: int) -> bool:
        """
        Enrich a single paper with LLM-generated content.

        Args:
            paper_id: ID of paper to enrich

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

            logger.info(f"Enriching paper {paper_id}: {paper.title[:60] if paper.title else 'Untitled'}...")

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

            # 3. Generate key insights
            if not metadata.get("insights"):
                logger.info(f"Generating insights for paper {paper_id}...")
                insights = await self._generate_insights(paper)
                if insights:
                    metadata["insights"] = insights
                    logger.info(f"Generated {len(insights)} insights")

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
            await self.session.commit()
            logger.info(f"Completed enrichment for paper {paper_id}")

            return True

        except Exception as e:
            logger.error(f"Error enriching paper {paper_id}: {str(e)}")
            await self.session.rollback()
            return False

    async def _generate_lay_summary(self, paper: ScientificPaper) -> Optional[str]:
        """Generate a lay summary using LM Studio."""
        try:
            # Prepare input text
            input_text = paper.title or "Untitled"
            if paper.abstract:
                input_text = f"{input_text}\n\n{paper.abstract}"
            elif paper.full_text:
                input_text = f"{input_text}\n\n{paper.full_text[:3000]}"

            messages = [
                {
                    "role": "system",
                    "content": "You are a science communicator who explains research in accessible language for non-experts."
                },
                {
                    "role": "user",
                    "content": f"Write a 2-3 paragraph lay summary of this research paper. Use accessible language that a general audience can understand. Avoid jargon.\n\n{input_text}"
                }
            ]

            result = await self._call_llm(messages, max_tokens=500, temperature=0.7)
            return result

        except Exception as e:
            logger.error(f"Error generating lay summary: {str(e)}")
            return None

    async def _generate_short_description(self, paper: ScientificPaper) -> Optional[str]:
        """Generate a 1-2 sentence description."""
        try:
            # Prepare input text
            input_text = paper.title or "Untitled"
            if paper.abstract:
                input_text = f"{input_text}\n\n{paper.abstract}"
            elif paper.full_text:
                input_text = f"{input_text}\n\n{paper.full_text[:2000]}"

            messages = [
                {
                    "role": "system",
                    "content": "You are a technical writer who creates concise summaries of research papers."
                },
                {
                    "role": "user",
                    "content": f"Summarize this in one sentence:\n\n{input_text}"
                }
            ]

            result = await self._call_llm(messages, max_tokens=200, temperature=0.5)
            return result

        except Exception as e:
            logger.error(f"Error generating short description: {str(e)}")
            return None

    async def _generate_insights(self, paper: ScientificPaper) -> Optional[List[str]]:
        """Generate key insights (3-5 main findings)."""
        try:
            # Prepare input text
            input_text = paper.title or "Untitled"
            if paper.abstract:
                input_text = f"{input_text}\n\n{paper.abstract}"
            elif paper.full_text:
                input_text = f"{input_text}\n\n{paper.full_text[:3000]}"

            messages = [
                {
                    "role": "system",
                    "content": "You are a research analyst who extracts key insights from papers."
                },
                {
                    "role": "user",
                    "content": f"List 3-5 key insights from this paper. Return ONLY a valid JSON array of strings, like [\"insight 1\", \"insight 2\", ...].\n\n{input_text}"
                }
            ]

            result = await self._call_llm(messages, max_tokens=1200, temperature=0.7)

            if result:
                # Try to parse as JSON
                import json
                try:
                    # Clean up the response - remove markdown code blocks if present
                    cleaned = result.strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    if cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    cleaned = cleaned.strip()

                    insights = json.loads(cleaned)
                    if isinstance(insights, list):
                        return insights
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse insights as JSON: {result[:100]}")
                    # Fall back to splitting by newlines
                    lines = [line.strip() for line in result.split('\n') if line.strip()]
                    # Remove numbering like "1.", "2." etc.
                    cleaned_lines = []
                    for line in lines:
                        # Remove leading numbers and punctuation
                        import re
                        cleaned = re.sub(r'^\d+\.\s*', '', line)
                        cleaned = re.sub(r'^[-*•]\s*', '', cleaned)
                        if cleaned:
                            cleaned_lines.append(cleaned)
                    return cleaned_lines[:5] if cleaned_lines else None

            return None

        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return None

    def _generate_citations(self, paper: ScientificPaper) -> Optional[Dict[str, str]]:
        """Generate citations in multiple formats."""
        try:
            formatter = CitationFormatter()

            citations = {}

            # Generate each format
            for format_name in ['apa', 'mla', 'chicago', 'ieee', 'harvard', 'bibtex']:
                try:
                    citation = formatter.format(paper, format_name)
                    if citation:
                        citations[format_name] = citation
                except Exception as e:
                    logger.warning(f"Failed to generate {format_name} citation: {str(e)}")

            return citations if citations else None

        except Exception as e:
            logger.error(f"Error generating citations: {str(e)}")
            return None

    async def close(self):
        """Clean up resources."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
