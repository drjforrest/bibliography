"""
API routes for Automated Ingestion from DEVONthink to Bibliography RAG Pipeline.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session, User
from app.users import current_active_user
from app.services.automated_ingestion_service import get_automated_ingestion_service, AutomatedIngestionService
from app.schemas.devonthink_schemas import DevonthinkSyncResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/automated-ingestion", tags=["Automated Ingestion"])


# Pydantic models for requests/responses
class MonitoringConfigRequest(BaseModel):
    database_name: str = Field("Reference", description="DEVONthink database name")
    search_space_id: Optional[int] = Field(None, description="Target search space ID")
    folder_path: Optional[str] = Field(None, description="Specific folder path to monitor")
    polling_interval_minutes: int = Field(30, description="Polling interval in minutes", ge=5, le=1440)


class MonitoringStatusResponse(BaseModel):
    is_running: bool
    polling_interval_minutes: float
    monitored_databases: int
    database_configs: dict


class HierarchyStatusResponse(BaseModel):
    total_folders: int
    max_depth: int
    folders_by_depth: dict
    sync_status: dict
    folder_tree: list


class FullSyncRequest(BaseModel):
    database_name: str = Field("Reference", description="DEVONthink database name")
    search_space_id: Optional[int] = Field(None, description="Target search space ID")
    folder_path: Optional[str] = Field(None, description="Specific folder path to sync")


@router.get("/health")
async def health_check():
    """Health check for automated ingestion service."""
    return {
        "status": "healthy",
        "service": "Automated Ingestion",
        "description": "DEVONthink to Bibliography RAG Pipeline"
    }


@router.post("/configure-monitoring")
async def configure_monitoring(
    config_request: MonitoringConfigRequest,
    current_user: User = Depends(current_active_user),
    ingestion_service: AutomatedIngestionService = Depends(get_automated_ingestion_service)
):
    """
    Configure automated monitoring for a DEVONthink database.
    
    This will set up continuous monitoring and incremental sync for the specified database,
    preserving hierarchical folder structure and automatically updating the RAG pipeline.
    """
    try:
        # Configure monitoring
        ingestion_service.configure_monitoring(
            user_id=current_user.id,
            database_name=config_request.database_name,
            search_space_id=config_request.search_space_id,
            folder_path=config_request.folder_path
        )
        
        # Update polling interval if specified
        if config_request.polling_interval_minutes != 30:
            ingestion_service.polling_interval = config_request.polling_interval_minutes * 60
        
        return {
            "success": True,
            "message": f"Configured monitoring for database '{config_request.database_name}'",
            "config": {
                "user_id": str(current_user.id),
                "database_name": config_request.database_name,
                "search_space_id": config_request.search_space_id,
                "folder_path": config_request.folder_path,
                "polling_interval_minutes": config_request.polling_interval_minutes
            }
        }
        
    except Exception as e:
        logger.error(f"Error configuring monitoring: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure monitoring: {str(e)}"
        )


@router.post("/start-monitoring")
async def start_monitoring(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(current_active_user),
    ingestion_service: AutomatedIngestionService = Depends(get_automated_ingestion_service)
):
    """
    Start the automated monitoring loop.
    
    This will begin continuous monitoring of configured DEVONthink databases
    and automatically sync changes to the RAG pipeline.
    """
    try:
        if ingestion_service.is_running:
            return {
                "success": False,
                "message": "Monitoring is already running",
                "status": ingestion_service.get_monitoring_status()
            }
        
        # Start monitoring in background
        background_tasks.add_task(ingestion_service.start_monitoring)
        
        return {
            "success": True,
            "message": "Automated monitoring started",
            "status": ingestion_service.get_monitoring_status()
        }
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start monitoring: {str(e)}"
        )


@router.post("/stop-monitoring")
async def stop_monitoring(
    current_user: User = Depends(current_active_user),
    ingestion_service: AutomatedIngestionService = Depends(get_automated_ingestion_service)
):
    """Stop the automated monitoring loop."""
    try:
        if not ingestion_service.is_running:
            return {
                "success": False,
                "message": "Monitoring is not running",
                "status": ingestion_service.get_monitoring_status()
            }
        
        await ingestion_service.stop_monitoring()
        
        return {
            "success": True,
            "message": "Automated monitoring stopped",
            "status": ingestion_service.get_monitoring_status()
        }
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop monitoring: {str(e)}"
        )


@router.get("/status", response_model=MonitoringStatusResponse)
async def get_monitoring_status(
    current_user: User = Depends(current_active_user),
    ingestion_service: AutomatedIngestionService = Depends(get_automated_ingestion_service)
):
    """Get the current status of automated monitoring."""
    try:
        status = ingestion_service.get_monitoring_status()
        return MonitoringStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring status: {str(e)}"
        )


@router.get("/hierarchy-status", response_model=HierarchyStatusResponse)
async def get_hierarchy_status(
    database_name: str = "Reference",
    current_user: User = Depends(current_active_user),
    ingestion_service: AutomatedIngestionService = Depends(get_automated_ingestion_service)
):
    """
    Get the current hierarchical folder structure status for a database.
    
    Returns detailed information about the preserved DEVONthink folder hierarchy.
    """
    try:
        hierarchy_status = await ingestion_service.get_hierarchy_status(
            user_id=current_user.id,
            database_name=database_name
        )
        return HierarchyStatusResponse(**hierarchy_status)
        
    except Exception as e:
        logger.error(f"Error getting hierarchy status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hierarchy status: {str(e)}"
        )


@router.post("/force-full-sync", response_model=DevonthinkSyncResponse)
async def force_full_sync(
    sync_request: FullSyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(current_active_user),
    ingestion_service: AutomatedIngestionService = Depends(get_automated_ingestion_service)
):
    """
    Force a complete full synchronization of a DEVONthink database.
    
    This will sync all papers from the specified database while preserving
    hierarchical structure and rebuilding the RAG pipeline vector store.
    """
    try:
        logger.info(f"Force full sync requested by user {current_user.id} for database {sync_request.database_name}")
        
        # For full database sync, run in background
        if sync_request.folder_path is None:
            background_tasks.add_task(
                ingestion_service.force_full_sync,
                current_user.id,
                sync_request.database_name,
                sync_request.search_space_id,
                sync_request.folder_path
            )
            return DevonthinkSyncResponse(
                success=True,
                message=f"Full database sync started in background for '{sync_request.database_name}'",
                details=["Background sync initiated for entire database", "Check monitoring status for progress"]
            )
        else:
            # Folder sync can run in foreground
            response = await ingestion_service.force_full_sync(
                user_id=current_user.id,
                database_name=sync_request.database_name,
                search_space_id=sync_request.search_space_id,
                folder_path=sync_request.folder_path
            )
            return response
        
    except Exception as e:
        logger.error(f"Error in force full sync: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Full sync failed: {str(e)}"
        )


@router.get("/monitoring-logs")
async def get_monitoring_logs(
    limit: int = 50,
    current_user: User = Depends(current_active_user)
):
    """
    Get recent monitoring logs (placeholder - implement log retrieval as needed).
    """
    # This is a placeholder - you could implement actual log retrieval
    # from your logging system, database, or file-based logs
    return {
        "message": "Monitoring logs endpoint - implement log retrieval as needed",
        "logs": [],
        "note": "Connect to your logging system to retrieve actual monitoring logs"
    }