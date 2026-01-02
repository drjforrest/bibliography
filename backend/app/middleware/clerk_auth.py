"""
Clerk authentication middleware for FastAPI.
"""

import logging
from typing import Optional

from app.db import User, get_async_session
from app.services.clerk_service import clerk_service
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

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
        clerk_user_id = token_claims.get("sub")  # Subject is the user ID
        email = token_claims.get("email")

        if not clerk_user_id:
            return None

        # Get or create user in database
        user = await clerk_service.get_or_create_user(
            session=session,
            clerk_user_id=clerk_user_id,
            email=email,
            first_name=token_claims.get("first_name")
            or token_claims.get("given_name"),  # Support both naming conventions
            last_name=token_claims.get("last_name")
            or token_claims.get("family_name"),  # Support both naming conventions
            profile_image_url=token_claims.get("picture"),
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
        logger.warning("Authentication required but no credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    logger.debug(f"Received token (first 20 chars): {token[:20]}...")

    try:
        # Verify the token
        token_claims = await clerk_service.verify_token(token)

        # Extract user information from token
        clerk_user_id = token_claims.get("sub")  # Subject is the user ID
        email = token_claims.get("email")  # Email may not always be in token

        logger.debug(
            f"Token verified. User ID: {clerk_user_id}, Email: {email or '(not in token)'}"
        )

        if not clerk_user_id:
            # Log only safe identifiers to avoid PII exposure
            claim_keys = list(token_claims.keys()) if token_claims else []
            jti = token_claims.get("jti") if token_claims else None
            safe_info = f"claim_keys={claim_keys}"
            if jti:
                safe_info += f", jti={jti}"
            logger.error(f"Invalid token claims: missing sub. {safe_info}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: missing sub",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get or create user in database
        # Email should always be present in Clerk JWT tokens (configured in JWT template)
        # If missing, get_or_create_user will raise ValueError indicating configuration issue
        logger.debug(f"Getting or creating user: {clerk_user_id}")
        user = await clerk_service.get_or_create_user(
            session=session,
            clerk_user_id=clerk_user_id,
            email=email,  # Required - should be present in JWT token
            first_name=token_claims.get("first_name")
            or token_claims.get("given_name"),  # Support both naming conventions
            last_name=token_claims.get("last_name")
            or token_claims.get("family_name"),  # Support both naming conventions
            profile_image_url=token_claims.get("picture"),
        )

        logger.debug(f"User retrieved: {user.id}, active: {user.is_active}")

        if not user.is_active:
            logger.warning(
                f"User {clerk_user_id} attempted access but account is inactive"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
            )

        logger.info(f"User {clerk_user_id} authenticated successfully")
        return user

    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes)
        raise
    except Exception as e:
        # Log full exception server-side, but do not expose internal details to clients
        logger.exception(
            f"Error requiring Clerk authentication: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Alias for backwards compatibility with existing code
get_current_clerk_user = require_clerk_auth
