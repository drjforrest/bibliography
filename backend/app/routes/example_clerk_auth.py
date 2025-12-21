"""
Example routes showing how to use Clerk authentication.

This file demonstrates how to convert existing routes from fastapi-users to Clerk.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import User, get_async_session, ScientificPaper
from app.middleware.clerk_auth import require_clerk_auth, get_current_user_from_clerk


router = APIRouter()


# Example 1: Protected route (requires authentication)
@router.get("/me")
async def get_current_user(
    current_user: User = Depends(require_clerk_auth)
):
    """
    Get the current authenticated user.
    
    BEFORE (with fastapi-users):
    ```python
    from app.users import current_active_user
    
    @router.get("/me")
    async def get_current_user(user: User = Depends(current_active_user)):
        return user
    ```
    
    AFTER (with Clerk):
    ```python
    from app.middleware.clerk_auth import require_clerk_auth
    
    @router.get("/me")
    async def get_current_user(current_user: User = Depends(require_clerk_auth)):
        return current_user
    ```
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "display_name": current_user.display_name,
        "clerk_user_id": current_user.clerk_user_id,
        "is_active": current_user.is_active,
    }


# Example 2: Optional authentication
@router.get("/public-or-private")
async def public_or_private_route(
    current_user: User | None = Depends(get_current_user_from_clerk)
):
    """
    Route that works with or without authentication.
    
    Returns different data based on authentication status.
    """
    if current_user:
        return {
            "message": f"Hello, {current_user.email}!",
            "authenticated": True,
            "user_id": str(current_user.id)
        }
    else:
        return {
            "message": "Hello, guest!",
            "authenticated": False
        }


# Example 3: Route with database operations
@router.get("/my-papers")
async def get_my_papers(
    current_user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get papers for the current user.
    
    This shows how to combine Clerk auth with database queries.
    """
    # Query papers (this is just an example - adjust based on your schema)
    result = await session.execute(
        select(ScientificPaper)
        .limit(10)
    )
    papers = result.scalars().all()
    
    return {
        "user_email": current_user.email,
        "paper_count": len(papers),
        "papers": [
            {
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors
            }
            for paper in papers
        ]
    }


# Example 4: Migration guide for existing routes
"""
MIGRATION GUIDE - How to update your existing routes:

1. REPLACE the import:
   OLD: from app.users import current_active_user
   NEW: from app.middleware.clerk_auth import require_clerk_auth

2. REPLACE the dependency:
   OLD: user: User = Depends(current_active_user)
   NEW: current_user: User = Depends(require_clerk_auth)

3. UPDATE variable names if needed:
   If you used 'user' before, rename to 'current_user' for consistency
   (or keep using 'user' - both work fine)

EXAMPLE CONVERSION:

BEFORE:
```python
from app.users import current_active_user

@router.post("/papers")
async def create_paper(
    paper_data: PaperCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    new_paper = ScientificPaper(
        title=paper_data.title,
        user_id=user.id  # Use the authenticated user's ID
    )
    session.add(new_paper)
    await session.commit()
    return {"id": new_paper.id}
```

AFTER:
```python
from app.middleware.clerk_auth import require_clerk_auth

@router.post("/papers")
async def create_paper(
    paper_data: PaperCreate,
    current_user: User = Depends(require_clerk_auth),
    session: AsyncSession = Depends(get_async_session)
):
    new_paper = ScientificPaper(
        title=paper_data.title,
        user_id=current_user.id  # Use the authenticated user's ID
    )
    session.add(new_paper)
    await session.commit()
    return {"id": new_paper.id}
```

That's it! The User object is the same, so everything else stays the same.
"""
