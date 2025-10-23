from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db import get_async_session, User
from app.services.tag_service import TagService
from app.users import current_active_user
from app.schemas.tags import (
    TagCreate,
    TagUpdate,
    TagResponse,
    TagWithChildren,
    TagListResponse,
    TagHierarchyResponse,
    PaperTagsUpdate,
)

router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/", response_model=TagResponse, status_code=201)
async def create_tag(
    tag_data: TagCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new tag."""
    tag_service = TagService(session)

    try:
        tag = await tag_service.create_tag(str(user.id), tag_data)

        # Get paper count
        paper_count = await tag_service.get_tag_paper_count(tag.id, str(user.id))

        response = TagResponse.from_orm(tag)
        response.paper_count = paper_count
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=TagListResponse)
async def get_tags(
    parent_id: Optional[int] = Query(None, description="Filter by parent tag ID"),
    flat: bool = Query(False, description="Return flat list of all tags"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get user's tags.
    - By default, returns only top-level tags (no parent)
    - Use ?parent_id=X to get children of a specific tag
    - Use ?flat=true to get all tags in a flat list
    """
    tag_service = TagService(session)

    if flat:
        tags = await tag_service.get_all_user_tags(str(user.id))
    else:
        tags = await tag_service.get_user_tags(str(user.id), parent_id=parent_id)

    # Add paper counts
    tag_responses = []
    for tag in tags:
        paper_count = await tag_service.get_tag_paper_count(tag.id, str(user.id))
        tag_response = TagResponse.from_orm(tag)
        tag_response.paper_count = paper_count
        tag_responses.append(tag_response)

    return TagListResponse(tags=tag_responses, total=len(tag_responses))


@router.get("/hierarchy", response_model=TagHierarchyResponse)
async def get_tag_hierarchy(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get tags in hierarchical tree structure with all children loaded."""
    tag_service = TagService(session)
    tags = await tag_service.get_tag_hierarchy(str(user.id))

    # Build response with children
    def build_tag_tree(tag) -> TagWithChildren:
        paper_count = 0  # Would need to calculate recursively
        response = TagWithChildren(
            id=tag.id,
            name=tag.name,
            description=tag.description,
            color=tag.color,
            icon=tag.icon,
            parent_id=tag.parent_id,
            user_id=str(tag.user_id),
            created_at=tag.created_at,
            paper_count=paper_count,
            children=[]
        )

        if hasattr(tag, 'children') and tag.children:
            response.children = [build_tag_tree(child) for child in tag.children]

        return response

    tag_tree = [build_tag_tree(tag) for tag in tags]
    return TagHierarchyResponse(tags=tag_tree, total=len(tags))


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific tag by ID."""
    tag_service = TagService(session)
    tag = await tag_service.get_tag_by_id(tag_id, str(user.id))

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    paper_count = await tag_service.get_tag_paper_count(tag_id, str(user.id))
    response = TagResponse.from_orm(tag)
    response.paper_count = paper_count
    return response


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    update_data: TagUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update a tag."""
    tag_service = TagService(session)

    try:
        tag = await tag_service.update_tag(tag_id, str(user.id), update_data)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        paper_count = await tag_service.get_tag_paper_count(tag_id, str(user.id))
        response = TagResponse.from_orm(tag)
        response.paper_count = paper_count
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a tag. Child tags will also be deleted."""
    tag_service = TagService(session)

    success = await tag_service.delete_tag(tag_id, str(user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found")

    return {"message": "Tag deleted successfully", "tag_id": tag_id}


@router.get("/search/query", response_model=TagListResponse)
async def search_tags(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Search tags by name."""
    tag_service = TagService(session)
    tags = await tag_service.search_tags(str(user.id), q, limit)

    # Add paper counts
    tag_responses = []
    for tag in tags:
        paper_count = await tag_service.get_tag_paper_count(tag.id, str(user.id))
        tag_response = TagResponse.from_orm(tag)
        tag_response.paper_count = paper_count
        tag_responses.append(tag_response)

    return TagListResponse(tags=tag_responses, total=len(tag_responses))


# Paper-Tag relationship endpoints
@router.get("/{tag_id}/papers")
async def get_papers_by_tag(
    tag_id: int,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get all papers tagged with a specific tag."""
    from sqlalchemy import select
    from app.db import ScientificPaper, paper_tags
    from app.schemas.papers import PaperResponse

    tag_service = TagService(session)

    # Verify tag exists and belongs to user
    tag = await tag_service.get_tag_by_id(tag_id, str(user.id))
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Get papers
    stmt = (
        select(ScientificPaper)
        .join(paper_tags, ScientificPaper.id == paper_tags.c.paper_id)
        .where(paper_tags.c.tag_id == tag_id)
        .order_by(ScientificPaper.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(stmt)
    papers = result.scalars().all()

    return {
        "papers": [PaperResponse.from_orm(paper) for paper in papers],
        "tag": TagResponse.from_orm(tag),
        "total": len(papers),
        "limit": limit,
        "offset": offset,
    }


@router.post("/papers/{paper_id}/tags/{tag_id}")
async def add_tag_to_paper(
    paper_id: int,
    tag_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Add a tag to a paper."""
    tag_service = TagService(session)

    try:
        success = await tag_service.add_tag_to_paper(paper_id, tag_id, str(user.id))
        if not success:
            return {"message": "Tag already applied to paper", "paper_id": paper_id, "tag_id": tag_id}

        return {"message": "Tag added successfully", "paper_id": paper_id, "tag_id": tag_id}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/papers/{paper_id}/tags/{tag_id}")
async def remove_tag_from_paper(
    paper_id: int,
    tag_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Remove a tag from a paper."""
    tag_service = TagService(session)

    success = await tag_service.remove_tag_from_paper(paper_id, tag_id, str(user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Tag or paper not found")

    return {"message": "Tag removed successfully", "paper_id": paper_id, "tag_id": tag_id}


@router.get("/papers/{paper_id}/tags", response_model=TagListResponse)
async def get_paper_tags(
    paper_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get all tags for a specific paper."""
    tag_service = TagService(session)
    tags = await tag_service.get_paper_tags(paper_id, str(user.id))

    # Add paper counts
    tag_responses = []
    for tag in tags:
        paper_count = await tag_service.get_tag_paper_count(tag.id, str(user.id))
        tag_response = TagResponse.from_orm(tag)
        tag_response.paper_count = paper_count
        tag_responses.append(tag_response)

    return TagListResponse(tags=tag_responses, total=len(tag_responses))


@router.put("/papers/{paper_id}/tags", response_model=TagListResponse)
async def set_paper_tags(
    paper_id: int,
    tags_update: PaperTagsUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Set tags for a paper (replaces all existing tags)."""
    tag_service = TagService(session)

    try:
        tags = await tag_service.set_paper_tags(paper_id, tags_update.tag_ids, str(user.id))

        # Add paper counts
        tag_responses = []
        for tag in tags:
            paper_count = await tag_service.get_tag_paper_count(tag.id, str(user.id))
            tag_response = TagResponse.from_orm(tag)
            tag_response.paper_count = paper_count
            tag_responses.append(tag_response)

        return TagListResponse(tags=tag_responses, total=len(tag_responses))

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
