"""
Podcast Generation Service for converting scientific papers into podcast-style audio.

Uses OpenRouter LLM for script generation and TTS service for audio conversion.
Generates conversational scripts with 2 AI hosts (Alex & Jordan).
"""

import logging
import os
import uuid
from typing import Dict, List, Optional

import aiohttp
from app.db import Podcast, ScientificPaper
from app.services.tts_service import TTSService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class PodcastGenerationService:
    """Service for generating podcasts from scientific papers."""

    def __init__(
        self,
        session: AsyncSession,
        openrouter_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        elevenlabs_api_key: Optional[str] = None,
        tts_provider: str = "openai",
        model: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        """
        Initialize Podcast Generation Service.

        Args:
            session: Database session
            openrouter_api_key: User's OpenRouter API key (for LLM script generation)
            openai_api_key: OpenAI API key (for TTS, optional)
            elevenlabs_api_key: ElevenLabs API key (for TTS, optional)
            tts_provider: TTS provider ("openai", "elevenlabs", "kokoro")
            model: Model name (optional, uses config default if not provided)
            api_base: API base URL (optional, uses config default if not provided)
        """
        self.session = session
        self.openrouter_api_key = openrouter_api_key
        self.openai_api_key = openai_api_key
        self.elevenlabs_api_key = elevenlabs_api_key
        self.tts_provider = tts_provider

        # Configure LLM endpoint
        if openrouter_api_key:
            # Use OpenRouter API for user keys
            self.llm_base = api_base or "https://openrouter.ai/api/v1"
            self.api_key = openrouter_api_key

            # Get model from config if not provided
            if not model:
                model = os.getenv("STRATEGIC_LLM", "anthropic/claude-3.5-sonnet")

            # Ensure model uses openrouter/ prefix if not already
            if not model.startswith("openrouter/"):
                if "/" in model:
                    model = f"openrouter/{model}"
                else:
                    model = f"openrouter/anthropic/{model}"

            self.llm_model = model
            logger.info(
                f"Podcast Generation Service initialized with user's OpenRouter key (model: {self.llm_model})"
            )
        else:
            # Fallback to config instances (uses .env keys)
            self.llm_base = (
                api_base or os.getenv("FAST_LLM_API_BASE") or os.getenv("LLM_API_BASE")
            )
            self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            self.llm_model = model or os.getenv("FAST_LLM", "mistral-7b-v0.1")
            logger.info(
                f"Podcast Generation Service initialized with config defaults (model: {self.llm_model})"
            )

        # Validate that llm_base is configured
        if not self.llm_base:
            raise ValueError(
                "LLM endpoint (llm_base) is not configured. "
                "Please set one of: api_base parameter, FAST_LLM_API_BASE, or LLM_API_BASE environment variable."
            )

        self.http_session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=600)  # 10 min timeout

    def _get_headers(self) -> dict:
        """Get HTTP headers with API key if available."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            if self.openrouter_api_key:
                # OpenRouter also requires HTTP-Referer header
                headers["HTTP-Referer"] = "https://hero-evidence-library"
                headers["X-Title"] = "Hero Evidence Library Podcast Generator"
        return headers

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.http_session is None or self.http_session.closed:
            self.http_session = aiohttp.ClientSession(
                timeout=self.timeout, headers=self._get_headers()
            )
        return self.http_session

    async def close(self):
        """Close HTTP session."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    async def _call_llm(self, messages: list, max_tokens: int = 2000) -> Optional[str]:
        """Call OpenAI-compatible LLM API for script generation."""
        try:
            session = await self._get_session()
            headers = self._get_headers()
            async with session.post(
                f"{self.llm_base}/chat/completions",
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
                headers=headers,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    try:
                        content = result["choices"][0]["message"]["content"]
                        return content.strip()
                    except (KeyError, IndexError) as e:
                        logger.error(
                            f"LLM API response structure error: {str(e)}. Raw result: {result}"
                        )
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"LLM API error ({response.status}): {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Failed to call LLM: {str(e)}")
            return None

    async def _get_paper_content(self, paper_id: int) -> Optional[Dict]:
        """Get paper content and metadata for podcast generation."""
        try:
            stmt = (
                select(ScientificPaper)
                .where(ScientificPaper.id == paper_id)
                .options(selectinload(ScientificPaper.document))
            )
            result = await self.session.execute(stmt)
            paper = result.scalar_one_or_none()

            if not paper:
                logger.error(f"Paper {paper_id} not found")
                return None

            # Build paper content
            content_parts = []

            if paper.title:
                content_parts.append(f"Title: {paper.title}")

            if paper.authors:
                content_parts.append(f"Authors: {', '.join(paper.authors)}")

            if paper.journal:
                content_parts.append(f"Journal: {paper.journal}")

            if paper.publication_year:
                content_parts.append(f"Year: {paper.publication_year}")

            if paper.doi:
                content_parts.append(f"DOI: {paper.doi}")

            if paper.abstract:
                content_parts.append(f"\nAbstract:\n{paper.abstract}")

            # Include full text (truncated for context)
            document = getattr(paper, "document", None)
            if document is not None and hasattr(document, "content") and document.content:
                # Use first 8000 chars to leave room for script generation
                content_parts.append(f"\nFull Text:\n{document.content[:8000]}")

            return {
                "title": paper.title,
                "content": "\n\n".join(content_parts),
                "metadata": {
                    "authors": paper.authors or [],
                    "journal": paper.journal,
                    "year": paper.publication_year,
                    "doi": paper.doi,
                    "abstract": paper.abstract,
                },
            }
        except Exception as e:
            logger.error(f"Error getting paper content: {str(e)}")
            return None

    async def generate_script(self, paper_id: int) -> Optional[str]:
        """
        Generate conversational podcast script from paper.

        Creates a dialogue between two hosts: Alex (expert guide) and Jordan (analyst).

        Args:
            paper_id: ID of the paper to generate script for

        Returns:
            Generated script text, or None if generation failed
        """
        paper_data = await self._get_paper_content(paper_id)
        if not paper_data:
            return None

        system_prompt = """You are a podcast script writer. Create an engaging, conversational podcast script based on a scientific paper.

The script should feature two hosts:
- Alex: An expert guide who introduces topics and provides context
- Jordan: An analyst who asks critical questions and discusses implications

Format the script as:
ALEX: [dialogue]
JORDAN: [dialogue]
ALEX: [dialogue]
...and so on

The script should:
1. Be 450-750 words (roughly 3-5 minutes when read)
2. Start with an engaging introduction
3. Cover the main research question, methodology, and key findings
4. Include natural transitions between speakers
5. End with implications or takeaways
6. Be accessible but maintain scientific accuracy
7. Use natural, conversational language

Do not include stage directions, sound effects, or metadata. Only include the dialogue lines."""

        user_prompt = f"""Please create a podcast script based on this scientific paper:

{paper_data['content']}

Generate a conversational script between Alex and Jordan discussing this paper."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        script = await self._call_llm(messages, max_tokens=2000)
        return script

    async def generate_podcast(
        self, paper_id: int, search_space_id: int, title: Optional[str] = None
    ) -> Optional[Podcast]:
        """
        Generate a complete podcast from a paper.

        Args:
            paper_id: ID of the paper to generate podcast for
            search_space_id: Search space ID to associate the podcast with
            title: Optional custom title (uses paper title if not provided)

        Returns:
            Created Podcast object, or None if generation failed
        """
        try:
            # Get paper for title
            paper_data = await self._get_paper_content(paper_id)
            if not paper_data:
                logger.error(f"Failed to get paper data for paper {paper_id}")
                return None

            podcast_title = title or f"Podcast: {paper_data['title']}"

            # Step 1: Generate script
            logger.info(f"Generating podcast script for paper {paper_id}")
            script = await self.generate_script(paper_id)
            if not script:
                logger.error(f"Failed to generate script for paper {paper_id}")
                return None

            # Step 2: Convert script to audio using TTS
            logger.info(f"Converting script to audio for paper {paper_id}")
            tts_service = TTSService(
                provider=self.tts_provider,
                openai_api_key=self.openai_api_key,
                elevenlabs_api_key=self.elevenlabs_api_key,
            )

            try:
                output_filename = f"podcast_{paper_id}_{uuid.uuid4().hex[:8]}"
                audio_path, duration = await tts_service.generate(script, output_filename)
                await tts_service.close()

                # Step 3: Parse script into transcript format
                transcript = self._parse_script_to_transcript(script)

                # Step 4: Create Podcast record
                podcast = Podcast(
                    title=podcast_title,
                    podcast_transcript=transcript,
                    file_location=audio_path,
                    search_space_id=search_space_id,
                )

                self.session.add(podcast)
                await self.session.commit()
                await self.session.refresh(podcast)

                logger.info(
                    f"Successfully generated podcast {podcast.id} for paper {paper_id}"
                )
                return podcast

            except Exception as e:
                await tts_service.close()
                logger.error(f"TTS generation failed: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Failed to generate podcast: {str(e)}")
            await self.session.rollback()
            return None

    def _parse_script_to_transcript(self, script: str) -> List[Dict[str, str]]:
        """
        Parse conversational script into transcript format.

        Converts:
        ALEX: dialogue
        JORDAN: dialogue

        Into:
        [{"speaker_id": "ALEX", "dialog": "dialogue"}, ...]
        """
        transcript = []
        lines = script.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line starts with speaker name
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    speaker = parts[0].strip().upper()
                    dialog = parts[1].strip()

                    # Normalize speaker names
                    if speaker.startswith("ALEX"):
                        speaker = "ALEX"
                    elif speaker.startswith("JORDAN"):
                        speaker = "JORDAN"

                    if dialog:
                        transcript.append({"speaker_id": speaker, "dialog": dialog})
                else:
                    # No speaker, might be continuation of previous dialogue
                    if transcript:
                        transcript[-1]["dialog"] += " " + line
            else:
                # Continuation of previous dialogue
                if transcript:
                    transcript[-1]["dialog"] += " " + line

        return transcript
