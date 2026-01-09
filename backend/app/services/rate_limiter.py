"""
Rate limiting service for API endpoints.

Tracks per-client request counts within a time window and rejects excess requests.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter that tracks requests per client within a time window.

    For production use with multiple workers, consider upgrading to Redis-based solution.
    """

    def __init__(self, window: timedelta, max_requests: int):
        """
        Initialize rate limiter.

        Args:
            window: Time window for rate limiting
            max_requests: Maximum number of requests allowed per window
        """
        self.window = window
        self.max_requests = max_requests
        # Track request timestamps per client identifier
        self._requests: Dict[str, List[datetime]] = defaultdict(list)
        # Last cleanup time
        self._last_cleanup = datetime.now()

    def _cleanup_old_entries(self):
        """Remove entries older than the rate limit window."""
        cutoff_time = datetime.now() - self.window
        keys_to_remove = []

        for client_id, timestamps in self._requests.items():
            # Filter out timestamps outside the window
            self._requests[client_id] = [ts for ts in timestamps if ts > cutoff_time]
            # Mark empty entries for removal
            if not self._requests[client_id]:
                keys_to_remove.append(client_id)

        # Remove empty entries
        for key in keys_to_remove:
            del self._requests[key]

        self._last_cleanup = datetime.now()

    def check_rate_limit(self, client_id: str) -> Tuple[bool, int, int]:
        """
        Check if a request should be allowed based on rate limits.

        Args:
            client_id: Unique identifier for the client (e.g., user ID)

        Returns:
            Tuple of (allowed, remaining, reset_after_seconds)
            - allowed: True if request should be allowed
            - remaining: Number of requests remaining in current window
            - reset_after_seconds: Seconds until the rate limit window resets
        """
        now = datetime.now()

        # Periodic cleanup (every 5 minutes or when checking)
        if (now - self._last_cleanup).total_seconds() > 300:
            self._cleanup_old_entries()

        # Clean up timestamps outside the window for this client
        cutoff_time = now - self.window
        self._requests[client_id] = [
            ts for ts in self._requests[client_id] if ts > cutoff_time
        ]

        # Check current request count
        current_count = len(self._requests[client_id])

        if current_count >= self.max_requests:
            # Find the oldest request to calculate reset time
            oldest_request = min(self._requests[client_id])
            reset_after = int((oldest_request + self.window - now).total_seconds())
            return False, 0, max(0, reset_after)

        # Add current request
        self._requests[client_id].append(now)
        remaining = self.max_requests - current_count - 1

        # Calculate reset time based on oldest request in current window
        if self._requests[client_id]:
            oldest_request = min(self._requests[client_id])
            reset_after = int((oldest_request + self.window - now).total_seconds())
        else:
            reset_after = int(self.window.total_seconds())

        return True, remaining, reset_after

    def get_status(self, client_id: str) -> Dict:
        """
        Get current rate limit status for a client.

        Args:
            client_id: Unique identifier for the client

        Returns:
            Dictionary with rate limit status information
        """
        now = datetime.now()
        cutoff_time = now - self.window

        # Clean up old entries
        if client_id in self._requests:
            self._requests[client_id] = [
                ts for ts in self._requests[client_id] if ts > cutoff_time
            ]

        current_count = len(self._requests.get(client_id, []) or [])
        remaining = max(0, self.max_requests - current_count)

        if self._requests.get(client_id):
            oldest_request = min(self._requests[client_id])
            reset_after = int((oldest_request + self.window - now).total_seconds())
        else:
            reset_after = int(self.window.total_seconds())

        return {
            "limit": self.max_requests,
            "remaining": remaining,
            "reset_after_seconds": max(0, reset_after),
        }
