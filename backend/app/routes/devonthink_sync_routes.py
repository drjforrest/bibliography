from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from uuid import UUID
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

from app.db import get_async_session, get_async_session_context, DevonthinkSync, DevonthinkFolder, DevonthinkSyncStatus, SearchSpace
from app.schemas.devonthink_schemas import (
    DevonthinkSyncRequest, DevonthinkSyncResponse, DevonthinkSyncStatus as SyncStatusSchema,
    DevonthinkFolderHierarchy, DevonthinkMonitorResponse
)
from app.services.devonthink_sync_service import DevonthinkSyncService
from app.users import current_active_user
from app.db import User

router = APIRouter(tags=["devonthink"])


async def _run_sync_in_background(request: DevonthinkSyncRequest, user_id: UUID):
    """
    Wrapper function to run sync in proper async context for background tasks.
    This creates its own database session to avoid context issues.
    """
    try:
        async with get_async_session_context() as session:
            sync_service = DevonthinkSyncService(session)
            result = await sync_service.sync_database(request, user_id)
            await sync_service.close()
            return result
    except Exception as e:
        logger.error(f"Background sync failed for user {user_id}: {str(e)}")
        raise


@router.get("/health")
async def devonthink_health_check():
    """Health check endpoint for DEVONthink sync functionality."""
    return {"status": "healthy", "service": "devonthink-sync", "endpoints_available": True}


@router.post("/sync-local", response_model=DevonthinkSyncResponse)
async def sync_devonthink_database_local(
    request: DevonthinkSyncRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Local development sync endpoint - NO AUTHENTICATION REQUIRED.
    
    Sync DEVONthink database with bibliography system using hardcoded user ID.
    Only for local development!
    """
    try:
        # Use hardcoded user ID for local development
        USER_ID = UUID("960bc239-c12e-4559-bb86-a5072df1f4a6")
        
        sync_service = DevonthinkSyncService(session)
        
        # For large syncs, run in background
        if request.folder_path is None:  # Full database sync
            background_tasks.add_task(
                _run_sync_in_background, request, USER_ID
            )
            return DevonthinkSyncResponse(
                success=True,
                message=f"Full database sync started in background for user {USER_ID}. Check sync status for progress.",
                details=["Background sync initiated for entire database", f"Using local user ID: {USER_ID}"]
            )
        else:
            # Smaller folder sync can run in foreground
            response = await sync_service.sync_database(request, USER_ID)
            await sync_service.close()
            return response
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/sync", response_model=DevonthinkSyncResponse)
async def sync_devonthink_database(
    request: DevonthinkSyncRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """
    Sync DEVONthink database with bibliography system.
    
    This endpoint initiates a full sync of the specified DEVONthink database,
    preserving the hierarchical folder structure and extracting metadata from PDFs.
    """
    try:
        sync_service = DevonthinkSyncService(session)
        
        # For large syncs, run in background
        if request.folder_path is None:  # Full database sync
            background_tasks.add_task(
                sync_service.sync_database, request, user.id
            )
            return DevonthinkSyncResponse(
                success=True,
                message="Full database sync started in background. Check sync status for progress.",
                details=["Background sync initiated for entire database"]
            )
        else:
            # Smaller folder sync can run in foreground
            response = await sync_service.sync_database(request, user.id)
            await sync_service.close()
            return response
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/sync/status", response_model=List[SyncStatusSchema])
async def get_sync_status(
    limit: int = 100,
    status_filter: DevonthinkSyncStatus = None,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """
    Get current sync status for DEVONthink records.
    
    Returns a list of sync records showing the status of each DEVONthink document
    in the bibliography system.
    """
    try:
        stmt = select(DevonthinkSync).where(DevonthinkSync.user_id == user.id)
        
        if status_filter:
            stmt = stmt.where(DevonthinkSync.sync_status == status_filter)
        
        stmt = stmt.order_by(DevonthinkSync.last_sync_date.desc()).limit(limit)
        
        result = await session.execute(stmt)
        sync_records = result.scalars().all()
        
        return [
            SyncStatusSchema(
                dt_uuid=record.dt_uuid,
                local_uuid=record.local_uuid,
                dt_path=record.dt_path or "",
                sync_status=record.sync_status.value,
                last_sync_date=record.last_sync_date,
                error_message=record.error_message
            )
            for record in sync_records
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


@router.get("/folders", response_model=List[DevonthinkFolderHierarchy])
async def get_folder_hierarchy(
    database_name: str = "Reference",
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """
    Get the DEVONthink folder hierarchy for the user.
    
    Returns the preserved hierarchical structure of folders from DEVONthink,
    allowing navigation of the original organization system.
    """
    try:
        # Get root folders (depth 0)
        stmt = select(DevonthinkFolder).where(
            DevonthinkFolder.user_id == user.id,
            DevonthinkFolder.depth_level == 0
        ).order_by(DevonthinkFolder.folder_name)
        
        result = await session.execute(stmt)
        root_folders = result.scalars().all()
        
        hierarchy = []
        for folder in root_folders:
            folder_hierarchy = await _build_folder_hierarchy(session, folder, user.id)
            hierarchy.append(folder_hierarchy)
        
        return hierarchy
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get folder hierarchy: {str(e)}")


@router.post("/monitor", response_model=DevonthinkMonitorResponse)
async def monitor_devonthink_changes(
    database_name: str = "Reference",
    days: int = 1,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """
    Monitor DEVONthink for recent changes.
    
    Checks for new, modified, or deleted records in DEVONthink since the specified
    number of days ago. Useful for incremental sync operations.
    """
    try:
        sync_service = DevonthinkSyncService(session)
        changes = await sync_service.monitor_changes(database_name, days)
        await sync_service.close()
        
        return DevonthinkMonitorResponse(
            changes_detected=changes["total_changes"],
            new_records=len(changes["new_records"]),
            updated_records=len(changes["updated_records"]),
            deleted_records=0,  # TODO: Implement deletion detection
            last_check=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to monitor changes: {str(e)}")


@router.post("/sync/incremental", response_model=DevonthinkSyncResponse)
async def incremental_sync(
    database_name: str = "Reference",
    days: int = 1,
    search_space_id: int = None,
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """
    Perform incremental sync of recent changes.
    
    Syncs only records that have been modified in DEVONthink within the specified
    number of days. More efficient than full sync for regular updates.
    """
    try:
        if not search_space_id:
            # Get user's default search space
            stmt = select(SearchSpace).where(SearchSpace.user_id == user.id).limit(1)
            result = await session.execute(stmt)
            search_space = result.scalar_one_or_none()
            if not search_space:
                raise HTTPException(status_code=400, detail="No search space found. Please specify search_space_id.")
            search_space_id = search_space.id
        
        sync_service = DevonthinkSyncService(session)
        
        # Monitor for changes first
        changes = await sync_service.monitor_changes(database_name, days)
        
        if changes["total_changes"] == 0:
            await sync_service.close()
            return DevonthinkSyncResponse(
                success=True,
                message="No changes detected in DEVONthink",
                details=["No new or modified records found"]
            )
        
        # Create sync request for incremental sync
        sync_request = DevonthinkSyncRequest(
            database_name=database_name,
            search_space_id=search_space_id,
            force_resync=True  # Force re-sync of modified records
        )
        
        # For small numbers of changes, sync in foreground
        if changes["total_changes"] <= 10:
            response = await sync_service.sync_database(sync_request, user.id)
            await sync_service.close()
            return response
        else:
            # Large changes go to background
            background_tasks.add_task(
                sync_service.sync_database, sync_request, user.id
            )
            await sync_service.close()
            return DevonthinkSyncResponse(
                success=True,
                message=f"Incremental sync started in background. {changes['total_changes']} changes detected.",
                details=[f"Processing {changes['new_records']} new and {changes['updated_records']} updated records"]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Incremental sync failed: {str(e)}")


@router.delete("/sync/{dt_uuid}")
async def remove_sync_record(
    dt_uuid: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """
    Remove a sync record and optionally the associated paper.
    
    This will break the link between DEVONthink and the bibliography system
    for the specified record.
    """
    try:
        # Find the sync record
        stmt = select(DevonthinkSync).where(
            DevonthinkSync.dt_uuid == dt_uuid,
            DevonthinkSync.user_id == user.id
        )
        result = await session.execute(stmt)
        sync_record = result.scalar_one_or_none()
        
        if not sync_record:
            raise HTTPException(status_code=404, detail="Sync record not found")
        
        # Delete the sync record
        await session.delete(sync_record)
        await session.commit()
        
        return {"success": True, "message": "Sync record removed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove sync record: {str(e)}")


@router.get("/stats")
async def get_sync_stats(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """
    Get sync statistics for the user.
    
    Returns counts of synced, pending, and failed records.
    """
    try:
        # Count by status
        stmt = select(
            DevonthinkSync.sync_status,
            func.count(DevonthinkSync.id).label('count')
        ).where(
            DevonthinkSync.user_id == user.id
        ).group_by(DevonthinkSync.sync_status)
        
        result = await session.execute(stmt)
        status_counts = {row.sync_status.value: row.count for row in result}
        
        # Count folders
        folder_stmt = select(func.count(DevonthinkFolder.id)).where(
            DevonthinkFolder.user_id == user.id
        )
        folder_result = await session.execute(folder_stmt)
        folder_count = folder_result.scalar() or 0
        
        return {
            "sync_records": status_counts,
            "total_records": sum(status_counts.values()),
            "folders_mapped": folder_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync stats: {str(e)}")


async def _build_folder_hierarchy(session: AsyncSession, folder: DevonthinkFolder, 
                                user_id: UUID) -> DevonthinkFolderHierarchy:
    """Recursively build folder hierarchy"""
    # Get child folders
    stmt = select(DevonthinkFolder).where(
        DevonthinkFolder.parent_dt_uuid == folder.dt_uuid,
        DevonthinkFolder.user_id == user_id
    ).order_by(DevonthinkFolder.folder_name)
    
    result = await session.execute(stmt)
    child_folders = result.scalars().all()
    
    children = []
    for child in child_folders:
        child_hierarchy = await _build_folder_hierarchy(session, child, user_id)
        children.append(child_hierarchy)
    
    return DevonthinkFolderHierarchy(
        dt_uuid=folder.dt_uuid,
        name=folder.folder_name,
        dt_path=folder.dt_path,
        parent_uuid=folder.parent_dt_uuid,
        depth=folder.depth_level,
        children=children
    )