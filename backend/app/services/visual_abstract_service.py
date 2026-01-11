"""
Visual Abstract Generation Service

Generates visual abstracts for scientific papers using OpenAI DALL-E or OpenRouter.
Stores generated images with 30-day expiration.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import aiohttp
from app.config import config
from app.db import ScientificPaper, VisualAbstract
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class VisualAbstractService:
    """Service for generating visual abstracts from scientific papers."""

    def __init__(
        self,
        session: AsyncSession,
        openai_api_key: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
    ):
        """
        Initialize Visual Abstract Service.

        Args:
            session: Database session
            openai_api_key: OpenAI API key (if user has configured)
            openrouter_api_key: OpenRouter API key (fallback)
        """
        self.session = session
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openrouter_api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")

        # Determine which service to use
        # Prefer OpenAI if user has configured it (likely cheaper)
        self.use_openai = bool(self.openai_api_key)
        self.use_openrouter = bool(self.openrouter_api_key) and not self.use_openai

        # Allow initialization without keys for cleanup operations
        # Only require keys when actually generating images
        self._has_api_keys = self.use_openai or self.use_openrouter

        # Storage for visual abstracts (30-day expiration)
        self.storage_root = Path(
            getattr(config, "VISUAL_ABSTRACT_STORAGE_ROOT", "./data/visual_abstracts")
        )
        self.storage_root.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Visual Abstract Service initialized - Using: "
            f"{'OpenAI' if self.use_openai else 'OpenRouter' if self.use_openrouter else 'No API configured'}"
        )

    def _get_storage_path(self, paper_id: int) -> Path:
        """Get storage path for a paper's visual abstract."""
        now = datetime.now()
        year_dir = self.storage_root / str(now.year)
        month_dir = year_dir / f"{now.month:02d}"
        month_dir.mkdir(parents=True, exist_ok=True)
        return month_dir / f"paper_{paper_id}.png"

    async def _generate_with_openai(self, prompt: str) -> bytes:
        """Generate image using OpenAI DALL-E."""
        timeout = aiohttp.ClientTimeout(total=120)  # 2 minutes for image generation
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            }

            # Use DALL-E 3 for better quality
            payload = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",  # Standard size for visual abstracts
                "quality": "standard",
            }

            async with session.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"OpenAI API error ({response.status}): {error_text}"
                    )

                result = await response.json()
                image_url = result["data"][0]["url"]

                # Download the image
                async with session.get(image_url) as img_response:
                    if img_response.status != 200:
                        raise Exception(
                            f"Failed to download image: {img_response.status}"
                        )
                    return await img_response.read()

    async def _generate_with_openrouter(self, prompt: str) -> bytes:
        """Generate image using OpenRouter (GPT-4 Vision or similar)."""
        # Note: OpenRouter doesn't directly support image generation
        # We'll use it to generate a detailed prompt, then use OpenAI if available
        # For now, if OpenRouter is selected but OpenAI key exists, use OpenAI
        if self.openai_api_key:
            return await self._generate_with_openai(prompt)

        # If no OpenAI key, we need to use OpenRouter's image generation models
        # OpenRouter supports DALL-E via openai/dall-e-3
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "HTTP-Referer": "https://counterforce-hero.tech",
                "X-Title": "Hero Evidence Library",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "openai/dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
            }

            async with session.post(
                "https://openrouter.ai/api/v1/images/generations",
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"OpenRouter API error ({response.status}): {error_text}"
                    )

                result = await response.json()
                image_url = result["data"][0]["url"]

                # Download the image
                async with session.get(image_url) as img_response:
                    if img_response.status != 200:
                        raise Exception(
                            f"Failed to download image: {img_response.status}"
                        )
                    return await img_response.read()

    def _create_prompt(self, paper: ScientificPaper) -> str:
        """
        Create a detailed prompt for visual abstract generation based on research guidelines.

        Uses the research document on effective visual abstracts to create a comprehensive prompt.
        """
        # Extract key information from paper
        title = paper.title or "Research Paper"
        abstract = paper.abstract or ""
        authors = ", ".join(paper.authors[:3]) if paper.authors else "Researchers"
        journal = paper.journal or ""
        year = paper.publication_year or ""

        # Build comprehensive prompt based on visual abstract best practices
        prompt = f"""Create a scientific visual abstract for this research paper:

TITLE: {title}

AUTHORS: {authors}
JOURNAL: {journal} ({year})

ABSTRACT:
{abstract[:1000]}

REQUIREMENTS FOR THE VISUAL ABSTRACT:
1. Design a single, self-contained visual summary that communicates the key research findings
2. Use a clear visual hierarchy with top-to-bottom or left-to-right reading flow
3. Include these essential components:
   - Background/Context: Visual representation of the research question or problem
   - Methodology: Simple diagram or icons showing the study design
   - Results: Key findings visualized through charts, graphs, or infographics
   - Conclusion: Clear takeaway message highlighted
4. Use a restricted palette of 3-5 complementary colors
5. Use sans-serif fonts (Arial, Helvetica style) with text sizes 12-16 points minimum
6. Keep text minimal - rely on visuals to carry the narrative
7. Use simple, clear icons, diagrams, or data visualizations
8. Ensure scientific accuracy in all visual elements
9. Make it suitable for social media sharing (clear at thumbnail size)
10. Dimensions: 1328x531 pixels (landscape) or 531x1328 pixels (portrait)

Create a professional, engaging visual abstract that would increase engagement and comprehension of this research."""

        return prompt

    async def generate_visual_abstract(
        self, paper_id: int, regenerate: bool = False
    ) -> VisualAbstract:
        """
        Generate a visual abstract for a paper.

        Args:
            paper_id: ID of the paper
            regenerate: If True, regenerate even if one exists

        Returns:
            VisualAbstract object
        """
        # Check if visual abstract already exists
        if not regenerate:
            stmt = select(VisualAbstract).where(
                VisualAbstract.paper_id == paper_id,
                VisualAbstract.expires_at > datetime.now(timezone.utc),
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                logger.info(f"Visual abstract already exists for paper {paper_id}")
                return existing

        # Get paper
        stmt = select(ScientificPaper).where(ScientificPaper.id == paper_id)
        result = await self.session.execute(stmt)
        paper = result.scalar_one_or_none()

        if not paper:
            raise ValueError(f"Paper {paper_id} not found")

        logger.info(
            f"Generating visual abstract for paper {paper_id}: {(paper.title or 'Untitled')[:60]}"
        )

        # Check if API keys are available
        if not self._has_api_keys:
            raise ValueError(
                "Either OpenAI API key or OpenRouter API key must be configured for image generation"
            )

        # Create prompt
        prompt = self._create_prompt(paper)

        # Generate image
        try:
            if self.use_openai:
                image_data = await self._generate_with_openai(prompt)
                model_used = "dall-e-3"
            else:
                image_data = await self._generate_with_openrouter(prompt)
                model_used = "openrouter/openai/dall-e-3"
        except Exception as e:
            logger.error(f"Failed to generate image: {str(e)}")
            raise

        # Save image to storage
        storage_path = self._get_storage_path(paper_id)
        storage_path.write_bytes(image_data)

        # Calculate expiration (30 days from now)
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        # Delete old visual abstract if regenerating
        if regenerate:
            old_stmt = select(VisualAbstract).where(VisualAbstract.paper_id == paper_id)
            old_result = await self.session.execute(old_stmt)
            old_abstracts = old_result.scalars().all()
            for old_abstract in old_abstracts:
                # Delete old file
                old_path = Path(old_abstract.file_path)
                if old_path.exists():
                    old_path.unlink()
                await self.session.delete(old_abstract)

        # Create database record
        visual_abstract = VisualAbstract(
            paper_id=paper_id,
            file_path=str(storage_path),
            prompt_used=prompt,
            model_used=model_used,
            expires_at=expires_at,
        )

        self.session.add(visual_abstract)
        await self.session.commit()
        await self.session.refresh(visual_abstract)

        logger.info(
            f"Successfully generated visual abstract for paper {paper_id} "
            f"(expires: {expires_at.date()})"
        )

        return visual_abstract

    async def get_visual_abstract(self, paper_id: int) -> Optional[VisualAbstract]:
        """Get the current visual abstract for a paper (if not expired)."""
        stmt = (
            select(VisualAbstract)
            .where(
                VisualAbstract.paper_id == paper_id,
                VisualAbstract.expires_at > datetime.now(timezone.utc),
            )
            .order_by(VisualAbstract.created_at.desc())
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def cleanup_expired(self) -> int:
        """
        Clean up expired visual abstracts (older than 30 days).

        Returns:
            Number of abstracts deleted
        """
        now = datetime.now(timezone.utc)
        stmt = select(VisualAbstract).where(VisualAbstract.expires_at <= now)
        result = await self.session.execute(stmt)
        expired = result.scalars().all()

        deleted_count = 0
        for abstract in expired:
            # Delete file
            file_path = Path(abstract.file_path)
            if file_path.exists():
                file_path.unlink()

            # Delete database record
            await self.session.delete(abstract)
            deleted_count += 1

        if deleted_count > 0:
            await self.session.commit()
            logger.info(f"Cleaned up {deleted_count} expired visual abstracts")

        return deleted_count
