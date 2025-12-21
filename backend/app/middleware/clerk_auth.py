"""
Clerk authentication middleware for FastAPI.
"""
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import User, get_async_session
from app.services.clerk_service import clerk_service
import logging

logger = logging.getLogger(__name__)


security = HTTPBearer(auto_error=False)


async def get_current_user_from_clerk(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_async_session),
) -> Optional[User]:
    """
    Get the current user from Clerk JWT token.
    
    This is an optional dependency - returns None if no token is present.
    Use this for endpoints that can work with or without authentication.
    
    Args:
        credentials: HTTP Bearer credentials
        session: Database session
        
    Returns:
        User or None: The authenticated user, or None if not authenticated
    """
    if not credentials:
        return None
    
    try:
        # Verify the token
        token_claims = await clerk_service.verify_token(credentials.credentials)
        
        # Extract user information from token
        clerk_user_id = token_claims.get('sub')  # Subject is the user ID
        email = token_claims.get('email')
        
        if not clerk_user_id:
            return None
        
        # Get or create user in database
        user = await clerk_service.get_or_create_user(
            session=session,
            clerk_user_id=clerk_user_id,
            email=email,
            first_name=token_claims.get('given_name'),
            last_name=token_claims.get('family_name'),
            profile_image_url=token_claims.get('picture')
        )
        
        return user
        
    except Exception as e:
        # Log the error but don't raise - this is optional auth
        print(f"Error authenticating with Clerk: {str(e)}")
        return None


async def require_clerk_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """
    Require Clerk authentication - raises 401 if not authenticated.
    
    Use this for endpoints that require authentication.
    
    Args:
        credentials: HTTP Bearer credentials
        session: Database session
        
    Returns:
        User: The authenticated user
        
    Raises:
        HTTPException: If not authenticated
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify the token
        token_claims = await clerk_service.verify_token(credentials.credentials)
        
        # Extract user information from token
        clerk_user_id = token_claims.get('sub')  # Subject is the user ID
        email = token_claims.get('email')
        
        if not clerk_user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get or create user in database
        user = await clerk_service.get_or_create_user(
            session=session,
            clerk_user_id=clerk_user_id,
            email=email,
            first_name=token_claims.get('given_name'),
            last_name=token_claims.get('family_name'),
            profile_image_url=token_claims.get('picture')
        )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        # Log full exception server-side, but do not expose internal details to clients
        logger.exception("Error requiring Clerk authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Alias for backwards compatibility with existing code
get_current_clerk_user = require_clerk_auth
