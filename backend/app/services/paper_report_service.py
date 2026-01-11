"""
Paper Report Service for generating AI-powered analysis reports.

Generates various report types based on best practices for scientific paper analysis.
Uses user's OpenRouter API key when available, falls back to config.
"""

import logging
import os
from typing import Dict, List, Optional

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import ScientificPaper

logger = logging.getLogger(__name__)


class PaperReportService:
    """Service for generating AI-powered analysis reports on scientific papers."""

    def __init__(
        self, 
        session: AsyncSession, 
        openrouter_api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        """
        Initialize Paper Report Service.
        
        Args:
            session: Database session
            openrouter_api_key: User's OpenRouter API key (optional, for BYOK)
            model: Model name (optional, uses config default if not provided)
            api_base: API base URL (optional, uses config default if not provided)
        """
        self.session = session
        self.openrouter_api_key = openrouter_api_key
        
        # Configure LLM endpoint
        if openrouter_api_key:
            # Use OpenRouter API for user keys
            self.llm_base = api_base or "https://openrouter.ai/api/v1"
            self.api_key = openrouter_api_key
            
            # Get model from config if not provided
            if not model:
                model = os.getenv("STRATEGIC_LLM", "openrouter/openai/gpt-4")
            
            # Ensure model uses openrouter/ prefix if not already
            if not model.startswith("openrouter/"):
                if "/" in model:
                    model = f"openrouter/{model}"
                else:
                    model = f"openrouter/openai/{model}"
            
            self.llm_model = model
            logger.info(f"Paper Report Service initialized with user's OpenRouter key (model: {self.llm_model})")
        else:
            # Fallback to config instances (uses .env keys)
            self.llm_base = api_base or os.getenv("FAST_LLM_API_BASE") or os.getenv(
                "LLM_API_BASE", "http://192.168.1.88:1234/v1"
            )
            self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            self.llm_model = model or os.getenv("FAST_LLM", "mistral-7b-v0.1")
            logger.info(f"Paper Report Service initialized with config defaults (model: {self.llm_model})")
        
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=600)  # 10 min timeout for reports

    def _get_headers(self) -> dict:
        """Get HTTP headers with API key if available."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            # Use Authorization header for OpenAI-compatible APIs
            if self.openrouter_api_key:
                # OpenRouter uses "Authorization: Bearer" format
                headers["Authorization"] = f"Bearer {self.api_key}"
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.http_session is None or self.http_session.closed:
            self.http_session = aiohttp.ClientSession(
                timeout=self.timeout, headers=self._get_headers()
            )
        return self.http_session

    async def _call_llm(
        self, messages: list, max_tokens: int = 2000, temperature: float = 0.7
    ) -> Optional[str]:
        """Call OpenAI-compatible LLM API."""
        try:
            session = await self._get_session()
            headers = self._get_headers()
            async with session.post(
                f"{self.llm_base}/chat/completions",
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                headers=headers,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    error_text = await response.text()
                    logger.error(f"LLM API error ({response.status}): {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Failed to call LLM: {str(e)}")
            return None

    async def _get_paper_content(self, paper_id: int) -> Optional[Dict]:
        """Get paper content and metadata for report generation."""
        try:
            stmt = select(ScientificPaper).where(ScientificPaper.id == paper_id)
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
            
            if paper.document and paper.document.content:
                # Include full text (may be truncated by LLM context window)
                content_parts.append(f"\nFull Text:\n{paper.document.content[:10000]}")  # First 10k chars
            
            return {
                "title": paper.title,
                "content": "\n\n".join(content_parts),
                "metadata": {
                    "authors": paper.authors or [],
                    "journal": paper.journal,
                    "year": paper.publication_year,
                    "doi": paper.doi,
                    "abstract": paper.abstract,
                }
            }
        except Exception as e:
            logger.error(f"Error getting paper content: {str(e)}")
            return None

    async def generate_quick_summary(self, paper_id: int) -> Optional[str]:
        """
        Generate a quick 150-word summary (Prompt #2).
        
        Captures:
        - Central research question
        - Methodology type
        - Main finding(s) with effect size if applicable
        - One key limitation
        - Why this matters
        """
        paper_data = await self._get_paper_content(paper_id)
        if not paper_data:
            return None

        prompt = f"""Provide a concise 150-word overview of this research paper:

{paper_data['content']}

Capture:
- Central research question
- Methodology type (e.g., RCT, qualitative, systematic review)
- Main finding(s) with effect size if applicable
- One key limitation
- Why this matters to the research domain

Format as a clear, readable summary suitable for quick understanding."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert research analyst specializing in summarizing scientific papers clearly and concisely."
            },
            {"role": "user", "content": prompt}
        ]

        return await self._call_llm(messages, max_tokens=300, temperature=0.5)

    async def generate_comprehensive_analysis(self, paper_id: int) -> Optional[str]:
        """
        Generate comprehensive analysis (Prompt #1).
        
        Analyzes:
        - Research Question & Objectives
        - Methodology & Data
        - Key Findings
        - Theoretical Framework
        - Limitations & Validity
        - Scholarly Context
        - Practical & Theoretical Implications
        """
        paper_data = await self._get_paper_content(paper_id)
        if not paper_data:
            return None

        prompt = f"""Analyze this research paper systematically:

{paper_data['content']}

Provide a comprehensive analysis covering:
- Research Question & Objectives: What is the study's central aim?
- Methodology & Data: What research design, sample size, and data sources were used?
- Key Findings: What are the most important results and their effect sizes/confidence intervals?
- Theoretical Framework: What theories or models underpin this work?
- Limitations & Validity: What methodological constraints or potential biases exist?
- Scholarly Context: How does this paper build upon, contradict, or extend prior research?
- Practical & Theoretical Implications: What are the real-world or policy applications?

Format as a structured, professional analysis."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert research analyst specializing in comprehensive critical analysis of scientific papers."
            },
            {"role": "user", "content": prompt}
        ]

        return await self._call_llm(messages, max_tokens=3000, temperature=0.7)

    async def generate_critical_appraisal(self, paper_id: int) -> Optional[str]:
        """
        Generate critical appraisal via IMRaD structure (Prompt #4).
        
        Reviews:
        - INTRODUCTION: Research gaps, relevance
        - METHODS: Reproducibility, ethics
        - RESULTS: Presentation, tables/figures
        - DISCUSSION: Interpretation, limitations, speculation
        - Overall Assessment: Strengths and weaknesses
        """
        paper_data = await self._get_paper_content(paper_id)
        if not paper_data:
            return None

        prompt = f"""Review this paper using IMRaD framework:

{paper_data['content']}

Provide critical appraisal covering:
INTRODUCTION: Are the research gaps clearly identified? Is the relevance established?
METHODS: Are methods adequately described for reproducibility? Are ethical considerations addressed?
RESULTS: Are results clearly presented? Do tables/figures match text descriptions?
DISCUSSION: Are interpretations supported by findings? Are limitations discussed? Is speculation identified?
Overall Assessment: [Score 1-5] What are the key strengths and weaknesses?

Format as a structured critical appraisal."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert research critic specializing in methodological quality assessment and critical appraisal of scientific papers."
            },
            {"role": "user", "content": prompt}
        ]

        return await self._call_llm(messages, max_tokens=2500, temperature=0.6)

    async def generate_methodology_assessment(self, paper_id: int) -> Optional[str]:
        """
        Generate methodology and risk of bias assessment (Prompt #3).
        
        Evaluates:
        - Study Design Appropriateness
        - Sample Adequacy
        - Data Collection Quality
        - Analysis Rigor
        - Potential Biases
        - Internal & External Validity
        - Quality Rating
        """
        paper_data = await self._get_paper_content(paper_id)
        if not paper_data:
            return None

        prompt = f"""Evaluate the methodological quality of this paper:

{paper_data['content']}

Assess:
- Study Design Appropriateness: Is the design well-suited to the research question?
- Sample Adequacy: Is the sample size, selection, and composition appropriate?
- Data Collection Quality: Were measurements valid and reliable?
- Analysis Rigor: Were statistical/qualitative analysis methods appropriate?
- Potential Biases: What sources of bias might affect findings (selection, measurement, reporting)?
- Internal Validity: Can we trust these results given the study design?
- External Validity: How generalizable are these findings beyond the study population?
- Quality Rating: [Strong/Moderate/Weak] with justification

Format as a structured methodology assessment."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert in research methodology and study design, specializing in quality assessment and bias detection."
            },
            {"role": "user", "content": prompt}
        ]

        return await self._call_llm(messages, max_tokens=2500, temperature=0.6)

    async def generate_research_gap_analysis(self, paper_id: int) -> Optional[str]:
        """
        Generate research gap identification (Prompt #7).
        
        Identifies:
        - Gaps This Paper Addressed
        - Gaps This Paper Creates
        - Why These Gaps Matter
        - Feasible Next Steps
        """
        paper_data = await self._get_paper_content(paper_id)
        if not paper_data:
            return None

        prompt = f"""Based on this paper, identify the research gaps it addresses and creates:

{paper_data['content']}

Analyze:
- Gaps This Paper Addressed: What prior knowledge or methodological gaps did it fill?
- Gaps This Paper Creates: What new questions emerge from the findings?
- Why These Gaps Matter: What are the theoretical or practical implications of these gaps?
- Feasible Next Steps: What follow-up research would logically address these gaps?

Format as a structured gap analysis."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert research strategist specializing in identifying research gaps and proposing next steps for scientific inquiry."
            },
            {"role": "user", "content": prompt}
        ]

        return await self._call_llm(messages, max_tokens=2000, temperature=0.7)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.http_session:
            await self.http_session.close()
