"""
Clerk authentication and user synchronization service.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiohttp
import jwt
from app.config import config
from app.db import User
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ClerkService:
    """Service for handling Clerk authentication and user sync."""

    def __init__(self):
        self.clerk_api_key = config.CLERK_API_KEY
        self.clerk_publishable_key = config.CLERK_PUBLISHABLE_KEY
        self.clerk_issuer = config.CLERK_ISSUER
        self.clerk_jwks_url = config.CLERK_JWKS_URL
        self.clerk_audience = getattr(config, "CLERK_AUDIENCE", None)
        self._jwks_cache: Optional[Dict[str, Any]] = None

        # Extract instance ID from publishable key (pk_test_xxx or pk_live_xxx)
        if self.clerk_publishable_key:
            parts = self.clerk_publishable_key.split("_")
            if len(parts) >= 3:
                # Format: pk_test_{instance_id} or pk_live_{instance_id}
                self.instance_id = "_".join(parts[2:])
            else:
                self.instance_id = None
        else:
            self.instance_id = None

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Clerk endpoint (with caching)."""
        if self._jwks_cache is None:
            timeout = aiohttp.ClientTimeout(total=10.0)
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(self.clerk_jwks_url) as response:
                        response.raise_for_status()
                        self._jwks_cache = await response.json()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to fetch JWKS: {str(e)}",
                )
        return self._jwks_cache

    async def verify_token(self, token: str) -> dict:
        """
        Verify a Clerk JWT token using JWKS and return the claims.

        Args:
            token: The JWT token from the request

        Returns:
            dict: The decoded token claims

        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Get unverified header to extract key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            logger.debug(f"Token header: {unverified_header}")
            logger.debug(f"Token key ID (kid): {kid}")

            if not kid:
                logger.error("Token missing key ID (kid)")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing key ID (kid)",
                )

            # Fetch JWKS
            logger.debug(f"Fetching JWKS from: {self.clerk_jwks_url}")
            jwks = await self._fetch_jwks()
            logger.debug(f"JWKS contains {len(jwks.get('keys', []))} keys")

            # Find the matching key
            public_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # Convert JWK to RSA public key
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    logger.debug(f"Found matching key for kid: {kid}")
                    break

            if not public_key:
                available_kids = [k.get("kid") for k in jwks.get("keys", [])]
                logger.error(
                    f"Key not found in JWKS. Looking for kid: {kid}, "
                    f"Available kids: {available_kids}"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Key not found in JWKS for kid: {kid}",
                )

            # Decode token without verification first to inspect claims
            try:
                unverified_payload = jwt.decode(
                    token, options={"verify_signature": False}
                )
                logger.debug(f"Token claims (unverified): {unverified_payload}")
                logger.debug(
                    f"Token issuer (iss): {unverified_payload.get('iss')}, "
                    f"Expected: {self.clerk_issuer}"
                )
                logger.debug(f"Token audience (aud): {unverified_payload.get('aud')}")
                logger.debug(f"Token subject (sub): {unverified_payload.get('sub')}")
                logger.debug(f"Token expiration (exp): {unverified_payload.get('exp')}")
            except Exception as decode_error:
                logger.warning(f"Could not decode token for inspection: {decode_error}")

            # Verify and decode token
            verify_options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
            }

            # Add audience verification if configured
            decode_kwargs = {
                "algorithms": ["RS256"],
                "issuer": self.clerk_issuer,
                "options": verify_options,
            }

            if self.clerk_audience:
                decode_kwargs["audience"] = self.clerk_audience
                verify_options["verify_aud"] = True
                logger.debug(
                    f"Verifying token with issuer: {self.clerk_issuer}, "
                    f"audience: {self.clerk_audience}, algorithms: ['RS256']"
                )
            else:
                logger.debug(
                    f"Verifying token with issuer: {self.clerk_issuer}, "
                    f"algorithms: ['RS256'] (no audience verification)"
                )

            decoded = jwt.decode(
                token,
                public_key,
                **decode_kwargs,
            )

            logger.info(f"Token verified successfully for user: {decoded.get('sub')}")
            return decoded

        except jwt.ExpiredSignatureError as e:
            logger.error(f"Token has expired: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.InvalidIssuerError as e:
            logger.error(
                f"Invalid token issuer. Expected: {self.clerk_issuer}, Error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token issuer. Expected: {self.clerk_issuer}",
            )
        except jwt.InvalidAudienceError as e:
            logger.error(
                f"Invalid token audience. Expected: {self.clerk_audience}, Error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token audience. Expected: {self.clerk_audience}",
            )
        except jwt.InvalidTokenError as e:
            # Log the actual error for debugging
            logger.error(f"Clerk JWT verification failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            )
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            # Catch any other exceptions and log them
            logger.error(
                f"Unexpected error during Clerk JWT verification: {str(e)}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}",
            )

    async def get_or_create_user(
        self,
        session: AsyncSession,
        clerk_user_id: str,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        profile_image_url: Optional[str] = None,
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
            # If email is missing from token but user exists, log warning (configuration issue)
            # but continue using existing user's email
            if not email:
                logger.warning(
                    f"Email missing from Clerk token for existing user {clerk_user_id}. "
                    f"Using existing email from database: {user.email}. "
                    f"Please configure JWT template to include email field."
                )
            elif email and user.email != email:
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

        # Try to find by email (for migrating existing users) if email is provided
        # Use a row lock (SELECT ... FOR UPDATE) to avoid races when multiple
        # concurrent requests try to link the same user. If a unique
        # constraint violation occurs on commit, rollback and re-query
        # by `clerk_user_id` to return the already-linked record.
        if email:
            result = await session.execute(
                select(User).where(User.email == email).with_for_update()
            )
            user = result.scalar_one_or_none()
        else:
            user = None

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
        # Email should always be present in Clerk JWT tokens (configured in JWT template)
        # If missing, this indicates a configuration issue that should be fixed
        if not email:
            logger.error(
                f"Email missing from Clerk token for user {clerk_user_id}. "
                f"This indicates the JWT template is not configured correctly. "
                f"Please ensure the JWT template includes: {{'email': '{{{{user.primary_email_address}}}}'}}"
            )
            raise ValueError(
                f"Email is required but missing from Clerk token for user {clerk_user_id}. "
                f"Please configure the Clerk JWT template to include the email field. "
                f"See docs/CLERK_JWT_TEMPLATE_REQUIREMENTS.md for details."
            )

        display_name = (
            f"{first_name or ''} {last_name or ''}".strip() or email.split("@")[0]
        )

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

        try:
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            return new_user
        except IntegrityError:
            # Another transaction may have created a user with the same
            # clerk_user_id or email concurrently. Rollback and attempt to
            # fetch the existing record.
            await session.rollback()

            # Try to find by clerk_user_id first (primary identifier)
            result = await session.execute(
                select(User).where(User.clerk_user_id == clerk_user_id)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                await session.refresh(existing_user)
                return existing_user

            # If not found by clerk_user_id, try by email
            result = await session.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                await session.refresh(existing_user)
                return existing_user

            # If still not found, raise HTTP conflict error
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User creation failed due to constraint violation. "
                f"Unable to locate existing user with clerk_user_id={clerk_user_id} or email={email}",
            )

    async def sync_user_from_webhook(
        self, session: AsyncSession, event_type: str, user_data: dict
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
        clerk_user_id = user_data.get("id")

        if event_type == "user.deleted":
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
        email_addresses = user_data.get("email_addresses", [])
        primary_email = None
        for email_obj in email_addresses:
            if email_obj.get("id") == user_data.get("primary_email_address_id"):
                primary_email = email_obj.get("email_address")
                break

        if not primary_email and email_addresses:
            primary_email = email_addresses[0].get("email_address")

        if not primary_email:
            raise ValueError("No email address found for user")

        first_name = user_data.get("first_name")
        last_name = user_data.get("last_name")
        profile_image_url = user_data.get("profile_image_url") or user_data.get(
            "image_url"
        )

        # Create or update user
        user = await self.get_or_create_user(
            session=session,
            clerk_user_id=clerk_user_id,
            email=primary_email,
            first_name=first_name,
            last_name=last_name,
            profile_image_url=profile_image_url,
        )

        return user


# Global instance
clerk_service = ClerkService()
