"""
Semantic Scholar API integration for paper recommendations.

Documentation: https://api.semanticscholar.org/api-docs/
"""

import logging
from datetime import timedelta
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://api.semanticscholar.org"
GRAPH_API = f"{BASE_URL}/graph/v1"
RECOMMENDATIONS_API = f"{BASE_URL}/recommendations/v1"

# Rate limiting (free tier: 100 requests/5 minutes)
RATE_LIMIT_WINDOW = timedelta(minutes=5)
RATE_LIMIT_MAX_REQUESTS = 100  # Free tier (increases to 1000 with API key)


def truncate_unicode(s: str, max_chars: int) -> str:
    """
    Truncate a Unicode string safely to max_chars characters, appending ellipsis if truncated.

    This function ensures that multi-byte Unicode characters are not split,
    as it works on Unicode code points rather than bytes.

    Args:
        s: String to truncate
        max_chars: Maximum number of characters to return

    Returns:
        Truncated string with ellipsis if it was longer than max_chars
    """
    if not s:
        return s
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "..."


class SemanticScholarService:
    """Service for interacting with Semantic Scholar API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Semantic Scholar service.

        Args:
            api_key: Optional API key for higher rate limits
                    Get one free at: https://www.semanticscholar.org/product/api
        """
        self.api_key = api_key
        self.headers = {}

        if api_key:
            self.headers["x-api-key"] = api_key
            logger.info("✅ Semantic Scholar API key configured")
        else:
            logger.warning("⚠️ No API key - using free tier (100 req/5min)")

        # Create a single AsyncClient for connection pooling with production-ready config
        # Timeout configuration: connect (5s), read (30s), write (30s), pool (60s)
        timeout = httpx.Timeout(
            connect=5.0,  # Connection timeout
            read=30.0,  # Read timeout
            write=30.0,  # Write timeout
            pool=60.0,  # Pool timeout
        )
        # Connection limits for production: max connections per host, max keepalive connections
        limits = httpx.Limits(
            max_keepalive_connections=10,  # Keep connections alive for reuse
            max_connections=20,  # Max total connections
        )
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,  # Follow redirects automatically
        )

    async def close(self):
        """Close the HTTP client and clean up resources."""
        await self.client.aclose()

    async def search_papers(
        self, query: str, limit: int = 10, fields: Optional[List[str]] = None
    ) -> Dict:
        """
        Search for papers by query string.

        Args:
            query: Search query (e.g., "machine learning healthcare")
            limit: Number of results (max 100)
            fields: List of fields to return (default: title, url, paperId)

        Returns:
            {
                "total": int,
            "limit": max(1, min(limit, 100)),
                "data": [
                    {
                        "paperId": "...",
                        "title": "...",
                        "url": "...",
                        # ... other fields if requested
                    }
                ]
            }
        """
        if not fields:
            fields = ["title", "url", "paperId", "abstract", "year", "authors"]

        url = f"{GRAPH_API}/paper/search"
        params = {"query": query, "limit": min(limit, 100), "fields": ",".join(fields)}

        try:
            response = await self.client.get(url, params=params, headers=self.headers)
            response.raise_for_status()

            result = response.json()
            logger.info(
                f"✅ Semantic Scholar search: '{query}' → {result.get('total', 0)} results"
            )
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Semantic Scholar API error: {e.response.status_code}")
            if e.response.status_code == 429:
                raise Exception("Rate limit exceeded. Try again in a few minutes.")
            raise
        except Exception as e:
            logger.error(f"❌ Semantic Scholar request failed: {e}")
            raise

    async def get_recommendations(
        self, paper_id: str, limit: int = 10, fields: Optional[List[str]] = None
    ) -> Dict:
        """
        Get paper recommendations based on a seed paper.

        Args:
            paper_id: Semantic Scholar paper ID or DOI
            limit: Number of recommendations (max 100)
            fields: List of fields to return

        Returns:
            {
                "recommendedPapers": [
                    {
                        "paperId": "...",
                        "title": "...",
                        "url": "...",
                        # ... other fields
                    }
                ]
            }
        """
        if not fields:
            fields = [
                "title",
                "url",
                "paperId",
                "abstract",
                "year",
                "authors",
                "citationCount",
                "isOpenAccess",
                "openAccessPdf",
            ]

        url = f"{RECOMMENDATIONS_API}/papers/forpaper/{paper_id}"
        params = {"limit": min(limit, 100), "fields": ",".join(fields)}

        try:
            response = await self.client.get(url, params=params, headers=self.headers)
            response.raise_for_status()

            result = response.json()
            rec_count = len(result.get("recommendedPapers", []))
            logger.info(f"✅ Got {rec_count} recommendations for paper {paper_id}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Semantic Scholar API error: {e.response.status_code}")
            if e.response.status_code == 404:
                raise Exception("Paper not found in Semantic Scholar")
            if e.response.status_code == 429:
                raise Exception("Rate limit exceeded. Try again in a few minutes.")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to get recommendations: {e}")
            raise

    async def get_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """
        Get paper details by DOI.

        Args:
            doi: Paper DOI (e.g., "10.1038/nature12373")

        Returns:
            Paper details or None if not found (404), raises for other errors
        """
        url = f"{GRAPH_API}/paper/DOI:{doi}"
        params = {"fields": "paperId,title,abstract,year,authors,url,citationCount"}

        try:
            response = await self.client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            # Handle 404 (not found) by returning None
            if e.response.status_code == 404:
                logger.warning(f"⚠️ Paper not found in Semantic Scholar: {doi}")
                return None
            # For other HTTP errors, log and re-raise
            logger.error(
                f"❌ Semantic Scholar API HTTP error for DOI {doi}: "
                f"status_code={e.response.status_code}, "
                f"error={e}, "
                f"response_text={e.response.text[:200] if e.response.text else 'N/A'}"
            )
            raise
        except httpx.RequestError as e:
            # Handle network/timeout errors - log and re-raise (don't silently return None)
            logger.error(
                f"❌ Semantic Scholar API request error for DOI {doi}: "
                f"error={e}, "
                f"error_type={type(e).__name__}"
            )
            raise

    async def get_recommendations_for_library_paper(
        self, paper: Dict, limit: int = 10
    ) -> Dict:
        """
        Get recommendations for a paper from your library.

        Tries multiple strategies to find the paper in Semantic Scholar:
        1. Use DOI if available
        2. Search by title
        3. Return empty if not found

        Args:
            paper: Your library paper dict with doi, title, etc.
            limit: Number of recommendations

        Returns:
            Recommendations result or empty dict
        """
        paper_id = None

        # Strategy 1: Try DOI
        if paper.get("doi"):
            logger.info(f"🔍 Looking up paper by DOI: {paper['doi']}")
            s2_paper = await self.get_paper_by_doi(paper["doi"])
            if s2_paper and s2_paper.get("paperId"):
                paper_id = s2_paper["paperId"]
        # Strategy 2: Search by title
        if not paper_id and paper.get("title"):
            logger.info(
                f"🔍 Searching by title: {truncate_unicode(paper['title'], 60)}"
            )
            search_results = await self.search_papers(
                query=paper["title"], limit=1, fields=["paperId", "title"]
            )

            if search_results.get("data"):
                # Take first result (best match)
                paper_id = search_results["data"][0]["paperId"]

        # Get recommendations
        if paper_id:
            return await self.get_recommendations(paper_id, limit=limit)
        else:
            logger.warning("⚠️ Could not find paper in Semantic Scholar")
            return {"recommendedPapers": []}


# Factory function
def create_semantic_scholar_service(
    api_key: Optional[str] = None,
) -> SemanticScholarService:
    """Create Semantic Scholar service instance."""
    return SemanticScholarService(api_key=api_key)
