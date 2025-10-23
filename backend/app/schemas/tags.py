from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TagBase(BaseModel):
    """Base schema for tag data."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(default="#3B82F6", pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None
    parent_id: Optional[int] = None


class TagCreate(TagBase):
    """Schema for creating a new tag."""
    pass


class TagUpdate(BaseModel):
    """Schema for updating a tag."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None
    parent_id: Optional[int] = None


class TagResponse(TagBase):
    """Response schema for tag data."""
    id: int
    user_id: str
    created_at: datetime
    paper_count: int = 0  # Count of papers with this tag

    class Config:
        from_attributes = True


class TagWithChildren(TagResponse):
    """Response schema for tag with its children."""
    children: List['TagWithChildren'] = []

    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    """Response schema for tag lists."""
    tags: List[TagResponse]
    total: int


class TagHierarchyResponse(BaseModel):
    """Response schema for hierarchical tag tree."""
    tags: List[TagWithChildren]
    total: int


class PaperTagsUpdate(BaseModel):
    """Schema for updating paper tags."""
    tag_ids: List[int]


# Allow forward references for recursive model
TagWithChildren.model_rebuild()
