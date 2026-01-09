# Semantic Scholar Paper Recommendations - V1 Implementation Plan

**Date:** 2026-01-08  
**Target:** V1 (Production system)  
**Feature:** AI-powered paper recommendations using Semantic Scholar API

---

## Feature Overview

Add Semantic Scholar integration to help users discover related papers based on their existing library.

### User Flow

```
1. User views a paper in their library
   ↓
2. Clicks "Find Related Papers" button
   ↓
3. Backend calls Semantic Scholar API with paper DOI/title
   ↓
4. Returns 10 recommended papers with titles, abstracts, URLs
   ↓
5. User can:
   - Preview recommendations
   - Save promising papers to library
   - Download PDFs (if available)
   - Mark as "to read"
```

---

## Semantic Scholar API

### Endpoints We'll Use

**1. Paper Search** (for finding papers not in library)

```
GET https://api.semanticscholar.org/graph/v1/paper/search
Params: query, limit, fields
```

**2. Paper Recommendations** (core feature)

```
GET https://api.semanticscholar.org/recommendations/v1/papers/forpaper/{paperId}
Params: fields, limit
```

**3. Paper Details** (for enriching data)

```
GET https://api.semanticscholar.org/graph/v1/paper/{paperId}
Params: fields
```

### Available Fields

```
title, authors, abstract, url, venue, year, citationCount,
influentialCitationCount, isOpenAccess, openAccessPdf,
fieldsOfStudy, publicationTypes, publicationDate
```

### Rate Limits

- **Free tier:** 100 requests/5 minutes
- **API Key (recommended):** 1,000 requests/5 minutes (free!)
- **Sign up:** https://www.semanticscholar.org/product/api

---

## Implementation Architecture

### Backend Components

```
/backend/app/
├── services/
│   └── semantic_scholar_service.py   # NEW - API integration
├── routes/
│   └── recommendations_routes.py      # NEW - API endpoints
└── schemas/
    └── recommendations.py             # NEW - Pydantic models
```

### Frontend Components

```
/frontend/nextjs-app/src/
├── components/
│   ├── RecommendationsButton.tsx      # NEW - Trigger button
│   ├── RecommendationsModal.tsx       # NEW - Results display
│   └── RecommendationCard.tsx         # NEW - Individual paper card
└── api/
    └── recommendations-api.ts         # NEW - API client
```

---

## Backend Implementation

### 1. Semantic Scholar Service

**File:** `/backend/app/services/semantic_scholar_service.py`

```python
"""
Semantic Scholar API integration for paper recommendations.

Documentation: https://api.semanticscholar.org/api-docs/
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://api.semanticscholar.org"
GRAPH_API = f"{BASE_URL}/graph/v1"
RECOMMENDATIONS_API = f"{BASE_URL}/recommendations/v1"

# Rate limiting (enforced per-user on our API endpoints)
RATE_LIMIT_WINDOW = timedelta(minutes=5)
RATE_LIMIT_MAX_REQUESTS = 100  # Free tier (increases to 1000 with API key)


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

    async def search_papers(
        self,
        query: str,
        limit: int = 10,
        fields: Optional[List[str]] = None
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
                "offset": int,
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
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": ",".join(fields)
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )
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
        self,
        paper_id: str,
        limit: int = 10,
        fields: Optional[List[str]] = None
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
                "title", "url", "paperId", "abstract", "year",
                "authors", "citationCount", "isOpenAccess", "openAccessPdf"
            ]

        url = f"{RECOMMENDATIONS_API}/papers/forpaper/{paper_id}"
        params = {
            "limit": min(limit, 100),
            "fields": ",".join(fields)
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()

                result = response.json()
                rec_count = len(result.get("recommendedPapers", []))
                logger.info(
                    f"✅ Got {rec_count} recommendations for paper {paper_id}"
                )
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
            Paper details or None if not found
        """
        url = f"{GRAPH_API}/paper/DOI:{doi}"
        params = {
            "fields": "paperId,title,abstract,year,authors,url,citationCount"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code == 404:
                    logger.warning(f"⚠️ Paper not found in Semantic Scholar: {doi}")
                    return None

                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"❌ Failed to get paper by DOI: {e}")
            return None

    async def get_recommendations_for_library_paper(
        self,
        paper: Dict,
        limit: int = 10
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
            if s2_paper:
                paper_id = s2_paper["paperId"]

        # Strategy 2: Search by title
        if not paper_id and paper.get("title"):
            logger.info(f"🔍 Searching by title: {paper['title'][:60]}...")
            search_results = await self.search_papers(
                query=paper["title"],
                limit=1,
                fields=["paperId", "title"]
            )

            if search_results.get("data"):
                # Take first result (best match)
                paper_id = search_results["data"][0]["paperId"]

        # Get recommendations
        if paper_id:
            return await self.get_recommendations(paper_id, limit=limit)
        else:
            logger.warning(f"⚠️ Could not find paper in Semantic Scholar")
            return {"recommendedPapers": []}


# Factory function
def create_semantic_scholar_service(api_key: Optional[str] = None) -> SemanticScholarService:
    """Create Semantic Scholar service instance."""
    return SemanticScholarService(api_key=api_key)
```

### 2. Rate Limiting

The service implements per-user rate limiting to prevent abuse and stay within Semantic Scholar API limits:

- **Rate Limiter Service** (`app/services/rate_limiter.py`): Tracks requests per user within a sliding time window
- **Integration**: Rate limiting is enforced in all recommendations endpoints
- **Configuration**: Uses `RATE_LIMIT_WINDOW` and `RATE_LIMIT_MAX_REQUESTS` constants from `semantic_scholar_service.py`
- **Response**: Returns 429 status code with rate limit headers when exceeded

**Rate Limit Headers:**

- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Seconds until window resets

### 3. Pydantic Schemas

**File:** `/backend/app/schemas/recommendations.py`

```python
"""Schemas for paper recommendations."""

from typing import List, Optional
from pydantic import BaseModel, Field


class Author(BaseModel):
    """Author information from Semantic Scholar."""
    authorId: Optional[str] = None
    name: str


class OpenAccessPdf(BaseModel):
    """Open access PDF information."""
    url: Optional[str] = None
    status: Optional[str] = None


class RecommendedPaper(BaseModel):
    """A recommended paper from Semantic Scholar."""
    paperId: str
    title: str
    url: Optional[str] = None
    abstract: Optional[str] = None
    year: Optional[int] = None
    authors: list[Author] = Field(default_factory=list)
    citationCount: int = 0
    isOpenAccess: bool = False
    openAccessPdf: Optional[OpenAccessPdf] = None

    class Config:
        from_attributes = True


class RecommendationsResponse(BaseModel):
    """Response for paper recommendations request."""
    source_paper_id: int
    source_paper_title: str
    recommendations: List[RecommendedPaper]
    total_found: int

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    """Paper search result from Semantic Scholar."""
    paperId: str
    title: str
    url: Optional[str] = None
    abstract: Optional[str] = None
    year: Optional[int] = None
    authors: Optional[List[Author]] = []


class SearchResponse(BaseModel):
    """Response for paper search request."""
    total: int
    offset: int
    data: List[SearchResult]

    class Config:
        from_attributes = True
```

### 3. Rate Limiting Service

**File:** `/backend/app/services/rate_limiter.py`

The rate limiter enforces per-user request limits using the constants defined in `semantic_scholar_service.py`. It tracks request timestamps per client within a sliding time window and rejects excess requests with a 429 status code.

**Key Features:**

- Per-user rate limiting (tracks by user ID)
- Sliding window algorithm
- Automatic cleanup of old entries
- Returns rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)

### 4. API Routes

**File:** `/backend/app/routes/recommendations_routes.py`

```python
"""
API routes for paper recommendations using Semantic Scholar.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db import get_async_session
from app.middleware.clerk_auth import require_clerk_auth, User
from app.services.semantic_scholar_service import (
    create_semantic_scholar_service,
    RATE_LIMIT_WINDOW,
    RATE_LIMIT_MAX_REQUESTS,
)
from app.services.rate_limiter import RateLimiter
from app.services.paper_manager import PaperManagerService
from app.schemas.recommendations import (
    RecommendationsResponse,
    RecommendedPaper,
    SearchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Initialize rate limiter with constants from semantic_scholar_service
# This enforces per-user rate limits on our recommendations endpoints
rate_limiter = RateLimiter(
    window=RATE_LIMIT_WINDOW,
    max_requests=RATE_LIMIT_MAX_REQUESTS,
)


@router.get("/{paper_id}", response_model=RecommendationsResponse)
async def get_recommendations_for_paper(
    paper_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get paper recommendations based on a paper in your library.

    Args:
        paper_id: ID of paper in your library
        limit: Number of recommendations (1-100, default 10)

    Returns:
        Recommendations from Semantic Scholar
    """
    # Rate limiting: check if user has exceeded request limit
    client_id = str(user.id)
    allowed, remaining, reset_after = rate_limiter.check_rate_limit(client_id)

    if not allowed:
        logger.warning(
            f"Rate limit exceeded for user {user.id}: {remaining} remaining, "
            f"reset in {reset_after}s"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please try again in {reset_after} seconds.",
            headers={
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_after),
            },
        )

    try:
        # Get paper from library
        paper_manager = PaperManagerService(session)
        paper = await paper_manager.get_paper_by_id(paper_id)

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Get Semantic Scholar service
        api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
        s2_service = create_semantic_scholar_service(api_key=api_key)

        # Get recommendations
        logger.info(
            f"Getting recommendations for paper {paper_id}: {paper.title[:60]}... "
            f"(user {user.id}, {remaining} requests remaining)"
        )

        result = await s2_service.get_recommendations_for_library_paper(
            paper={
                "doi": paper.doi,
                "title": paper.title,
            },
            limit=limit,
        )

        recommendations = [
            RecommendedPaper(**rec)
            for rec in result.get("recommendedPapers", [])
        ]

        return RecommendationsResponse(
            source_paper_id=paper_id,
            source_paper_title=paper.title,
            recommendations=recommendations,
            total_found=len(recommendations)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get recommendations. Please try again later."
        )


@router.get("/search", response_model=SearchResponse)
async def search_semantic_scholar(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=100),
    user: User = Depends(require_clerk_auth),
):
    """
    Search Semantic Scholar for papers.

    Args:
        query: Search query string
        limit: Number of results (1-100, default 10)

    Returns:
        Search results from Semantic Scholar
    """
    # Rate limiting: check if user has exceeded request limit
    client_id = str(user.id)
    allowed, remaining, reset_after = rate_limiter.check_rate_limit(client_id)

    if not allowed:
        logger.warning(
            f"Rate limit exceeded for user {user.id}: {remaining} remaining, "
            f"reset in {reset_after}s"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please try again in {reset_after} seconds.",
            headers={
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_after),
            },
        )

    try:
        # Get Semantic Scholar service
        api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
        s2_service = create_semantic_scholar_service(api_key=api_key)

        # Search
        logger.info(
            f"Searching Semantic Scholar: '{query}' "
            f"(user {user.id}, {remaining} requests remaining)"
        )
        result = await s2_service.search_papers(query=query, limit=limit)

        return SearchResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching Semantic Scholar: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Search failed. Please try again later."
        )


@router.get("/health")
async def check_semantic_scholar_health(
    user: User = Depends(require_clerk_auth),
):
    """
    Check if Semantic Scholar API is accessible.

    Returns:
        Status and configuration info
    """
    try:
        api_key = getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
        s2_service = create_semantic_scholar_service(api_key=api_key)

        # Try a simple search to test connectivity
        result = await s2_service.search_papers("machine learning", limit=1)

        return {
            "status": "healthy",
            "api_key_configured": bool(api_key),
            "rate_limit": "1000/5min" if api_key else "100/5min",
            "test_search_results": result.get("total", 0),
        }
    except Exception as e:
        logger.error(f"Error checking Semantic Scholar health: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": "Service unavailable. Please try again later.",
            "api_key_configured": bool(
                getattr(config, "SEMANTIC_SCHOLAR_API_KEY", None)
            ),
        }
```

---

## Frontend Implementation

### 1. Recommendations Button Component

**File:** `/frontend/nextjs-app/src/components/RecommendationsButton.tsx`

```typescript
"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecommendationsModal } from "./RecommendationsModal";

interface RecommendationsButtonProps {
  paperId: number;
  paperTitle: string;
}

export function RecommendationsButton({
  paperId,
  paperTitle,
}: RecommendationsButtonProps) {
  const [showModal, setShowModal] = useState(false);

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowModal(true)}
        className="gap-2"
      >
        <Sparkles className="h-4 w-4" />
        Find Related Papers
      </Button>

      {showModal && (
        <RecommendationsModal
          paperId={paperId}
          paperTitle={paperTitle}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
}
```

### 2. Recommendations Modal

**File:** `/frontend/nextjs-app/src/components/RecommendationsModal.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import { X, ExternalLink, Download, BookmarkPlus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import {
  getRecommendations,
  type RecommendedPaper,
} from "@/api/recommendations-api";

interface RecommendationsModalProps {
  paperId: number;
  paperTitle: string;
  onClose: () => void;
}

export function RecommendationsModal({
  paperId,
  paperTitle,
  onClose,
}: RecommendationsModalProps) {
  const [loading, setLoading] = useState(true);
  const [recommendations, setRecommendations] = useState<RecommendedPaper[]>(
    []
  );
  const { toast } = useToast();

  useEffect(() => {
    loadRecommendations();
  }, [paperId]);

  async function loadRecommendations() {
    try {
      setLoading(true);
      const data = await getRecommendations(paperId);
      setRecommendations(data.recommendations);

      if (data.recommendations.length === 0) {
        toast({
          title: "No recommendations found",
          description: "This paper may not be in Semantic Scholar's database.",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error loading recommendations",
        description:
          error instanceof Error ? error.message : "Please try again",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Related Papers
          </DialogTitle>
          <p className="text-sm text-muted-foreground">
            Based on: {paperTitle}
          </p>
        </DialogHeader>

        <ScrollArea className="h-[60vh] pr-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
            </div>
          ) : recommendations.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No recommendations found for this paper.
            </div>
          ) : (
            <div className="space-y-4">
              {recommendations.map((paper, idx) => (
                <RecommendationCard
                  key={paper.paperId}
                  paper={paper}
                  rank={idx + 1}
                />
              ))}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

interface RecommendationCardProps {
  paper: RecommendedPaper;
  rank: number;
}

function RecommendationCard({ paper, rank }: RecommendationCardProps) {
  const { toast } = useToast();

  const handleAddToLibrary = () => {
    toast({
      title: "Coming soon",
      description: "Paper import feature will be available soon!",
    });
  };

  return (
    <div className="border rounded-lg p-4 space-y-3 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-muted-foreground">
              #{rank}
            </span>
            <h3 className="font-semibold leading-tight">{paper.title}</h3>
          </div>

          {paper.authors && paper.authors.length > 0 && (
            <p className="text-sm text-muted-foreground">
              {paper.authors
                .slice(0, 3)
                .map((a) => a.name)
                .join(", ")}
              {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
            </p>
          )}

          {paper.abstract && (
            <p className="text-sm text-muted-foreground line-clamp-3">
              {paper.abstract}
            </p>
          )}

          <div className="flex items-center gap-2 flex-wrap">
            {paper.year && <Badge variant="secondary">{paper.year}</Badge>}
            {paper.citationCount !== undefined && (
              <Badge variant="secondary">{paper.citationCount} citations</Badge>
            )}
            {paper.isOpenAccess && (
              <Badge variant="default" className="bg-green-600">
                Open Access
              </Badge>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          {paper.url && (
            <Button variant="ghost" size="sm" asChild>
              <a href={paper.url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4" />
              </a>
            </Button>
          )}

          {paper.openAccessPdf?.url && (
            <Button variant="ghost" size="sm" asChild>
              <a
                href={paper.openAccessPdf.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Download className="h-4 w-4" />
              </a>
            </Button>
          )}

          <Button variant="ghost" size="sm" onClick={handleAddToLibrary}>
            <BookmarkPlus className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
```

### 3. API Client

**File:** `/frontend/nextjs-app/src/api/recommendations-api.ts`

```typescript
import { getAuthToken } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Author {
  authorId?: string;
  name: string;
}

export interface OpenAccessPdf {
  url?: string;
  status?: string;
}

export interface RecommendedPaper {
  paperId: string;
  title: string;
  url?: string;
  abstract?: string;
  year?: number;
  authors?: Author[];
  citationCount?: number;
  isOpenAccess?: boolean;
  openAccessPdf?: OpenAccessPdf;
}

export interface RecommendationsResponse {
  source_paper_id: number;
  source_paper_title: string;
  recommendations: RecommendedPaper[];
  total_found: number;
}

export async function getRecommendations(
  paperId: number,
  limit: number = 10
): Promise<RecommendationsResponse> {
  const token = await getAuthToken();

  const response = await fetch(
    `${API_BASE}/api/recommendations/${paperId}?limit=${limit}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || "Failed to get recommendations");
  }

  return response.json();
}

export async function checkSemanticScholarHealth() {
  const response = await fetch(`${API_BASE}/api/recommendations/health`);
  return response.json();
}
```

---

## Environment Configuration

### Backend `.env`

```bash
# Semantic Scholar API (optional but recommended)
# Get free API key: https://www.semanticscholar.org/product/api
SEMANTIC_SCHOLAR_API_KEY=your_api_key_here

# Without API key: 100 requests / 5 minutes
# With API key: 1,000 requests / 5 minutes (free!)
```

---

## Integration Points

### Where to Add the Button

**1. Paper Detail View**

```tsx
// In paper detail page
<RecommendationsButton paperId={paper.id} paperTitle={paper.title} />
```

**2. Paper List Actions**

```tsx
// In paper list item
<DropdownMenu>
  <DropdownMenuItem onClick={() => handleRecommendations(paper)}>
    <Sparkles className="mr-2 h-4 w-4" />
    Find Related Papers
  </DropdownMenuItem>
</DropdownMenu>
```

**3. Search Results**

```tsx
// After searching
<Button onClick={() => getRecommendations(paper.id)}>
  Discover Similar Papers
</Button>
```

---

## Testing Plan

### 1. Backend Tests

```python
# tests/test_semantic_scholar_service.py

import pytest
from app.services.semantic_scholar_service import create_semantic_scholar_service

@pytest.mark.asyncio
async def test_search_papers():
    service = create_semantic_scholar_service()
    result = await service.search_papers("machine learning", limit=5)

    assert result["total"] > 0
    assert len(result["data"]) <= 5
    assert "paperId" in result["data"][0]

@pytest.mark.asyncio
async def test_get_recommendations():
    service = create_semantic_scholar_service()
    # Use a known paper ID
    result = await service.get_recommendations(
        paper_id="649def34f8be52c8b66281af98ae884c09aef38b",  # BERT paper
        limit=5
    )

    assert "recommendedPapers" in result
    assert len(result["recommendedPapers"]) > 0
```

### 2. Frontend Tests

```typescript
// __tests__/RecommendationsModal.test.tsx

import { render, screen, waitFor } from "@testing-library/react";
import { RecommendationsModal } from "@/components/RecommendationsModal";

jest.mock("@/api/recommendations-api");

test("loads and displays recommendations", async () => {
  render(
    <RecommendationsModal
      paperId={1}
      paperTitle="Test Paper"
      onClose={() => {}}
    />
  );

  await waitFor(() => {
    expect(screen.getByText(/Related Papers/i)).toBeInTheDocument();
  });
});
```

---

## Deployment Checklist

### Backend

#### Core Files & Registration

- [x] Add `semantic_scholar_service.py` to `/backend/app/services/`
- [x] Add `recommendations.py` schemas to `/backend/app/schemas/`
- [x] Add `recommendations_routes.py` to `/backend/app/routes/`
- [x] Register routes in `app/routes/__init__.py` (already included via `recommendations_router`)
- [x] Routes available at `/api/v1/recommendations/*` via `crud_router` in `app.py`

#### Dependency Management & Version Pinning

- [x] Pin `pydantic>=2.9.0,<3.0.0` in `requirements.txt` (ensures Pydantic v2)
- [x] Pin `fastapi==0.115.8` in `requirements.txt` (compatible with Pydantic v2)
- [x] Pin `httpx==0.27.2` in `requirements.txt` (stable version for async HTTP)
- [x] Verify all schemas use Pydantic v2 patterns:
  - [x] `recommendations.py` uses `from_attributes = True` in `Config` class (lines 32, 43, 63)
  - [x] All models inherit from `pydantic.BaseModel` correctly

#### Production HTTPX Configuration

- [x] Configure httpx client pooling in `semantic_scholar_service.py`:
  - [x] Timeouts: `connect=5.0s`, `read=30.0s`, `write=30.0s`, `pool=60.0s`
  - [x] Connection limits: `max_keepalive_connections=10`, `max_connections=20`
  - [x] Follow redirects enabled
  - [x] Client created in `__init__` for connection reuse

#### Structured Logging Configuration

- [x] Service uses `logging.getLogger(__name__)` for structured logging
- [x] Log levels appropriate: `info` for success, `warning` for rate limits, `error` for failures
- [x] Log messages include context: query strings, paper IDs, rate limit status
- [ ] Consider adding structured log formatting (JSON) for production monitoring

#### Monitoring & Rate-Limit Alerts

- [x] Rate limiting implemented via `RateLimiter` service (100 req/5min free tier)
- [x] Rate limit headers included in responses: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- [x] HTTP 429 responses for rate limit exceeded with clear error messages
- [ ] Set up monitoring alerts for rate limit thresholds (e.g., 80% of limit)
- [ ] Configure alerting for Semantic Scholar API failures (5xx errors)
- [ ] Monitor httpx connection pool exhaustion metrics

#### Configuration & Testing

- [ ] Optional: Add `SEMANTIC_SCHOLAR_API_KEY` to `.env` for higher rate limits (1000 req/5min)
- [ ] Test API endpoint: `curl http://localhost:8000/api/v1/recommendations/health`
- [ ] Test recommendations endpoint: `curl http://localhost:8000/api/v1/recommendations/{paper_id}`
- [ ] Test search endpoint: `curl http://localhost:8000/api/v1/recommendations/search?query=machine+learning`

### Frontend

- [ ] Add `RecommendationsButton.tsx` component
- [ ] Add `RecommendationsModal.tsx` component
- [ ] Add `recommendations-api.ts` client
- [ ] Integrate button into paper detail view
- [ ] Test modal opens and loads recommendations

### Testing

- [ ] Backend unit tests pass
- [ ] API endpoints return correct data
- [ ] Frontend displays recommendations
- [ ] Modal opens/closes properly
- [ ] External links work
- [ ] Rate limiting handled gracefully

---

## Timeline

**Estimated time: 4-6 hours**

- Backend service: 1.5 hours
- Backend routes & schemas: 1 hour
- Frontend components: 2 hours
- Integration & testing: 1.5 hours

---

## Future Enhancements

### Phase 2 Features

1. **Import to Library**

   - Add "Import" button on recommendations
   - Fetch full paper metadata
   - Download PDF if open access
   - Add to user's library

2. **Bulk Operations**

   - Select multiple recommendations
   - Import batch to library
   - Export to citation manager

3. **Smart Filtering**

   - Filter by year range
   - Filter by citation count
   - Filter by open access only
   - Filter by field of study

4. **Recommendation History**

   - Track recommendation requests
   - Show previously viewed recommendations
   - "Already in library" indicator

5. **Citation Network**
   - Visualize citation relationships
   - Find papers citing your library papers
   - Find papers cited by your library papers

---

## Questions?

Ready to implement! Let me know if you'd like me to:

1. Start with backend implementation
2. Create all files at once
3. Walk through specific parts
4. Test with your existing V1 setup

This should be straightforward to add—Semantic Scholar's API is well-documented and the feature fits naturally into your existing paper management flow!
