"""
Clerk webhook routes for user synchronization.
"""

import json
import logging
from typing import Optional

from app.config import config
from app.db import get_async_session
from app.services.clerk_service import clerk_service
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/webhooks/clerk")
async def clerk_webhook(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    svix_id: str = Header(None, alias="svix-id"),
    svix_timestamp: str = Header(None, alias="svix-timestamp"),
    svix_signature: str = Header(None, alias="svix-signature"),
):
    """
    Handle Clerk webhook events for user synchronization.

    Clerk sends webhooks for events like:
    - user.created: When a new user signs up
    - user.updated: When user info changes
    - user.deleted: When a user is deleted

    Read more: https://clerk.com/docs/integrations/webhooks
    """
    if not config.CLERK_WEBHOOK_SIGNING_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk webhook signing key not configured",
        )

    # Get the raw body
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    # Ensure required Svix headers are present
    missing_headers = []
    if not svix_id:
        missing_headers.append("svix-id")
    if not svix_timestamp:
        missing_headers.append("svix-timestamp")
    if not svix_signature:
        missing_headers.append("svix-signature")

    if missing_headers:
        missing = ", ".join(missing_headers)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required webhook header: {missing}",
        )

    # Verify the webhook signature
    try:
        wh = Webhook(config.CLERK_WEBHOOK_SIGNING_KEY)
        payload = wh.verify(
            body_str,
            {
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature,
            },
        )
    except WebhookVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook verification failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing webhook: {str(e)}",
        )

    # Parse the event
    event_type = payload.get("type")
    event_data = payload.get("data", {})

    try:
        # Handle user events
        if event_type in ["user.created", "user.updated"]:
            user = await clerk_service.sync_user_from_webhook(
                session=session, event_type=event_type, user_data=event_data
            )
            return {
                "success": True,
                "event_type": event_type,
                "user_id": str(user.id) if user else None,
            }

        elif event_type == "user.deleted":
            await clerk_service.sync_user_from_webhook(
                session=session, event_type=event_type, user_data=event_data
            )
            return {
                "success": True,
                "event_type": event_type,
                "message": "User deleted",
            }

        else:
            # Unknown event type - just acknowledge it
            return {
                "success": True,
                "event_type": event_type,
                "message": "Event received but not processed",
            }

    except (ValueError, json.JSONDecodeError) as e:
        # Permanent/client-side error (bad payload/validation). Rollback and
        # return 200 so Svix/Clerk does not retry.
        try:
            await session.rollback()
        except Exception:
            logger.exception(
                "Failed to rollback DB session after permanent webhook error"
            )

        logger.exception("Permanent error processing Clerk webhook")
        return {
            "success": False,
            "error": str(e),
            "event_type": event_type,
        }

    except Exception:
        # Transient/server error (DB, network, unexpected). Rollback and
        # return 500 so the webhook sender can retry.
        try:
            await session.rollback()
        except Exception:
            logger.exception(
                "Failed to rollback DB session after transient webhook error"
            )

        logger.exception("Transient error processing Clerk webhook")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/webhooks/clerk/test")
async def test_clerk_webhook():
    """Test endpoint to verify Clerk webhook route is accessible."""
    return {"message": "Clerk webhook endpoint is active"}


# Security scheme for debug endpoint
security = HTTPBearer(auto_error=False)


@router.get("/debug/token")
async def debug_token_verification(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    Debug endpoint to test token verification and display token claims.

    This endpoint helps diagnose authentication issues by:
    - Showing whether a token is present
    - Displaying token claims (iss, aud, sub, exp, etc.)
    - Showing verification status
    - Displaying configuration values (issuer, JWKS URL)

    Use this endpoint to verify:
    1. Token is being sent correctly from frontend
    2. Token claims match expected values
    3. Issuer configuration is correct
    """
    debug_info = {
        "token_present": credentials is not None,
        "config": {
            "clerk_issuer": clerk_service.clerk_issuer,
            "clerk_jwks_url": clerk_service.clerk_jwks_url,
            "clerk_audience": clerk_service.clerk_audience,
            "clerk_publishable_key_prefix": (
                clerk_service.clerk_publishable_key[:20] + "..."
                if clerk_service.clerk_publishable_key
                else None
            ),
        },
        "token_info": None,
        "verification_result": None,
        "error": None,
    }

    if not credentials:
        debug_info["error"] = "No Authorization header provided"
        return debug_info

    token = credentials.credentials

    try:
        # Try to decode token without verification first
        import jwt

        unverified_header = jwt.get_unverified_header(token)
        unverified_payload = jwt.decode(token, options={"verify_signature": False})

        debug_info["token_info"] = {
            "header": unverified_header,
            "claims": {
                "iss": unverified_payload.get("iss"),
                "aud": unverified_payload.get("aud"),
                "sub": unverified_payload.get("sub"),
                "email": unverified_payload.get("email"),
                "exp": unverified_payload.get("exp"),
                "iat": unverified_payload.get("iat"),
                "nbf": unverified_payload.get("nbf"),
                "given_name": unverified_payload.get("given_name"),
                "family_name": unverified_payload.get("family_name"),
                "picture": unverified_payload.get("picture"),
            },
            "issuer_match": unverified_payload.get("iss") == clerk_service.clerk_issuer,
            "audience_match": (
                unverified_payload.get("aud") == clerk_service.clerk_audience
                if clerk_service.clerk_audience
                else None
            ),
        }

        # Now try to verify the token
        try:
            verified_claims = await clerk_service.verify_token(token)
            debug_info["verification_result"] = {
                "status": "success",
                "verified_claims": {
                    "sub": verified_claims.get("sub"),
                    "email": verified_claims.get("email"),
                    "iss": verified_claims.get("iss"),
                },
            }
        except HTTPException as e:
            debug_info["verification_result"] = {
                "status": "failed",
                "error": e.detail,
                "status_code": e.status_code,
            }
        except Exception as e:
            debug_info["verification_result"] = {
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    except Exception as e:
        debug_info["error"] = f"Failed to decode token: {str(e)}"
        debug_info["error_type"] = type(e).__name__

    return debug_info
