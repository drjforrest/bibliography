"""
Infographic Generation Service for HERO Evidence Library v2.0

Generates visual infographics from research papers using Imagen via OpenRouter.
Adapted from SciGram's PDF infographic generation.
"""

import asyncio
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pathlib import Path
import base64
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import Infographic, Paper, User


InfographicStyle = Literal["minimal", "detailed", "modern", "classic"]
InfographicFocus = Literal["statistics", "messages", "recommendations", "all"]


class InfographicGenerationService:
    """
    Service for generating visual infographics from research papers.
    
    Uses Google Imagen via OpenRouter for image generation.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        openrouter_api_key: str,
        output_dir: Optional[Path] = None
    ):
        self.db = db
        self.openrouter_api_key = openrouter_api_key
        # Use project-relative generated directory
        if output_dir is None:
            base_dir = Path(__file__).parent.parent / "generated" / "infographics"
        else:
            base_dir = output_dir
        self.output_dir = base_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
    
    async def generate_infographic(
        self,
        paper_id: int,
        user_id: int,
        style: InfographicStyle = "modern",
        focus: InfographicFocus = "all",
        color_scheme: str = "professional",
        custom_description: Optional[str] = None
    ) -> Infographic:
        """
        Generate an infographic from a research paper.
        
        Args:
            paper_id: ID of the paper
            user_id: ID of the user
            style: Visual style (minimal, detailed, modern, classic)
            focus: Content focus (statistics, messages, recommendations, all)
            color_scheme: Color palette
            custom_description: Optional user description
            
        Returns:
            Infographic database object
        """
        # Fetch paper
        paper = await self._get_paper(paper_id)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")
        
        # Build prompt
        prompt = self._build_infographic_prompt(
            paper=paper,
            style=style,
            focus=focus,
            color_scheme=color_scheme,
            custom_description=custom_description
        )
        
        # Generate image with OpenRouter
        image_data = await self._generate_with_openrouter(prompt)
        
        # Save image file
        image_filename = f"infographic_{paper_id}_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        image_path = self.output_dir / image_filename
        image_path.write_bytes(image_data)
        
        # Create infographic record
        infographic = Infographic(
            user_id=user_id,
            source_paper_id=paper_id,
            title=f"Infographic: {paper.title[:80]}",
            image_url=str(image_path),
            style=style,
            focus_area=focus,
            generation_prompt=prompt,
            created_at=datetime.utcnow()
        )
        
        self.db.add(infographic)
        await self.db.commit()
        await self.db.refresh(infographic)
        
        return infographic
    
    def _build_infographic_prompt(
        self,
        paper: Paper,
        style: InfographicStyle,
        focus: InfographicFocus,
        color_scheme: str,
        custom_description: Optional[str] = None
    ) -> str:
        """
        Build a prompt for Gemini to generate an infographic.
        """
        # Sanitize custom description
        sanitized_desc = self._sanitize_description(custom_description) if custom_description else ""
        user_request = f"\n\nUser's specific request: {sanitized_desc}\n" if sanitized_desc else ""
        
        # Build content sections based on focus
        content_sections = []
        
        if focus in ["all", "messages"] and paper.summary:
            content_sections.append(f"Key Findings:\n{paper.summary}")
        
        if focus in ["all", "messages"] and paper.lay_summary:
            content_sections.append(f"Plain Language Summary:\n{paper.lay_summary}")
        
        if focus in ["all", "recommendations"] and paper.insights:
            insights_list = "\n".join([f"• {insight}" for insight in paper.insights[:5]])
            content_sections.append(f"Key Insights:\n{insights_list}")
        
        content_text = "\n\n".join(content_sections)
        
        prompt = f"""Create a full-page professional infographic summarizing this research paper:{user_request}

Paper Information:
- Title: {paper.title}
- Authors: {paper.authors if hasattr(paper, 'authors') else 'Not specified'}
- Year: {paper.year if hasattr(paper, 'year') else 'Not specified'}
- Type: {paper.literature_type if hasattr(paper, 'literature_type') else 'Research'}

{content_text}

Infographic Requirements:
- Full-page 16:9 widescreen layout (standard presentation format)
- {style} design style
- {color_scheme} color scheme
- Clear visual hierarchy with prominent title
- Professional typography (minimum 12pt body text, 24pt+ headers)
- Icons and visual elements to support key points
- Statistics highlighted prominently with charts or large numbers
- Balanced layout with effective use of white space
- Easy to scan and understand at a glance
- Publication-ready quality
- High contrast and legibility (WCAG AA compliant - 4.5:1 minimum contrast)
- Suitable for scientific/academic use
- Grid-based layout with consistent spacing

Create ONE comprehensive, visually appealing infographic that captures the essence of this research in a single 16:9 slide format. Use visual elements, icons, charts, and typography to make the information engaging and accessible."""

        return prompt
    
    def _sanitize_description(self, description: str) -> str:
        """
        Sanitize user description to prevent prompt injection.
        """
        if not description:
            return ""
        
        # Trim and limit length
        sanitized = description.strip()[:500]
        
        # Replace newlines
        sanitized = sanitized.replace("\n", " ").replace("\r", " ")
        
        # Remove injection patterns
        injection_patterns = [
            "ignore previous instructions",
            "ignore all instructions",
            "forget previous",
            "system:",
            "assistant:",
            "user:",
        ]
        
        for pattern in injection_patterns:
            sanitized = sanitized.replace(pattern, "")
            sanitized = sanitized.replace(pattern.upper(), "")
        
        # Collapse multiple spaces
        sanitized = " ".join(sanitized.split())
        
        return sanitized
    
    async def _generate_with_openrouter(self, prompt: str) -> bytes:
        """
        Call OpenRouter's chat completions API with Gemini image generation.
        
        For Gemini models (imagen-4.0-generate-001), OpenRouter uses the 
        chat completions endpoint with modalities: ["image", "text"].
        The model is actually gemini-2.5-flash-image-preview which generates images.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://counterforce-hero.tech",
                    "X-Title": "HERO Evidence Library"
                },
                json={
                    "model": "google/gemini-2.5-flash-image-preview",  # Gemini model that generates images
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "modalities": ["image", "text"],  # Critical: enables image generation
                    "image_config": {
                        "aspect_ratio": "16:9",  # Professional presentation format
                        "image_size": "2K"  # Higher quality (1K, 2K, or 4K)
                    }
                },
                timeout=120.0  # Image generation can take time
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract base64 image from response
            # Response format: choices[0].message.images[0].image_url.url
            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0].get("message", {})
                images = message.get("images", [])
                
                if images and len(images) > 0:
                    image_url = images[0].get("image_url", {}).get("url", "")
                    
                    # Remove data URL prefix if present
                    if image_url.startswith("data:image/png;base64,"):
                        image_base64 = image_url.replace("data:image/png;base64,", "")
                    else:
                        image_base64 = image_url
                    
                    image_data = base64.b64decode(image_base64)
                    return image_data
                else:
                    raise ValueError("No images in response from Gemini")
            else:
                raise ValueError("No choices in response from OpenRouter")
    
    async def _get_paper(self, paper_id: int) -> Optional[Paper]:
        """Fetch paper from database."""
        result = await self.db.execute(
            select(Paper).where(Paper.id == paper_id)
        )
        return result.scalar_one_or_none()
