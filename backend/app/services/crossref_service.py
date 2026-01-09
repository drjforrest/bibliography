"""
Crossref API integration for DOI metadata lookup.

Crossref is the official DOI registration agency and has the most complete metadata
for academic papers, including volume, issue, pages, and journal information.

Documentation: https://api.crossref.org/
"""

import logging
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Crossref API base URL
CROSSREF_API_BASE = "https://api.crossref.org/works"


class CrossrefService:
    """Service for fetching paper metadata from Crossref API."""

    def __init__(self):
        """Initialize Crossref service."""
        timeout = httpx.Timeout(30.0, connect=5.0)
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
        )
        logger.info("Crossref service initialized")

    async def close(self):
        """Close the HTTP client and clean up resources."""
        await self.client.aclose()

    async def get_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """
        Get paper metadata by DOI from Crossref.

        Args:
            doi: Paper DOI (e.g., "10.1038/nature12373")

        Returns:
            Dictionary with normalized paper metadata or None if not found
        """
        # Clean DOI - remove any URL prefixes
        clean_doi = doi.strip()
        if clean_doi.startswith("http://") or clean_doi.startswith("https://"):
            clean_doi = clean_doi.split("doi.org/")[-1] if "doi.org/" in clean_doi else clean_doi
        if clean_doi.startswith("doi:"):
            clean_doi = clean_doi[4:]

        url = f"{CROSSREF_API_BASE}/{clean_doi}"

        try:
            response = await self.client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()

            data = response.json()
            if data.get("status") == "ok" and "message" in data:
                crossref_data = data["message"]
                return self._normalize_crossref_data(crossref_data)
            else:
                logger.warning(f"Crossref returned unexpected format for DOI: {doi}")
                return None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"⚠️ Paper not found in Crossref: {doi}")
                return None
            logger.error(
                f"❌ Crossref API HTTP error for DOI {doi}: "
                f"status_code={e.response.status_code}, "
                f"error={e.response.text[:200] if e.response.text else 'N/A'}"
            )
            return None
        except httpx.RequestError as e:
            logger.error(
                f"❌ Crossref API request error for DOI {doi}: "
                f"error={e}, "
                f"error_type={type(e).__name__}"
            )
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching from Crossref for DOI {doi}: {e}")
            return None

    def _normalize_crossref_data(self, crossref_data: Dict) -> Dict:
        """
        Normalize Crossref API response to our schema.

        Args:
            crossref_data: Raw Crossref API response

        Returns:
            Normalized dictionary with our field names
        """
        normalized = {}

        # Title
        if crossref_data.get("title"):
            titles = crossref_data["title"]
            if isinstance(titles, list) and titles:
                normalized["title"] = titles[0]
            elif isinstance(titles, str):
                normalized["title"] = titles

        # Authors
        authors = []
        if crossref_data.get("author"):
            for author in crossref_data["author"]:
                # Crossref author format: {"given": "John", "family": "Doe", ...}
                given = author.get("given", "")
                family = author.get("family", "")
                name = f"{given} {family}".strip() if given or family else None
                if name:
                    authors.append(name)
        if authors:
            normalized["authors"] = authors

        # Journal (container-title or short-container-title)
        if crossref_data.get("container-title"):
            containers = crossref_data["container-title"]
            if isinstance(containers, list) and containers:
                normalized["journal"] = containers[0]
            elif isinstance(containers, str):
                normalized["journal"] = containers
        elif crossref_data.get("short-container-title"):
            containers = crossref_data["short-container-title"]
            if isinstance(containers, list) and containers:
                normalized["journal"] = containers[0]
            elif isinstance(containers, str):
                normalized["journal"] = containers

        # Volume
        if crossref_data.get("volume"):
            normalized["volume"] = str(crossref_data["volume"])

        # Issue
        if crossref_data.get("issue"):
            normalized["issue"] = str(crossref_data["issue"])

        # Pages
        pages = None
        if crossref_data.get("page"):
            pages = crossref_data["page"]
        elif crossref_data.get("article-number"):
            # Some papers use article-number instead of pages
            pages = f"e{crossref_data['article-number']}"
        
        if pages:
            normalized["pages"] = str(pages)

        # Publication year (from published-print or published-online date)
        if crossref_data.get("published-print"):
            dates = crossref_data["published-print"]["date-parts"][0]
            if dates and len(dates) > 0:
                normalized["publication_year"] = int(dates[0])
        elif crossref_data.get("published-online"):
            dates = crossref_data["published-online"]["date-parts"][0]
            if dates and len(dates) > 0:
                normalized["publication_year"] = int(dates[0])
        elif crossref_data.get("created"):
            dates = crossref_data["created"]["date-parts"][0]
            if dates and len(dates) > 0:
                normalized["publication_year"] = int(dates[0])

        # Abstract
        if crossref_data.get("abstract"):
            # Crossref abstracts are often wrapped in <jats:p> tags
            abstract = crossref_data["abstract"]
            if isinstance(abstract, str):
                # Remove HTML/JATS tags
                import re
                abstract = re.sub(r"<[^>]+>", "", abstract)
                abstract = abstract.strip()
                if abstract:
                    normalized["abstract"] = abstract

        # DOI
        if crossref_data.get("DOI"):
            normalized["doi"] = crossref_data["DOI"]

        # Keywords (subject field)
        keywords = []
        if crossref_data.get("subject"):
            keywords = [s for s in crossref_data["subject"] if isinstance(s, str)]
        if keywords:
            normalized["keywords"] = keywords

        # Open access
        if crossref_data.get("is-referenced-by-count"):
            normalized["citation_count"] = int(crossref_data["is-referenced-by-count"])

        # License information (for open access detection)
        if crossref_data.get("license"):
            # Check if any license indicates open access
            licenses = crossref_data["license"] if isinstance(crossref_data["license"], list) else [crossref_data["license"]]
            for license_info in licenses:
                if license_info.get("content-version") == "vor":  # Version of Record
                    normalized["is_open_access"] = True
                    break

        return normalized


# Factory function
def create_crossref_service() -> CrossrefService:
    """Create Crossref service instance."""
    return CrossrefService()
