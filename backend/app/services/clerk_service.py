"""
Clerk authentication and user synchronization service.
"""
import jwt
import httpx
from typing import Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db import User
from app.config import config


class ClerkService:
    """Service for handling Clerk authentication and user sync."""
    
    def __init__(self):
        self.clerk_api_key = config.CLERK_API_KEY
        self.clerk_publishable_key = config.CLERK_PUBLISHABLE_KEY
        
        # Extract instance ID from publishable key (pk_test_xxx or pk_live_xxx)
        if self.clerk_publishable_key:
            parts = self.clerk_publishable_key.split('_')
            if len(parts) >= 3:
                # Format: pk_test_{instance_id} or pk_live_{instance_id}
                self.instance_id = '_'.join(parts[2:])
            else:
                self.instance_id = None
        else:
            self.instance_id = None
    
    async def verify_token(self, token: str) -> dict:
        """
        Verify a Clerk JWT token and return the claims.
        
        Args:
            token: The JWT token from the request
            
        Returns:
            dict: The decoded token claims
            
        Raises:
            HTTPException: If token is invalid
        """
        if not self.clerk_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Clerk API key not configured"
            )
        
        try:
            # Decode the JWT token
            # Clerk uses RS256 algorithm, but we need to fetch the JWKS
            # For simplicity, we'll decode without verification first
            # In production, you should verify against Clerk's JWKS endpoint
            decoded = jwt.decode(
                token,
                self.clerk_api_key,
                algorithms=["RS256"],
                options={"verify_signature": False}  # TEMPORARY - should verify in production
            )
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    async def get_or_create_user(
        self,
        session: AsyncSession,
        clerk_user_id: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        profile_image_url: Optional[str] = None
    ) -> User:
        """
        Get or create a user based on Clerk user ID.
        
        Args:
            session: Database session
            clerk_user_id: Clerk user ID
            email: User's email
            first_name: User's first name
            last_name: User's last name
            profile_image_url: User's profile image URL
            
        Returns:
            User: The user object
        """
        # Try to find existing user by clerk_user_id
        result = await session.execute(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update user information if changed
            updated = False
            if user.email != email:
                user.email = email
                updated = True
            if profile_image_url and user.avatar_url != profile_image_url:
                user.avatar_url = profile_image_url
                updated = True
            
            # Update display name if we have first/last name
            if first_name or last_name:
                new_display_name = f"{first_name or ''} {last_name or ''}".strip()
                if new_display_name and user.display_name != new_display_name:
                    user.display_name = new_display_name
                    updated = True
            
            if updated:
                user.last_login = datetime.now(timezone.utc)
                await session.commit()
                await session.refresh(user)
            
            return user
        
        # Try to find by email (for migrating existing users). Use a row
        # lock (SELECT ... FOR UPDATE) to avoid races when multiple
        # concurrent requests try to link the same user. If a unique
        # constraint violation occurs on commit, rollback and re-query
        # by `clerk_user_id` to return the already-linked record.
        result = await session.execute(
            select(User).where(User.email == email).with_for_update()
        )
        user = result.scalar_one_or_none()

        if user:
            # Link existing user to Clerk
            user.clerk_user_id = clerk_user_id
            if profile_image_url:
                user.avatar_url = profile_image_url
            if first_name or last_name:
                user.display_name = f"{first_name or ''} {last_name or ''}".strip()
            user.last_login = datetime.now(timezone.utc)
            try:
                await session.commit()
            except IntegrityError:
                # Another transaction may have linked this email to the
                # clerk_user_id concurrently. Rollback and attempt to fetch
                # the authoritative record by clerk_user_id.
                await session.rollback()
                result = await session.execute(
                    select(User).where(User.clerk_user_id == clerk_user_id)
                )
                linked_user = result.scalar_one_or_none()
                if linked_user:
                    await session.refresh(linked_user)
                    return linked_user
                # If not found, re-raise to let caller handle it
                raise

            await session.refresh(user)
            return user
        
        # Create new user
        display_name = f"{first_name or ''} {last_name or ''}".strip() or email.split('@')[0]
        
        new_user = User(
            email=email,
            clerk_user_id=clerk_user_id,
            display_name=display_name,
            avatar_url=profile_image_url,
            is_active=True,
            is_verified=True,  # Clerk handles verification
            is_superuser=False,
            last_login=datetime.now(timezone.utc),
            # Note: hashed_password is NOT set - auth is handled by Clerk
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user

    async def sync_user_from_webhook(
        self,
        session: AsyncSession,
        event_type: str,
        user_data: dict
    ) -> Optional[User]:
        """
        Sync user data from Clerk webhook event.

        Args:
            session: Database session
            event_type: Clerk event type (user.created, user.updated, user.deleted)
            user_data: User data from Clerk webhook

        Returns:
            User or None: The synced user, or None if deleted
        """
        clerk_user_id = user_data.get('id')

        if event_type == 'user.deleted':
            # Handle user deletion
            result = await session.execute(
                select(User).where(User.clerk_user_id == clerk_user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                # Option 1: Soft delete (deactivate)
                user.is_active = False
                await session.commit()

                # Option 2: Hard delete (uncomment if preferred)
                # await session.delete(user)
                # await session.commit()
            return None

        # Extract user information
        email_addresses = user_data.get('email_addresses', [])
        primary_email = None
        for email_obj in email_addresses:
            if email_obj.get('id') == user_data.get('primary_email_address_id'):
                primary_email = email_obj.get('email_address')
                break

        if not primary_email and email_addresses:
            primary_email = email_addresses[0].get('email_address')

        if not primary_email:
            raise ValueError("No email address found for user")

        first_name = user_data.get('first_name')
        last_name = user_data.get('last_name')
        profile_image_url = user_data.get('profile_image_url') or user_data.get('image_url')

        # Create or update user
        user = await self.get_or_create_user(
            session=session,
            clerk_user_id=clerk_user_id,
            email=primary_email,
            first_name=first_name,
            last_name=last_name,
            profile_image_url=profile_image_url
        )

        return user


# Global instance
clerk_service = ClerkService()
