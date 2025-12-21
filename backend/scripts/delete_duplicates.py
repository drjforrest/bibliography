#!/usr/bin/env python3
"""
Delete duplicate papers, keeping the most complete version.

Identifies duplicates by title and keeps the version with the most complete data
(full_text, file_hash, DOI, etc.)
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db import ScientificPaper
from app.config import config

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def delete_duplicates():
    """Delete duplicate papers, keeping the most complete version."""

    # Create async engine
    engine = create_async_engine(config.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find all papers grouped by normalized title
        stmt = select(
            func.lower(func.trim(ScientificPaper.title)).label('normalized_title'),
            func.count().label('count')
        ).group_by(
            func.lower(func.trim(ScientificPaper.title))
        ).having(
            func.count() > 1
        )

        result = await session.execute(stmt)
        duplicate_titles = result.all()

        logger.info(f"Found {len(duplicate_titles)} sets of duplicate titles")

        total_deleted = 0

        for normalized_title, count in duplicate_titles:
            # Get all papers with this title
            papers_stmt = select(ScientificPaper).where(
                func.lower(func.trim(ScientificPaper.title)) == normalized_title
            ).order_by(ScientificPaper.id)

            papers_result = await session.execute(papers_stmt)
            papers = papers_result.scalars().all()

            # Rank papers by completeness
            def completeness_score(paper):
                score = 0
                if paper.full_text and len(paper.full_text) > 100:
                    score += 100
                if paper.file_hash:
                    score += 50
                if paper.doi:
                    score += 30
                if paper.abstract:
                    score += 10
                if paper.publication_year:
                    score += 5
                return score

            # Sort by completeness (highest first)
            papers_sorted = sorted(papers, key=completeness_score, reverse=True)

            # Keep the most complete one, delete the rest
            to_keep = papers_sorted[0]
            to_delete = papers_sorted[1:]

            logger.info(
                f"Title: '{normalized_title[:60]}...' - "
                f"Keeping paper {to_keep.id} (score: {completeness_score(to_keep)}), "
                f"deleting {len(to_delete)} duplicates"
            )

            for paper in to_delete:
                logger.debug(f"  Deleting paper {paper.id} (score: {completeness_score(paper)})")
                await session.delete(paper)
                total_deleted += 1

        # Commit all deletions
        await session.commit()
        logger.info(f"\n{'='*60}")
        logger.info(f"DELETION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total papers deleted: {total_deleted}")
        logger.info(f"Duplicate title sets processed: {len(duplicate_titles)}")
        logger.info(f"{'='*60}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(delete_duplicates())
