"""Security event logging utilities."""

from typing import Any

from fastapi import Request

from app.common.request_id import get_request_id
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_client_ip(request: Request) -> str:
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


def get_user_agent(request: Request) -> str | None:
    """Extract user agent from request."""
    return request.headers.get("User-Agent")


def log_security_event(
    request: Request,
    event_type: str,
    outcome: str,  # "allow", "deny", "degraded"
    reason_code: str | None = None,
    user_id: str | None = None,
    provider: str | None = None,
    **extra_fields: Any,
) -> None:
    """
    Log a security event with structured fields.

    Args:
        request: FastAPI request object
        event_type: Event type (e.g., "auth_login_success", "rate_limited")
        outcome: "allow", "deny", or "degraded"
        reason_code: Error code if outcome is "deny"
        user_id: User ID if known
        provider: OAuth provider if relevant
        **extra_fields: Additional fields to include
    """
    request_id = get_request_id(request)
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    log_data = {
        "event_type": event_type,
        "request_id": request_id,
        "outcome": outcome,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }

    if user_id:
        log_data["user_id"] = user_id
    if provider:
        log_data["provider"] = provider
    if reason_code:
        log_data["reason_code"] = reason_code

    log_data.update(extra_fields)

    # Use appropriate log level based on outcome
    if outcome == "deny":
        logger.warning("Security event: denied", extra=log_data)
    elif outcome == "degraded":
        logger.warning("Security event: degraded", extra=log_data)
    else:
        logger.info("Security event: allowed", extra=log_data)

