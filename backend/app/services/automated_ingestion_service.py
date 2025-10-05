"""
Automated Ingestion Service for DEVONthink to Bibliography RAG Pipeline.

This service provides automated, continuous ingestion of research papers from DEVONthink
while preserving the hierarchical group structure and maintaining real-time RAG capabilities.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set
from uuid import UUID
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import (
    DevonthinkSync, DevonthinkFolder, DevonthinkSyncStatus, 
    SearchSpace, User, get_async_session_context
)
from app.services.devonthink_sync_service import DevonthinkSyncService
from app.schemas.devonthink_schemas import DevonthinkSyncRequest

logger = logging.getLogger(__name__)


class AutomatedIngestionService:
    """
    Service for automated, continuous ingestion from DEVONthink to Bibliography RAG pipeline.
    
    Features:
    - Continuous monitoring of DEVONthink databases
    - Hierarchical folder structure preservation
    - Automatic RAG pipeline integration
    - Incremental sync capabilities
    - Error recovery and retry mechanisms
    """
    
    def __init__(self, polling_interval_minutes: int = 30):
        self.polling_interval = polling_interval_minutes * 60  # Convert to seconds
        self.is_running = False
        self.monitored_databases: Dict[str, Dict] = {}
        self._stop_event = asyncio.Event()
    
    def configure_monitoring(self, user_id: UUID, database_name: str = "Reference", 
                           search_space_id: int = None, folder_path: str = None):
        """
        Configure automatic monitoring for a DEVONthink database.
        
        Args:
            user_id: User ID for the sync
            database_name: Name of DEVONthink database to monitor
            search_space_id: Target search space ID
            folder_path: Specific folder path to monitor (optional)
        """
        monitor_key = f"{user_id}:{database_name}"
        
        self.monitored_databases[monitor_key] = {
            "user_id": user_id,
            "database_name": database_name,
            "search_space_id": search_space_id,
            "folder_path": folder_path,
            "last_check": None,
            "error_count": 0,
            "last_error": None
        }
        
        logger.info(f"Configured monitoring for {monitor_key}")
    
    async def start_monitoring(self):
        """Start the automated monitoring loop."""
        if self.is_running:
            logger.warning("Monitoring already running")
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        logger.info(f"Starting automated ingestion monitoring (interval: {self.polling_interval}s)")
        
        while self.is_running and not self._stop_event.is_set():
            try:
                await self._monitoring_cycle()
                
                # Wait for next cycle or stop signal
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.polling_interval)
                    break  # Stop event was set
                except asyncio.TimeoutError:
                    continue  # Timeout - continue to next cycle
                    
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
        
        self.is_running = False
        logger.info("Automated ingestion monitoring stopped")
    
    async def stop_monitoring(self):
        """Stop the automated monitoring loop."""
        if not self.is_running:
            return
        
        logger.info("Stopping automated ingestion monitoring")
        self._stop_event.set()
        
        # Wait for monitoring to actually stop
        timeout = 30  # seconds
        for _ in range(timeout):
            if not self.is_running:
                break
            await asyncio.sleep(1)
        
        if self.is_running:
            logger.warning("Monitoring did not stop gracefully within timeout")
    
    async def _monitoring_cycle(self):
        """Execute one monitoring cycle for all configured databases."""
        if not self.monitored_databases:
            logger.debug("No databases configured for monitoring")
            return
        
        logger.info(f"Starting monitoring cycle for {len(self.monitored_databases)} databases")
        
        for monitor_key, config in self.monitored_databases.items():
            try:
                await self._check_database_changes(monitor_key, config)
            except Exception as e:
                config["error_count"] += 1
                config["last_error"] = str(e)
                logger.error(f"Error checking {monitor_key}: {str(e)}")
    
    async def _check_database_changes(self, monitor_key: str, config: Dict):
        """Check for changes in a specific database and sync if needed."""
        user_id = config["user_id"]
        database_name = config["database_name"]
        
        logger.debug(f"Checking changes for {monitor_key}")
        
        async with get_async_session_context() as session:
            sync_service = DevonthinkSyncService(session)
            
            try:
                # Monitor for recent changes (last 24 hours or since last check)
                hours_to_check = 24
                if config["last_check"]:
                    hours_since_check = (datetime.now(timezone.utc) - config["last_check"]).total_seconds() / 3600
                    hours_to_check = max(1, int(hours_since_check) + 1)  # Add buffer
                
                changes = await sync_service.monitor_changes(database_name, days=hours_to_check/24)
                
                # Check if there are any new or updated records
                total_changes = len(changes.get("new_records", [])) + len(changes.get("updated_records", []))
                
                if total_changes > 0:
                    logger.info(f"Found {total_changes} changes in {monitor_key}, starting incremental sync")
                    
                    # Perform incremental sync for changed records
                    await self._incremental_sync(session, config, changes)
                    
                    config["error_count"] = 0  # Reset error count on success
                    config["last_error"] = None
                else:
                    logger.debug(f"No changes found in {monitor_key}")
                
                config["last_check"] = datetime.now(timezone.utc)
                
            except Exception as e:
                logger.error(f"Error monitoring {monitor_key}: {str(e)}")
                raise
            finally:
                await sync_service.close()
    
    async def _incremental_sync(self, session: AsyncSession, config: Dict, changes: Dict):
        """Perform incremental sync for changed records."""
        user_id = config["user_id"]
        database_name = config["database_name"]
        search_space_id = config["search_space_id"]
        
        sync_service = DevonthinkSyncService(session)
        
        # Sync new records
        new_records = changes.get("new_records", [])
        if new_records:
            logger.info(f"Syncing {len(new_records)} new records")
            for record in new_records:
                try:
                    await sync_service._sync_single_record(
                        record, database_name, user_id, search_space_id, force_resync=False
                    )
                    logger.debug(f"Synced new record: {record.get('name', 'Unknown')}")
                except Exception as e:
                    logger.error(f"Failed to sync new record {record.get('uuid', 'Unknown')}: {str(e)}")
        
        # Sync updated records
        updated_records = changes.get("updated_records", [])
        if updated_records:
            logger.info(f"Re-syncing {len(updated_records)} updated records")
            for record in updated_records:
                try:
                    await sync_service._sync_single_record(
                        record, database_name, user_id, search_space_id, force_resync=True
                    )
                    logger.debug(f"Re-synced updated record: {record.get('name', 'Unknown')}")
                except Exception as e:
                    logger.error(f"Failed to re-sync updated record {record.get('uuid', 'Unknown')}: {str(e)}")
        
        # Rebuild FAISS vector store if we had changes
        if new_records or updated_records:
            try:
                logger.info("Rebuilding Enhanced RAG vector store after incremental sync")
                rebuilt_success = await sync_service.enhanced_rag.build_vector_store_from_papers(
                    user_id=str(user_id), search_space_id=search_space_id
                )
                if rebuilt_success:
                    stats = sync_service.enhanced_rag.get_stats()
                    logger.info(f"Rebuilt FAISS vector store with {stats.get('documents_indexed', 0)} documents")
                else:
                    logger.warning("Failed to rebuild FAISS vector store after incremental sync")
            except Exception as e:
                logger.error(f"Error rebuilding FAISS vector store: {str(e)}")
    
    async def force_full_sync(self, user_id: UUID, database_name: str = "Reference", 
                             search_space_id: int = None, folder_path: str = None):
        """
        Force a full synchronization of a DEVONthink database.
        
        Args:
            user_id: User ID for the sync
            database_name: Name of DEVONthink database
            search_space_id: Target search space ID
            folder_path: Specific folder path to sync (optional)
        """
        logger.info(f"Starting forced full sync for user {user_id}, database {database_name}")
        
        async with get_async_session_context() as session:
            sync_service = DevonthinkSyncService(session)
            
            try:
                request = DevonthinkSyncRequest(
                    database_name=database_name,
                    search_space_id=search_space_id,
                    folder_path=folder_path,
                    force_resync=True
                )
                
                response = await sync_service.sync_database(request, user_id)
                
                # Update monitoring config if this database is being monitored
                monitor_key = f"{user_id}:{database_name}"
                if monitor_key in self.monitored_databases:
                    self.monitored_databases[monitor_key]["last_check"] = datetime.now(timezone.utc)
                    self.monitored_databases[monitor_key]["error_count"] = 0
                    self.monitored_databases[monitor_key]["last_error"] = None
                
                return response
                
            finally:
                await sync_service.close()
    
    def get_monitoring_status(self) -> Dict:
        """Get current monitoring status."""
        return {
            "is_running": self.is_running,
            "polling_interval_minutes": self.polling_interval / 60,
            "monitored_databases": len(self.monitored_databases),
            "database_configs": {
                key: {
                    "database_name": config["database_name"],
                    "last_check": config["last_check"].isoformat() if config["last_check"] else None,
                    "error_count": config["error_count"],
                    "last_error": config["last_error"]
                }
                for key, config in self.monitored_databases.items()
            }
        }
    
    async def get_hierarchy_status(self, user_id: UUID, database_name: str = "Reference") -> Dict:
        """
        Get the current hierarchical folder structure status for a database.
        
        Returns:
            Dictionary with folder hierarchy statistics and structure
        """
        async with get_async_session_context() as session:
            # Get folder hierarchy from database
            stmt = select(DevonthinkFolder).where(
                DevonthinkFolder.user_id == user_id
            ).order_by(DevonthinkFolder.depth_level, DevonthinkFolder.folder_name)
            
            result = await session.execute(stmt)
            folders = result.scalars().all()
            
            # Build hierarchy statistics
            hierarchy_stats = {
                "total_folders": len(folders),
                "max_depth": max((f.depth_level for f in folders), default=0),
                "folders_by_depth": {},
                "sync_status": {"synced": 0, "pending": 0, "error": 0},
                "folder_tree": self._build_folder_tree(folders)
            }
            
            # Count folders by depth and sync status
            for folder in folders:
                depth = folder.depth_level
                if depth not in hierarchy_stats["folders_by_depth"]:
                    hierarchy_stats["folders_by_depth"][depth] = 0
                hierarchy_stats["folders_by_depth"][depth] += 1
                
                # Count sync status
                status = folder.sync_status.value if folder.sync_status else "unknown"
                if status in hierarchy_stats["sync_status"]:
                    hierarchy_stats["sync_status"][status] += 1
            
            return hierarchy_stats
    
    def _build_folder_tree(self, folders: List) -> List[Dict]:
        """Build a nested folder tree structure."""
        folder_dict = {f.dt_uuid: f for f in folders}
        tree = []
        
        def build_children(parent_uuid: Optional[str]) -> List[Dict]:
            children = []
            for folder in folders:
                if folder.parent_dt_uuid == parent_uuid:
                    folder_node = {
                        "uuid": folder.dt_uuid,
                        "name": folder.folder_name,
                        "path": folder.dt_path,
                        "depth": folder.depth_level,
                        "sync_status": folder.sync_status.value if folder.sync_status else "unknown",
                        "last_sync": folder.last_sync_date.isoformat() if folder.last_sync_date else None,
                        "children": build_children(folder.dt_uuid)
                    }
                    children.append(folder_node)
            return children
        
        # Start with root folders (no parent)
        return build_children(None)


# Global instance for the automated ingestion service
automated_ingestion_service = AutomatedIngestionService()


async def get_automated_ingestion_service() -> AutomatedIngestionService:
    """Get the global automated ingestion service instance."""
    return automated_ingestion_service