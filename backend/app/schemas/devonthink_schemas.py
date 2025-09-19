from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID

from app.db import DevonthinkSyncStatus


class DevonthinkRecordBase(BaseModel):
    """Base DEVONthink record information"""
    dt_uuid: str = Field(..., description="DEVONthink UUID")
    name: str = Field(..., description="Record name")
    dt_path: str = Field(..., description="DEVONthink location path")
    kind: str = Field(..., description="Record type (pdf, group, etc.)")
    creation_date: Optional[datetime] = Field(None, description="Creation date")
    modification_date: Optional[datetime] = Field(None, description="Last modification date")
    size: Optional[int] = Field(None, description="File size in bytes")


class DevonthinkRecordProperties(DevonthinkRecordBase):
    """Extended DEVONthink record properties"""
    tags: Optional[List[str]] = Field(default_factory=list, description="Record tags")
    comment: Optional[str] = Field(None, description="Record comment")
    label: Optional[int] = Field(None, description="Record label")
    rating: Optional[int] = Field(None, description="Record rating")
    state: Optional[bool] = Field(None, description="Record state")
    custom_meta_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata fields")


class DevonthinkFolderHierarchy(BaseModel):
    """DEVONthink folder hierarchy representation"""
    dt_uuid: str = Field(..., description="Folder UUID")
    name: str = Field(..., description="Folder name")
    dt_path: str = Field(..., description="Full path")
    parent_uuid: Optional[str] = Field(None, description="Parent folder UUID")
    depth: int = Field(..., description="Depth level in hierarchy")
    children: List['DevonthinkFolderHierarchy'] = Field(default_factory=list, description="Child folders")


class DevonthinkSyncRequest(BaseModel):
    """Request to sync from DEVONthink"""
    database_name: str = Field(default="Reference", description="DEVONthink database name")
    folder_path: Optional[str] = Field(None, description="Specific folder to sync (optional)")
    force_resync: bool = Field(False, description="Force re-sync of existing records")
    search_space_id: int = Field(..., description="Target search space for documents")


class DevonthinkSyncResponse(BaseModel):
    """Response from sync operation"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")
    synced_count: int = Field(0, description="Number of records synced")
    error_count: int = Field(0, description="Number of errors encountered")
    skipped_count: int = Field(0, description="Number of records skipped")
    details: List[str] = Field(default_factory=list, description="Detailed operation log")


class DevonthinkSyncStatus(BaseModel):
    """Current sync status for a record"""
    dt_uuid: str = Field(..., description="DEVONthink UUID")
    local_uuid: UUID = Field(..., description="Local paper UUID")
    dt_path: str = Field(..., description="DEVONthink path")
    sync_status: str = Field(..., description="Current sync status")
    last_sync_date: Optional[datetime] = Field(None, description="Last sync timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class DevonthinkFolderCreate(BaseModel):
    """Create/update DEVONthink folder record"""
    dt_uuid: str = Field(..., description="Folder UUID")
    dt_path: str = Field(..., description="Folder path")
    folder_name: str = Field(..., description="Folder name")
    parent_dt_uuid: Optional[str] = Field(None, description="Parent folder UUID")
    depth_level: int = Field(0, description="Depth in hierarchy")


class DevonthinkMonitorResponse(BaseModel):
    """Response from monitoring operation"""
    changes_detected: int = Field(..., description="Number of changes detected")
    new_records: int = Field(0, description="New records found")
    updated_records: int = Field(0, description="Updated records found")
    deleted_records: int = Field(0, description="Deleted records found")
    last_check: datetime = Field(..., description="Timestamp of last check")


class MCPToolCall(BaseModel):
    """MCP tool call request"""
    tool_name: str = Field(..., description="Name of the MCP tool to call")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class MCPToolResponse(BaseModel):
    """MCP tool call response"""
    success: bool = Field(..., description="Tool call success status")
    result: Dict[str, Any] = Field(default_factory=dict, description="Tool response data")
    error: Optional[str] = Field(None, description="Error message if failed")


# Update forward references
DevonthinkFolderHierarchy.model_rebuild()