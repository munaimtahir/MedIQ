"""Rate limiting utilities using Redis."""

from typing import Tuple

from fastapi import Request, status

from app.core.app_exceptions import raise_app_error
from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_redis_client
from app.core.security_logging import log_security_event

logger = get_logger(__name__)


def rate_limit(key: str, limit: int, window_seconds: int) -> Tuple[bool, int, int]:
    """
    Check rate limit using Redis.

    Args:
        key: Redis key for the rate limit counter
        limit: Maximum number of requests allowed
        window_seconds: Time window in seconds

    Returns:
        Tuple of (allowed: bool, remaining: int, reset_seconds: int)
    """
    redis_client = get_redis_client()
    if redis_client is None:
        # If Redis is unavailable and not required, allow the request
        if not settings.REDIS_REQUIRED:
            return True, limit, window_seconds
        # If Redis is required but unavailable, deny (shouldn't happen if startup checks work)
        logger.error("Redis unavailable but required for rate limiting")
        return False, 0, window_seconds

    try:
        # Get current count
        current = redis_client.get(key)
        if current is None:
            # First request in window
            redis_client.setex(key, window_seconds, 1)
            return True, limit - 1, window_seconds

        count = int(current)
        if count >= limit:
            # Rate limit exceeded
            ttl = redis_client.ttl(key)
            return False, 0, max(ttl, 0)

        # Increment counter
        new_count = redis_client.incr(key)
        if new_count == 1:
            # Set expiry on first increment (in case key was created without expiry)
            redis_client.expire(key, window_seconds)

        remaining = max(0, limit - new_count)
        ttl = redis_client.ttl(key)
        return True, remaining, max(ttl, 0)

    except Exception as e:
        logger.error(f"Rate limit check failed: {e}", exc_info=True)
        # On error, if Redis is required, deny. Otherwise allow.
        if settings.REDIS_REQUIRED:
            return False, 0, window_seconds
        return True, limit, window_seconds


def check_rate_limit_and_raise(
    key: str, limit: int, window_seconds: int, request: Request, event_type: str = "rate_limited"
) -> None:
    """
    Check rate limit and raise HTTPException if exceeded.

    Args:
        key: Redis key for the rate limit counter
        limit: Maximum number of requests allowed
        window_seconds: Time window in seconds
        request: FastAPI request object
        event_type: Event type for logging
    """
    allowed, remaining, reset_seconds = rate_limit(key, limit, window_seconds)

    if not allowed:
        # Log security event
        log_security_event(
            request,
            event_type=event_type,
            outcome="deny",
            reason_code="RATE_LIMITED",
        )

        # Raise 429 with error envelope
        # Note: Retry-After header should be set by middleware or response handler
        # For now, include it in details
        raise_app_error(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMITED",
            message="Rate limit exceeded. Please try again later.",
            details={"retry_after_seconds": reset_seconds},
        )


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    if request.client:
        return request.client.host
    # Check for forwarded headers (X-Forwarded-For, X-Real-IP)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return "unknown"


def normalize_email_for_key(email: str) -> str:
    """Normalize email for use in Redis keys."""
    return email.lower().strip()

