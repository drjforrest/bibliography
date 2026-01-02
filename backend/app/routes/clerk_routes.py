"""
Clerk webhook routes for user synchronization.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError
import json
import logging

from app.db import get_async_session
from app.services.clerk_service import clerk_service
from app.config import config


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
            detail="Clerk webhook signing key not configured"
        )
    
    # Get the raw body
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    # Ensure required Svix headers are present
    missing_headers = []
    if not svix_id:
        missing_headers.append('svix-id')
    if not svix_timestamp:
        missing_headers.append('svix-timestamp')
    if not svix_signature:
        missing_headers.append('svix-signature')

    if missing_headers:
        missing = ', '.join(missing_headers)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required webhook header: {missing}"
        )
    
    # Verify the webhook signature
    try:
        wh = Webhook(config.CLERK_WEBHOOK_SIGNING_KEY)
        payload = wh.verify(body_str, {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        })
    except WebhookVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook verification failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing webhook: {str(e)}"
        )
    
    # Parse the event
    event_type = payload.get("type")
    event_data = payload.get("data", {})
    
    try:
        # Handle user events
        if event_type in ["user.created", "user.updated"]:
            user = await clerk_service.sync_user_from_webhook(
                session=session,
                event_type=event_type,
                user_data=event_data
            )
            return {
                "success": True,
                "event_type": event_type,
                "user_id": str(user.id) if user else None
            }
        
        elif event_type == "user.deleted":
            await clerk_service.sync_user_from_webhook(
                session=session,
                event_type=event_type,
                user_data=event_data
            )
            return {
                "success": True,
                "event_type": event_type,
                "message": "User deleted"
            }
        
        else:
            # Unknown event type - just acknowledge it
            return {
                "success": True,
                "event_type": event_type,
                "message": "Event received but not processed"
            }
    
    except (ValueError, json.JSONDecodeError) as e:
        # Permanent/client-side error (bad payload/validation). Rollback and
        # return 200 so Svix/Clerk does not retry.
        try:
            await session.rollback()
        except Exception:
            logger.exception("Failed to rollback DB session after permanent webhook error")

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
            logger.exception("Failed to rollback DB session after transient webhook error")

        logger.exception("Transient error processing Clerk webhook")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/webhooks/clerk/test")
async def test_clerk_webhook():
    """Test endpoint to verify Clerk webhook route is accessible."""
    return {
        "message": "Clerk webhook endpoint is active"
    }
