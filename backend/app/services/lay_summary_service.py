import asyncio
import aiohttp
import json
import logging
import os
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class LaySummaryService:
    """Service for generating lay summaries of academic papers using Ollama"""
    
    def __init__(self, 
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 timeout: Optional[int] = None):
        
        # Get configuration from environment or parameters
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:8b-instruct-q4_K_M")
        timeout_seconds = timeout or int(os.getenv("OLLAMA_TIMEOUT", "120"))
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Default timeout for LLM requests
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json"
                }
            )
        return self.session
    
    async def generate_lay_summary(self, 
                                 title: str,
                                 abstract: Optional[str] = None,
                                 full_text: Optional[str] = None,
                                 max_length: int = 300) -> Optional[str]:
        """
        Generate a lay summary of an academic paper
        
        Args:
            title: Paper title
            abstract: Paper abstract (if available)
            full_text: Full paper text (if available, will be truncated)
            max_length: Maximum length of summary in words
            
        Returns:
            Generated lay summary or None if generation fails
        """
        try:
            # Prepare input text
            input_text = self._prepare_input_text(title, abstract, full_text)
            if not input_text:
                logger.warning("No input text available for lay summary generation")
                return None
            
            # Generate the lay summary
            summary = await self._call_ollama(input_text, max_length)
            
            if summary:
                # Clean and validate the summary
                cleaned_summary = self._clean_summary(summary)
                logger.debug(f"Generated lay summary for '{title[:50]}...': {len(cleaned_summary)} characters")
                return cleaned_summary
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate lay summary for '{title}': {str(e)}")
            return None
    
    def _prepare_input_text(self, title: str, abstract: Optional[str], full_text: Optional[str]) -> str:
        """Prepare input text for the LLM, prioritizing abstract over full text"""
        
        # Start with title
        input_parts = [f"Title: {title}"]
        
        # Add abstract if available
        if abstract and abstract.strip():
            input_parts.append(f"Abstract: {abstract.strip()}")
        
        # If no abstract, use beginning of full text
        elif full_text and full_text.strip():
            # Get first few paragraphs or first 2000 characters
            truncated_text = self._truncate_full_text(full_text, max_chars=2000)
            input_parts.append(f"Text excerpt: {truncated_text}")
        
        return "\n\n".join(input_parts)
    
    def _truncate_full_text(self, full_text: str, max_chars: int = 2000) -> str:
        """Intelligently truncate full text to extract most relevant parts"""
        
        # Clean the text first
        text = re.sub(r'\s+', ' ', full_text.strip())
        
        # If text is short enough, return as is
        if len(text) <= max_chars:
            return text
        
        # Try to find introduction or methodology sections
        intro_patterns = [
            r'(?i)\n\s*(?:introduction|abstract|summary|background)\s*\n',
            r'(?i)\n\s*1\.?\s*(?:introduction|background)\s*\n',
            r'(?i)(?:^|\n)\s*introduction[:\s]',
            r'(?i)(?:^|\n)\s*background[:\s]'
        ]
        
        best_start = 0
        for pattern in intro_patterns:
            match = re.search(pattern, text[:max_chars * 2])  # Search in first portion
            if match:
                best_start = match.end()
                break
        
        # Extract from best starting point
        if best_start > 0:
            excerpt = text[best_start:best_start + max_chars]
        else:
            # Just take the beginning
            excerpt = text[:max_chars]
        
        # Try to end at a sentence boundary
        last_sentence = max(
            excerpt.rfind('. '),
            excerpt.rfind('! '),
            excerpt.rfind('? ')
        )
        
        if last_sentence > max_chars * 0.7:  # If we can cut at least 70% through
            excerpt = excerpt[:last_sentence + 1]
        
        return excerpt + "..." if len(text) > len(excerpt) else excerpt
    
    async def _call_ollama(self, input_text: str, max_length: int) -> Optional[str]:
        """Make API call to Ollama"""
        
        # Create the prompt
        prompt = self._create_lay_summary_prompt(input_text, max_length)
        
        try:
            session = await self._get_session()
            
            # Prepare the request for Ollama chat API
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a science communicator who excels at explaining complex academic research to general audiences. You create clear, engaging, and accurate lay summaries that make research accessible to everyone."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": max_length + 100,
                    "stop": ["</summary>", "\n\n---", "\n\nNote:", "\n\nDisclaimer:"]
                },
                "stream": False
            }
            
            async with session.post(f"{self.base_url}/api/chat", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if "message" in result and "content" in result["message"]:
                        content = result["message"]["content"].strip()
                        return content
                    else:
                        logger.error(f"Unexpected Ollama response format: {result}")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"Ollama API error {response.status}: {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error("Ollama request timed out")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Ollama connection error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama: {str(e)}")
            return None
    
    def _create_lay_summary_prompt(self, input_text: str, max_length: int) -> str:
        """Create an effective prompt for lay summary generation"""
        
        return f"""Please read this academic paper information and create a clear lay summary for a general audience.

{input_text}

Instructions:
- Write a lay summary that explains this research in simple, accessible language
- Target audience: educated general public (high school to college level)
- Maximum length: {max_length} words
- Focus on: what the researchers did, what they found, and why it matters
- Avoid jargon, technical terms, and complex methodology details
- Use engaging, conversational tone while remaining accurate
- Start with the main finding or significance
- Explain the real-world implications or applications

Lay Summary:"""
    
    def _clean_summary(self, summary: str) -> str:
        """Clean and validate the generated summary"""
        
        # Remove common prefixes/suffixes that the model might add
        prefixes_to_remove = [
            "lay summary:",
            "summary:",
            "here's a lay summary:",
            "here is a lay summary:",
            "the lay summary is:",
            "in simple terms:",
        ]
        
        cleaned = summary.strip()
        
        # Remove prefixes (case insensitive)
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                break
        
        # Remove any markdown formatting that might have been added
        cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned)  # Bold
        cleaned = re.sub(r'\*(.*?)\*', r'\1', cleaned)      # Italic
        cleaned = re.sub(r'`(.*?)`', r'\1', cleaned)        # Code
        
        # Clean up multiple spaces and normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Ensure it ends with proper punctuation
        if cleaned and not cleaned[-1] in '.!?':
            cleaned += '.'
        
        return cleaned
    
    async def test_connection(self) -> bool:
        """Test connection to Ollama"""
        try:
            session = await self._get_session()
            
            # Simple test request
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hello, are you working?"}],
                "options": {
                    "num_predict": 10,
                    "temperature": 0.1
                },
                "stream": False
            }
            
            async with session.post(f"{self.base_url}/api/chat", json=payload) as response:
                success = response.status == 200
                if success:
                    logger.info(f"✅ Ollama connection successful (model: {self.model})")
                else:
                    logger.error(f"❌ Ollama connection failed with status {response.status}")
                return success
                
        except Exception as e:
            logger.error(f"❌ Ollama connection test failed: {str(e)}")
            return False
    
    async def generate_batch_summaries(self, papers_data: list, max_concurrent: int = 3) -> Dict[str, str]:
        """
        Generate lay summaries for multiple papers concurrently
        
        Args:
            papers_data: List of dicts with 'id', 'title', 'abstract', 'full_text'
            max_concurrent: Maximum concurrent requests to avoid overwhelming LM Studio
            
        Returns:
            Dict mapping paper IDs to generated summaries
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def process_paper(paper_data):
            async with semaphore:
                paper_id = paper_data.get('id')
                summary = await self.generate_lay_summary(
                    title=paper_data.get('title', ''),
                    abstract=paper_data.get('abstract'),
                    full_text=paper_data.get('full_text')
                )
                if summary:
                    results[paper_id] = summary
        
        # Process all papers concurrently
        tasks = [process_paper(paper) for paper in papers_data]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"Generated lay summaries for {len(results)}/{len(papers_data)} papers")
        return results
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()


# Singleton instance
_lay_summary_service: Optional[LaySummaryService] = None


def get_lay_summary_service() -> LaySummaryService:
    """Get singleton lay summary service instance"""
    global _lay_summary_service
    if _lay_summary_service is None:
        _lay_summary_service = LaySummaryService()
    return _lay_summary_service