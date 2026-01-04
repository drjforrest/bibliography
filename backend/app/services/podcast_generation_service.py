"""
Podcast Generation Service for HERO Evidence Library v2.0

Generates AI-powered podcast discussions from research papers.
Uses OpenRouter for LLM generation and TTSService for audio synthesis.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import Podcast, Paper, User
from app.services.tts_service import TTSService, TTSProvider


class PodcastGenerationService:
    """
    Service for generating podcast-style discussions from research papers.
    
    Workflow:
    1. Extract paper content (title, abstract, key findings)
    2. Generate podcast script using LLM (via OpenRouter)
    3. Convert script to audio using TTS
    4. Save metadata to database
    """
    
    def __init__(
        self,
        db: AsyncSession,
        openrouter_api_key: str,
        tts_service: TTSService
    ):
        self.db = db
        self.openrouter_api_key = openrouter_api_key
        self.tts = tts_service
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
    
    async def generate_podcast(
        self,
        paper_id: int,
        user_id: int,
        model: str = "anthropic/claude-sonnet-4-20250514",
        tts_provider: TTSProvider | str = "auto",
        voice: Optional[str] = None
    ) -> Podcast:
        """
        Generate a podcast from a research paper.
        
        Args:
            paper_id: ID of the paper to generate podcast from
            user_id: ID of the user requesting generation
            model: OpenRouter model to use for script generation
            tts_provider: TTS provider ("auto", "kokoro", "openai", "elevenlabs")
            voice: Voice ID (provider-specific)
            
        Returns:
            Podcast database object with metadata and file location
        """
        # Fetch paper
        paper = await self._get_paper(paper_id)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")
        
        # Fetch user for default model preference
        user = await self._get_user(user_id)
        if user and user.default_openrouter_model:
            model = user.default_openrouter_model
        
        # Generate podcast script using LLM
        script = await self._generate_script(paper, model)
        
        # Convert script to audio
        audio_path = await self.tts.generate_speech(
            text=script,
            provider=tts_provider,
            voice=voice,
            output_filename=f"podcast_{paper_id}_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        )
        
        # Calculate duration (estimate: ~150 words per minute, ~5 chars per word)
        estimated_duration = int((len(script) / 5) / 150 * 60)  # in seconds
        
        # Create podcast record in database
        podcast = Podcast(
            user_id=user_id,
            source_paper_ids=[paper_id],
            title=f"Discussion: {paper.title[:100]}",
            podcast_transcript=script,
            duration_seconds=estimated_duration,
            file_location=str(audio_path),
            generation_model=model,
            tts_provider=tts_provider if isinstance(tts_provider, str) else "auto",
            created_at=datetime.utcnow()
        )
        
        self.db.add(podcast)
        await self.db.commit()
        await self.db.refresh(podcast)
        
        return podcast
    
    async def generate_multi_paper_podcast(
        self,
        paper_ids: List[int],
        user_id: int,
        model: str = "anthropic/claude-sonnet-4-20250514",
        tts_provider: TTSProvider | str = "auto",
        voice: Optional[str] = None,
        focus: Optional[str] = None
    ) -> Podcast:
        """
        Generate a comparative podcast discussing multiple papers.
        
        Args:
            paper_ids: List of paper IDs to discuss
            user_id: ID of the user requesting generation
            model: OpenRouter model to use
            tts_provider: TTS provider
            voice: Voice ID
            focus: Optional focus area (e.g., "methodology", "findings", "implications")
            
        Returns:
            Podcast database object
        """
        # Fetch all papers
        papers = []
        for paper_id in paper_ids:
            paper = await self._get_paper(paper_id)
            if paper:
                papers.append(paper)
        
        if not papers:
            raise ValueError("No valid papers found")
        
        # Generate comparative script
        script = await self._generate_comparative_script(papers, model, focus)
        
        # Convert to audio
        audio_path = await self.tts.generate_speech(
            text=script,
            provider=tts_provider,
            voice=voice,
            output_filename=f"podcast_multi_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        )
        
        # Calculate duration
        estimated_duration = int((len(script) / 5) / 150 * 60)
        
        # Create podcast record
        podcast = Podcast(
            user_id=user_id,
            source_paper_ids=paper_ids,
            title=f"Comparative Discussion: {len(papers)} Papers",
            podcast_transcript=script,
            duration_seconds=estimated_duration,
            file_location=str(audio_path),
            generation_model=model,
            tts_provider=tts_provider if isinstance(tts_provider, str) else "auto",
            created_at=datetime.utcnow()
        )
        
        self.db.add(podcast)
        await self.db.commit()
        await self.db.refresh(podcast)
        
        return podcast
    
    async def _generate_script(self, paper: Paper, model: str) -> str:
        """
        Generate podcast script for a single paper using LLM.
        """
        # Build prompt for podcast generation
        prompt = self._build_single_paper_prompt(paper)
        
        # Call OpenRouter API
        script = await self._call_openrouter(prompt, model)
        
        return script
    
    async def _generate_comparative_script(
        self,
        papers: List[Paper],
        model: str,
        focus: Optional[str] = None
    ) -> str:
        """
        Generate comparative podcast script for multiple papers.
        """
        prompt = self._build_multi_paper_prompt(papers, focus)
        script = await self._call_openrouter(prompt, model)
        return script
    
    def _build_single_paper_prompt(self, paper: Paper) -> str:
        """
        Build prompt for single-paper podcast generation.
        """
        return f"""You are creating a podcast discussion about a research paper. Generate an engaging, conversational script between two AI hosts discussing this paper.

Paper Title: {paper.title}

Authors: {paper.authors if hasattr(paper, 'authors') else 'Not specified'}

Abstract: {paper.summary if paper.summary else 'Not available'}

Instructions:
- Create a natural conversation between two hosts (Alex and Jordan)
- Start with a friendly introduction
- Explain the paper's main contribution in accessible language
- Discuss methodology, findings, and implications
- Include thoughtful questions and back-and-forth dialogue
- End with key takeaways
- Target 3-5 minutes of audio (approximately 450-750 words)
- Use casual, engaging language while remaining accurate

Generate the podcast script now:"""
    
    def _build_multi_paper_prompt(
        self,
        papers: List[Paper],
        focus: Optional[str] = None
    ) -> str:
        """
        Build prompt for multi-paper comparative podcast.
        """
        papers_text = "\n\n".join([
            f"Paper {i+1}: {paper.title}\n"
            f"Summary: {paper.summary if paper.summary else 'Not available'}"
            for i, paper in enumerate(papers)
        ])
        
        focus_text = f"\nFocus area: {focus}" if focus else ""
        
        return f"""You are creating a comparative podcast discussing multiple research papers. Generate an engaging conversation between two AI hosts (Alex and Jordan) comparing and contrasting these papers.

{papers_text}{focus_text}

Instructions:
- Create natural dialogue between Alex and Jordan
- Compare methodologies, findings, and conclusions across papers
- Identify common themes and contradictions
- Discuss how the papers relate to each other
- Highlight the most significant insights from the collection
- Target 5-8 minutes of audio (approximately 750-1200 words)
- Use accessible language while maintaining accuracy

Generate the comparative podcast script now:"""
    
    async def _call_openrouter(self, prompt: str, model: str) -> str:
        """
        Call OpenRouter API to generate text.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://counterforce-hero.tech",  # Optional
                    "X-Title": "HERO Evidence Library"  # Optional
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                timeout=120.0
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def _get_paper(self, paper_id: int) -> Optional[Paper]:
        """Fetch paper from database."""
        result = await self.db.execute(
            select(Paper).where(Paper.id == paper_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_user(self, user_id: int) -> Optional[User]:
        """Fetch user from database."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
