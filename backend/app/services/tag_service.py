from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import Tag, ScientificPaper, paper_tags
from app.schemas.tags import TagCreate, TagUpdate


class TagService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_tag(self, user_id: str, tag_data: TagCreate) -> Tag:
        """Create a new tag for a user."""
        # Check if parent exists if parent_id is provided
        if tag_data.parent_id:
            parent = await self.get_tag_by_id(tag_data.parent_id, user_id)
            if not parent:
                raise ValueError("Parent tag not found")

        tag = Tag(
            name=tag_data.name,
            description=tag_data.description,
            color=tag_data.color,
            icon=tag_data.icon,
            parent_id=tag_data.parent_id,
            user_id=user_id
        )

        self.session.add(tag)
        await self.session.commit()
        await self.session.refresh(tag)
        return tag

    async def get_tag_by_id(self, tag_id: int, user_id: str) -> Optional[Tag]:
        """Get a tag by ID (only user's own tags)."""
        stmt = select(Tag).where(
            and_(Tag.id == tag_id, Tag.user_id == user_id)
        ).options(selectinload(Tag.children))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_tags(
        self,
        user_id: str,
        parent_id: Optional[int] = None,
        include_children: bool = False
    ) -> List[Tag]:
        """Get all tags for a user, optionally filtered by parent."""
        stmt = select(Tag).where(Tag.user_id == user_id)

        if parent_id is not None:
            stmt = stmt.where(Tag.parent_id == parent_id)
        else:
            # By default, only show top-level tags (no parent)
            stmt = stmt.where(Tag.parent_id.is_(None))

        if include_children:
            stmt = stmt.options(selectinload(Tag.children))

        stmt = stmt.order_by(Tag.name)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_user_tags(self, user_id: str) -> List[Tag]:
        """Get all tags for a user (flat list, including nested)."""
        stmt = select(Tag).where(
            Tag.user_id == user_id
        ).order_by(Tag.name)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_tag_hierarchy(self, user_id: str) -> List[Tag]:
        """Get tags in hierarchical structure (only top-level tags with children loaded)."""
        stmt = select(Tag).where(
            and_(Tag.user_id == user_id, Tag.parent_id.is_(None))
        ).options(selectinload(Tag.children)).order_by(Tag.name)

        result = await self.session.execute(stmt)
        tags = list(result.scalars().all())

        # Recursively load all descendants
        for tag in tags:
            await self._load_tag_descendants(tag)

        return tags

    async def _load_tag_descendants(self, tag: Tag):
        """Recursively load all descendants of a tag."""
        if hasattr(tag, 'children') and tag.children:
            for child in tag.children:
                await self.session.refresh(child, ['children'])
                await self._load_tag_descendants(child)

    async def update_tag(
        self,
        tag_id: int,
        user_id: str,
        update_data: TagUpdate
    ) -> Optional[Tag]:
        """Update a tag."""
        tag = await self.get_tag_by_id(tag_id, user_id)
        if not tag:
            return None

        # Check if new parent exists and is not a descendant
        if update_data.parent_id is not None and update_data.parent_id != tag.parent_id:
            if update_data.parent_id == tag_id:
                raise ValueError("Tag cannot be its own parent")

            new_parent = await self.get_tag_by_id(update_data.parent_id, user_id)
            if not new_parent:
                raise ValueError("Parent tag not found")

            # Check if new parent is a descendant (would create cycle)
            if await self._is_descendant(tag_id, update_data.parent_id):
                raise ValueError("Cannot set a descendant as parent")

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(tag, field, value)

        await self.session.commit()
        await self.session.refresh(tag)
        return tag

    async def _is_descendant(self, ancestor_id: int, potential_descendant_id: int) -> bool:
        """Check if potential_descendant_id is a descendant of ancestor_id."""
        current_tag = await self.session.get(Tag, potential_descendant_id)
        while current_tag and current_tag.parent_id:
            if current_tag.parent_id == ancestor_id:
                return True
            current_tag = await self.session.get(Tag, current_tag.parent_id)
        return False

    async def delete_tag(self, tag_id: int, user_id: str) -> bool:
        """Delete a tag. Child tags will also be deleted due to CASCADE."""
        tag = await self.get_tag_by_id(tag_id, user_id)
        if not tag:
            return False

        await self.session.delete(tag)
        await self.session.commit()
        return True

    async def get_tag_paper_count(self, tag_id: int, user_id: str) -> int:
        """Get count of papers tagged with this tag."""
        tag = await self.get_tag_by_id(tag_id, user_id)
        if not tag:
            return 0

        stmt = select(func.count()).select_from(paper_tags).where(
            paper_tags.c.tag_id == tag_id
        )

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def add_tag_to_paper(
        self,
        paper_id: int,
        tag_id: int,
        user_id: str
    ) -> bool:
        """Add a tag to a paper."""
        # Verify tag belongs to user
        tag = await self.get_tag_by_id(tag_id, user_id)
        if not tag:
            raise ValueError("Tag not found")

        # Verify paper exists
        paper = await self.session.get(ScientificPaper, paper_id)
        if not paper:
            raise ValueError("Paper not found")

        # Check if already tagged
        stmt = select(paper_tags).where(
            and_(
                paper_tags.c.paper_id == paper_id,
                paper_tags.c.tag_id == tag_id
            )
        )
        result = await self.session.execute(stmt)
        if result.first():
            return False  # Already tagged

        # Add tag
        stmt = paper_tags.insert().values(paper_id=paper_id, tag_id=tag_id)
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def remove_tag_from_paper(
        self,
        paper_id: int,
        tag_id: int,
        user_id: str
    ) -> bool:
        """Remove a tag from a paper."""
        # Verify tag belongs to user
        tag = await self.get_tag_by_id(tag_id, user_id)
        if not tag:
            return False

        # Remove tag
        stmt = paper_tags.delete().where(
            and_(
                paper_tags.c.paper_id == paper_id,
                paper_tags.c.tag_id == tag_id
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_paper_tags(self, paper_id: int, user_id: str) -> List[Tag]:
        """Get all tags for a specific paper."""
        stmt = select(Tag).join(
            paper_tags, Tag.id == paper_tags.c.tag_id
        ).where(
            and_(
                paper_tags.c.paper_id == paper_id,
                Tag.user_id == user_id
            )
        ).order_by(Tag.name)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_paper_tags(
        self,
        paper_id: int,
        tag_ids: List[int],
        user_id: str
    ) -> List[Tag]:
        """Set tags for a paper (replaces existing tags)."""
        # Verify paper exists
        paper = await self.session.get(ScientificPaper, paper_id)
        if not paper:
            raise ValueError("Paper not found")

        # Verify all tags belong to user
        if tag_ids:
            stmt = select(Tag).where(
                and_(Tag.id.in_(tag_ids), Tag.user_id == user_id)
            )
            result = await self.session.execute(stmt)
            found_tags = list(result.scalars().all())
            if len(found_tags) != len(tag_ids):
                raise ValueError("One or more tags not found")

        # Remove existing tags
        delete_stmt = paper_tags.delete().where(paper_tags.c.paper_id == paper_id)
        await self.session.execute(delete_stmt)

        # Add new tags
        if tag_ids:
            for tag_id in tag_ids:
                insert_stmt = paper_tags.insert().values(
                    paper_id=paper_id,
                    tag_id=tag_id
                )
                await self.session.execute(insert_stmt)

        await self.session.commit()

        # Return updated tags
        return await self.get_paper_tags(paper_id, user_id)

    async def search_tags(self, user_id: str, query: str, limit: int = 20) -> List[Tag]:
        """Search tags by name."""
        stmt = select(Tag).where(
            and_(
                Tag.user_id == user_id,
                Tag.name.ilike(f"%{query}%")
            )
        ).order_by(Tag.name).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
