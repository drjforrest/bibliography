"""
Background task to clean up expired visual abstracts.

This task should be run periodically (e.g., daily) to delete visual abstracts
that have exceeded their 30-day expiration period.
"""

import asyncio
import logging
from app.db import get_async_session_context
from app.services.visual_abstract_service import VisualAbstractService

logger = logging.getLogger(__name__)


async def cleanup_expired_visual_abstracts():
    """
    Clean up expired visual abstracts (older than 30 days).
    
    This function can be called from:
    - A scheduled task (cron job)
    - A background worker
    - An API endpoint for manual triggering
    """
    try:
        async with get_async_session_context() as session:
            # Initialize service (API keys not needed for cleanup)
            visual_abstract_service = VisualAbstractService(
                session=session,
                openai_api_key=None,
                openrouter_api_key=None,
            )
            
            # Clean up expired abstracts
            deleted_count = await visual_abstract_service.cleanup_expired()
            
            logger.info(f"Cleanup completed: {deleted_count} expired visual abstracts deleted")
            return deleted_count
            
    except Exception as e:
        logger.error(f"Failed to cleanup expired visual abstracts: {str(e)}")
        raise


if __name__ == "__main__":
    # Allow running as a standalone script
    asyncio.run(cleanup_expired_visual_abstracts())
