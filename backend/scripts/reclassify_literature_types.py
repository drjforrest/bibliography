#!/usr/bin/env python3
"""
Script to re-classify existing papers' literature_type based on DEVONthink metadata.

This script:
1. Finds papers with dt_source_uuid (synced from DEVONthink)
2. Fetches their DEVONthink metadata
3. Re-determines literature_type using the same logic as sync
4. Updates papers that have changed

Usage:
    python backend/scripts/reclassify_literature_types.py [--dry-run] [--limit N]
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config
from app.db import LiteratureType, ScientificPaper, get_async_session
from app.services.devonthink_mcp_client import DevonthinkMCPClient
from app.services.pdf_processor import PDFProcessor
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _determine_literature_type(
    record_props: dict, pdf_metadata: Optional[dict] = None
) -> LiteratureType:
    """Determine literature type from DEVONthink record properties and PDF metadata.
    
    Same logic as DevonthinkSyncService._determine_literature_type
    """
    # Get comment (Finder Comment) - highest priority (explicit user classification)
    comment = record_props.get("comment", "") or ""
    comment_lower = comment.lower()
    
    # Check Finder Comment for hashtags
    if any(
        tag in comment_lower
        for tag in ["#peer-review", "#peer", "#journal", "#academic"]
    ):
        return LiteratureType.PEER_REVIEWED
    elif any(
        tag in comment_lower for tag in ["#grey-lit", "#grey", "#gray-lit", "#gray"]
    ):
        return LiteratureType.GREY_LITERATURE
    elif any(tag in comment_lower for tag in ["#news", "#media", "#press"]):
        return LiteratureType.NEWS
    
    # Check for DOI - strong indicator of peer-reviewed (takes precedence over other heuristics)
    if pdf_metadata and pdf_metadata.get("doi"):
        # DOI almost always indicates peer-reviewed academic paper
        return LiteratureType.PEER_REVIEWED
    
    # Check tags for keywords
    tags = record_props.get("tags", [])
    if tags:
        tags_str = " ".join(str(tag).lower() for tag in tags)
        if any(
            term in tags_str
            for term in ["grey", "gray", "grey literature", "gray literature"]
        ):
            return LiteratureType.GREY_LITERATURE
        elif any(term in tags_str for term in ["news", "media", "press"]):
            return LiteratureType.NEWS
        elif any(term in tags_str for term in ["peer", "journal", "academic"]):
            return LiteratureType.PEER_REVIEWED
    
    # Check folder path (location) for keywords
    location = record_props.get("location", "") or ""
    location_lower = location.lower()
    if any(
        term in location_lower
        for term in ["grey", "gray", "grey literature", "gray literature"]
    ):
        return LiteratureType.GREY_LITERATURE
    elif any(term in location_lower for term in ["news", "media", "press"]):
        return LiteratureType.NEWS
    elif any(term in location_lower for term in ["peer", "journal", "academic"]):
        return LiteratureType.PEER_REVIEWED
    
    # Use PDF metadata heuristics if available
    if pdf_metadata:
        # Strong indicators of peer-reviewed
        has_doi = bool(pdf_metadata.get("doi"))
        has_journal = bool(pdf_metadata.get("journal"))
        has_abstract = bool(pdf_metadata.get("abstract"))
        has_references = bool(
            pdf_metadata.get("references")
            and len(pdf_metadata.get("references", [])) > 5
        )
        
        # Get metadata for analysis
        title = (pdf_metadata.get("title") or "").lower()
        journal = (pdf_metadata.get("journal") or "").lower()
        pub_year = pdf_metadata.get("publication_year")
        full_text = (pdf_metadata.get("full_text") or "")[:1000].lower()  # First 1000 chars for analysis
        
        # News article indicators
        news_keywords_title = [
            "breaking",
            "news",
            "article",
            "press release",
            "announcement",
            "update",
            "reports",
            "coverage",
            "story",
        ]
        news_sources = [
            "bbc",
            "cnn",
            "reuters",
            "ap news",
            "associated press",
            "the guardian",
            "new york times",
            "washington post",
            "the times",
            "financial times",
            "wall street journal",
            "wsj",
            "the economist",
            "nature news",
            "science news",
            "scientific american news",
        ]
        news_indicators_text = [
            "by our staff",
            "reported by",
            "according to sources",
            "breaking news",
            "live updates",
            "this just in",
        ]
        
        # Check for news indicators (high priority - news is very distinct)
        title_has_news = any(keyword in title for keyword in news_keywords_title)
        journal_is_news = any(source in journal for source in news_sources)
        text_has_news = any(indicator in full_text for indicator in news_indicators_text)
        is_recent_news = pub_year and pub_year >= 2020  # Recent publication suggests news
        
        # Strong news indicators: news source in journal OR multiple news keywords
        if journal_is_news or (title_has_news and text_has_news):
            return LiteratureType.NEWS
        # Moderate news indicators: recent + news keywords
        if is_recent_news and (title_has_news or text_has_news):
            return LiteratureType.NEWS
        
        # Grey literature indicators
        grey_lit_keywords = [
            "report",
            "brief",
            "white paper",
            "policy brief",
            "working paper",
            "technical report",
            "case study",
            "handbook",
            "guide",
            "manual",
            "position paper",
            "discussion paper",
        ]
        
        # Check title for grey literature indicators
        if any(keyword in title for keyword in grey_lit_keywords):
            return LiteratureType.GREY_LITERATURE
        
        # Note: DOI already checked above and returns PEER_REVIEWED if present
        # Remaining peer-reviewed indicators (DOI already handled)
        peer_reviewed_score = 0
        if has_journal:
            peer_reviewed_score += 2  # Journal name is strong indicator
        if has_abstract:
            peer_reviewed_score += 1  # Abstract suggests academic paper
        if has_references:
            peer_reviewed_score += 1  # Many references suggests peer-reviewed
        
        # If we have strong indicators, classify as peer-reviewed
        if peer_reviewed_score >= 2:
            return LiteratureType.PEER_REVIEWED
        
        # If we have weak indicators, check for grey lit patterns
        if peer_reviewed_score < 2:
            # No journal and no abstract suggests grey literature
            if not has_journal and not has_abstract:
                return LiteratureType.GREY_LITERATURE
    
    # Default to peer-reviewed (conservative - assumes academic context)
    return LiteratureType.PEER_REVIEWED


async def reclassify_papers(
    session: AsyncSession,
    dry_run: bool = True,
    limit: Optional[int] = None,
) -> dict:
    """Re-classify papers based on DEVONthink metadata and PDF metadata."""
    mcp_client = DevonthinkMCPClient()
    pdf_processor = PDFProcessor(session)
    
    # Get all papers with DEVONthink UUIDs
    stmt = select(ScientificPaper).where(
        ScientificPaper.dt_source_uuid.isnot(None)
    )
    if limit:
        stmt = stmt.limit(limit)
    
    result = await session.execute(stmt)
    papers = result.scalars().all()
    
    logger.info(f"Found {len(papers)} papers with DEVONthink UUIDs")
    
    stats = {
        "total": len(papers),
        "updated": 0,
        "unchanged": 0,
        "errors": 0,
        "not_found": 0,
    }
    
    for paper in papers:
        try:
            # Fetch DEVONthink record properties
            record_props = await mcp_client.get_record_properties(
                record_uuid=paper.dt_source_uuid
            )
            
            if not record_props or not record_props.get("success", False):
                logger.warning(
                    f"Could not fetch DEVONthink properties for paper {paper.id} "
                    f"(UUID: {paper.dt_source_uuid})"
                )
                stats["not_found"] += 1
                continue
            
            # Try to get PDF metadata if file exists
            pdf_metadata = None
            if paper.file_path:
                try:
                    import os
                    if not os.path.isabs(paper.file_path):
                        pdf_path = os.path.join(config.PDF_STORAGE_ROOT, paper.file_path)
                    else:
                        pdf_path = paper.file_path
                    
                    if os.path.exists(pdf_path):
                        pdf_metadata = await pdf_processor.extract_metadata(pdf_path)
                except Exception as e:
                    logger.debug(f"Could not extract PDF metadata for paper {paper.id}: {e}")
                    # Continue without PDF metadata - will use DEVONthink metadata only
            
            # Determine correct literature type using both sources
            correct_type = _determine_literature_type(record_props, pdf_metadata)
            
            # Check if update needed
            if paper.literature_type == correct_type:
                stats["unchanged"] += 1
                logger.debug(
                    f"Paper {paper.id} ({paper.title[:50]}...) already has correct type: {correct_type.value}"
                )
            else:
                stats["updated"] += 1
                logger.info(
                    f"Paper {paper.id} ({paper.title[:50]}...): "
                    f"{paper.literature_type.value} → {correct_type.value}"
                )
                
                if not dry_run:
                    paper.literature_type = correct_type
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"Error processing paper {paper.id}: {e}")
            stats["errors"] += 1
            await session.rollback()
    
    return stats


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Re-classify papers' literature_type from DEVONthink metadata"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually update papers, just show what would change",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of papers to process (for testing)",
    )
    args = parser.parse_args()
    
    async for session in get_async_session():
        try:
            stats = await reclassify_papers(
                session, dry_run=args.dry_run, limit=args.limit
            )
            
            print("\n" + "=" * 60)
            print("Re-classification Summary")
            print("=" * 60)
            print(f"Total papers processed: {stats['total']}")
            print(f"Would be updated: {stats['updated']}")
            print(f"Already correct: {stats['unchanged']}")
            print(f"Errors: {stats['errors']}")
            print(f"Not found in DEVONthink: {stats['not_found']}")
            
            if args.dry_run:
                print("\n⚠️  DRY RUN - No changes were made")
                print("Run without --dry-run to apply changes")
            else:
                print(f"\n✅ Updated {stats['updated']} papers")
                
        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(main())
