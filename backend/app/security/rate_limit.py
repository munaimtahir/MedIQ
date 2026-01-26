"""Enhanced Redis-backed rate limiting framework."""

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Request, status

from app.core.app_exceptions import raise_app_error
from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_redis_client
from app.core.security_logging import log_security_event

logger = get_logger(__name__)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    reset_at: int  # Unix timestamp when the window resets
    retry_after: int  # Seconds until retry is allowed


def _normalize_email(email: str) -> str:
    """Normalize email for use in keys (lowercase, trimmed)."""
    return email.lower().strip()


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    if request.client:
        return request.client.host
    # Check for forwarded headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return "unknown"


def _check_rate_limit(
    scope: str,
    identifier: str,
    max_requests: int,
    window_seconds: int,
    fail_open: bool = False,
) -> RateLimitResult:
    """
    Check rate limit using Redis with atomic INCR + EXPIRE.

    Key format: rl:{scope}:{identifier}:{window_seconds}

    Args:
        scope: Rate limit scope (e.g., "login", "signup")
        identifier: Unique identifier (IP, user_id, email)
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        fail_open: If True, allow requests when Redis is unavailable

    Returns:
        RateLimitResult with allowed status, remaining count, reset time, and retry_after
    """
    redis_client = get_redis_client()

    # Handle Redis unavailability
    if redis_client is None:
        if fail_open:
            logger.warning(
                f"Redis unavailable for rate limit {scope}:{identifier}, failing open",
                extra={"scope": scope, "identifier": identifier},
            )
            return RateLimitResult(
                allowed=True,
                remaining=max_requests,
                reset_at=0,
                retry_after=window_seconds,
            )
        # For auth endpoints, fail-open but log warning
        logger.warning(
            f"Redis unavailable for rate limit {scope}:{identifier}, failing open with warning",
            extra={"scope": scope, "identifier": identifier},
        )
        return RateLimitResult(
            allowed=True,
            remaining=max_requests,
            reset_at=0,
            retry_after=window_seconds,
        )

    # Build key: rl:{scope}:{identifier}:{window_seconds}
    key = f"rl:{scope}:{identifier}:{window_seconds}"

    try:
        # Atomic operation: INCR + EXPIRE in pipeline
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = pipe.execute()

        current_count = results[0]
        ttl = redis_client.ttl(key)

        # Calculate reset time (current time + TTL)
        import time

        reset_at = int(time.time()) + max(ttl, window_seconds)
        retry_after = max(ttl, 0)

        if current_count > max_requests:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                retry_after=retry_after,
            )

        remaining = max(0, max_requests - current_count)
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=0,
        )

    except Exception as e:
        logger.error(
            f"Rate limit check failed for {scope}:{identifier}: {e}",
            exc_info=True,
            extra={"scope": scope, "identifier": identifier},
        )
        # On error, fail-open
        if fail_open:
            return RateLimitResult(
                allowed=True,
                remaining=max_requests,
                reset_at=0,
                retry_after=window_seconds,
            )
        # For auth endpoints, fail-open but log warning
        logger.warning(
            f"Rate limit error for {scope}:{identifier}, failing open",
            extra={"scope": scope, "identifier": identifier},
        )
        return RateLimitResult(
            allowed=True,
            remaining=max_requests,
            reset_at=0,
            retry_after=window_seconds,
        )


def limit_by_ip(
    route_key: str, max_requests: int, window_seconds: int, fail_open: bool = False
) -> Callable:
    """
    Create a rate limit dependency by IP address.

    Args:
        route_key: Route identifier (e.g., "login", "signup")
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        fail_open: If True, allow requests when Redis is unavailable

    Returns:
        FastAPI dependency function
    """

    def dependency(request: Request) -> None:
        ip = _get_client_ip(request)
        scope = f"{route_key}:ip"
        result = _check_rate_limit(scope, ip, max_requests, window_seconds, fail_open)

        if not result.allowed:
            log_security_event(
                request,
                event_type=f"rate_limited_{route_key}_ip",
                outcome="deny",
                reason_code="RATE_LIMITED",
            )
            raise_app_error(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code="RATE_LIMITED",
                message="Too many requests. Try again later.",
                details={"retry_after_seconds": result.retry_after},
            )

    return dependency


def limit_by_user(
    route_key: str, max_requests: int, window_seconds: int, fail_open: bool = False
) -> Callable:
    """
    Create a rate limit dependency by user ID.

    This can be used as a dependency that requires get_current_user, or called directly
    with (user_id, request).

    Args:
        route_key: Route identifier (e.g., "sessions", "submit")
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        fail_open: If True, allow requests when Redis is unavailable

    Returns:
        Function that can be used as dependency or called with (user_id, request)
    """

    def check(user_id: str | None, request: Request) -> None:
        if user_id is None:
            # Try to get from request state (set by auth middleware)
            user_id = getattr(request.state, "user_id", None)
            if user_id is None:
                logger.warning(
                    f"Rate limit by user for {route_key} but no user_id available"
                )
                # Fail-open if user_id not available
                return

        scope = f"{route_key}:user"
        result = _check_rate_limit(scope, str(user_id), max_requests, window_seconds, fail_open)

        if not result.allowed:
            log_security_event(
                request,
                event_type=f"rate_limited_{route_key}_user",
                outcome="deny",
                reason_code="RATE_LIMITED",
                user_id=str(user_id),
            )
            raise_app_error(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code="RATE_LIMITED",
                message="Too many requests. Try again later.",
                details={"retry_after_seconds": result.retry_after},
            )

    return check


def limit_by_email(
    route_key: str, max_requests: int, window_seconds: int, fail_open: bool = False
) -> Callable:
    """
    Create a rate limit dependency by email (normalized to lowercase).

    This returns a function that can be called with (email, request) inside endpoints,
    or used as a dependency if email is available from another dependency.

    Args:
        route_key: Route identifier (e.g., "login", "reset")
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        fail_open: If True, allow requests when Redis is unavailable

    Returns:
        Function that takes (email: str, request: Request) and raises on limit
    """

    def check(email: str, request: Request) -> None:
        email_normalized = _normalize_email(email)
        scope = f"{route_key}:email"
        result = _check_rate_limit(
            scope, email_normalized, max_requests, window_seconds, fail_open
        )

        if not result.allowed:
            log_security_event(
                request,
                event_type=f"rate_limited_{route_key}_email",
                outcome="deny",
                reason_code="RATE_LIMITED",
            )
            raise_app_error(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code="RATE_LIMITED",
                message="Too many requests. Try again later.",
                details={"retry_after_seconds": result.retry_after},
            )

    return check


# Policy configuration
# These can be overridden via environment variables
RATE_LIMIT_POLICIES = {
    # Auth endpoints
    "auth.login": {
        "ip": {"max_requests": 5, "window_seconds": 60},  # 5/min per IP
        "email": {"max_requests": 10, "window_seconds": 60},  # 10/min per email
    },
    "auth.signup": {
        "ip": {"max_requests": 3, "window_seconds": 60},  # 3/min per IP
    },
    "auth.password_reset_request": {
        "ip": {"max_requests": 3, "window_seconds": 60},  # 3/min per IP
        "email": {"max_requests": 3, "window_seconds": 60},  # 3/min per email
    },
    "auth.password_reset_confirm": {
        "ip": {"max_requests": 10, "window_seconds": 60},  # 10/min per IP
    },
    # Admin dangerous endpoints
    "admin.runtime_switch": {
        "user": {"max_requests": 10, "window_seconds": 3600},  # 10/hour per admin user
    },
    "admin.email_drain": {
        "user": {"max_requests": 20, "window_seconds": 3600},  # 20/hour per admin user
    },
    "admin.notifications_broadcast": {
        "user": {"max_requests": 30, "window_seconds": 3600},  # 30/hour per admin user
    },
    # Student sessions (light)
    "sessions.create": {
        "user": {"max_requests": 10, "window_seconds": 60},  # 10/min per user
    },
    "sessions.submit": {
        "user": {"max_requests": 10, "window_seconds": 60},  # 10/min per user
    },
    # Security endpoints
    "security.csp_report": {
        "ip": {"max_requests": 100, "window_seconds": 60},  # 100/min per IP (CSP reports can be frequent)
    },
}


def get_rate_limit_policy(route_key: str) -> dict:
    """Get rate limit policy for a route."""
    return RATE_LIMIT_POLICIES.get(route_key, {})


# Convenience functions for common patterns
def rate_limit_ip(route_key: str, fail_open: bool = False) -> Callable:
    """Get IP-based rate limit dependency for a route."""
    policy = get_rate_limit_policy(route_key)
    ip_policy = policy.get("ip", {})
    if not ip_policy:
        # Return no-op dependency if no policy
        return lambda request: None
    return limit_by_ip(
        route_key, ip_policy["max_requests"], ip_policy["window_seconds"], fail_open
    )


def rate_limit_email(route_key: str, fail_open: bool = False) -> Callable:
    """
    Get email-based rate limit function for a route.
    
    Usage in endpoint:
        check_email_limit = rate_limit_email("auth.login")
        check_email_limit(request_data.email, request)
    """
    policy = get_rate_limit_policy(route_key)
    email_policy = policy.get("email", {})
    if not email_policy:
        # Return no-op function if no policy
        return lambda email, request: None
    return limit_by_email(
        route_key, email_policy["max_requests"], email_policy["window_seconds"], fail_open
    )


def create_user_rate_limit_dep(route_key: str, fail_open: bool = False):
    """
    Create a FastAPI dependency for user-based rate limiting.
    
    This dependency explicitly depends on get_current_user, so it will run after
    authentication. When used in dependencies=[Depends(...)], it will ensure
    get_current_user runs first.
    
    Usage:
        @router.post(
            "/endpoint",
            dependencies=[Depends(create_user_rate_limit_dep("sessions.create"))],
        )
        async def endpoint(
            current_user: User = Depends(get_current_user),
            ...
        ):
            ...
    
    Note: The dependency internally depends on get_current_user, so it will run
    after authentication even when used in the dependencies list.
    """
    from app.core.dependencies import get_current_user
    from fastapi import Depends
    
    policy = get_rate_limit_policy(route_key)
    user_policy = policy.get("user", {})
    if not user_policy:
        # Return no-op dependency if no policy
        def noop() -> None:
            pass
        return noop
    
    max_requests = user_policy["max_requests"]
    window_seconds = user_policy["window_seconds"]
    
    def dependency(
        current_user=Depends(get_current_user),
        request: Request = None,
    ) -> None:
        """Rate limit dependency that depends on get_current_user."""
        user_id = str(current_user.id)
        scope = f"{route_key}:user"
        result = _check_rate_limit(scope, user_id, max_requests, window_seconds, fail_open)
        
        if not result.allowed:
            log_security_event(
                request,
                event_type=f"rate_limited_{route_key}_user",
                outcome="deny",
                reason_code="RATE_LIMITED",
                user_id=user_id,
            )
            raise_app_error(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code="RATE_LIMITED",
                message="Too many requests. Try again later.",
                details={"retry_after_seconds": result.retry_after},
            )
    
    return dependency


def rate_limit_user(route_key: str, fail_open: bool = False) -> Callable:
    """Get user-based rate limit dependency for a route."""
    policy = get_rate_limit_policy(route_key)
    user_policy = policy.get("user", {})
    if not user_policy:
        # Return no-op dependency if no policy
        return lambda request: None
    return limit_by_user(
        route_key, user_policy["max_requests"], user_policy["window_seconds"], fail_open
    )
