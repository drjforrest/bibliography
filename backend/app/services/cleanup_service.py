"""
Cleanup service for generated content.

Automatically deletes files older than 30 days to manage storage.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List

logger = logging.getLogger(__name__)


class CleanupService:
    """Service for cleaning up old generated content."""
    
    def __init__(self, base_dir: Path, retention_days: int = 30):
        self.base_dir = base_dir
        self.retention_days = retention_days
        self.cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    def cleanup_old_files(self) -> dict:
        """
        Delete files older than retention period.
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "files_deleted": 0,
            "bytes_freed": 0,
            "errors": []
        }
        
        if not self.base_dir.exists():
            logger.info(f"Base directory {self.base_dir} does not exist yet")
            return stats
        
        # Walk through all subdirectories
        for file_path in self.base_dir.rglob("*"):
            if not file_path.is_file():
                continue
            
            try:
                # Check file modification time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if mtime < self.cutoff_date:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    stats["files_deleted"] += 1
                    stats["bytes_freed"] += file_size
                    logger.info(f"Deleted old file: {file_path} (age: {(datetime.now() - mtime).days} days)")
            
            except Exception as e:
                error_msg = f"Failed to delete {file_path}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
        
        # Log summary
        if stats["files_deleted"] > 0:
            mb_freed = stats["bytes_freed"] / (1024 * 1024)
            logger.info(f"Cleanup complete: {stats['files_deleted']} files deleted, {mb_freed:.2f} MB freed")
        else:
            logger.info("Cleanup complete: No old files found")
        
        return stats


async def run_daily_cleanup(base_dir: Path = None):
    """
    Run cleanup once per day.
    
    This should be called as a background task when the app starts.
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent / "generated"
    
    cleanup_service = CleanupService(base_dir, retention_days=30)
    
    while True:
        try:
            logger.info("Starting daily cleanup of generated content...")
            stats = cleanup_service.cleanup_old_files()
            
            if stats["errors"]:
                logger.warning(f"Cleanup completed with {len(stats['errors'])} errors")
        
        except Exception as e:
            logger.error(f"Cleanup task error: {str(e)}")
        
        # Wait 24 hours
        await asyncio.sleep(24 * 60 * 60)
