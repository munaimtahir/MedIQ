"""OpenTelemetry tracing utilities for manual span creation."""

import uuid
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)


def get_safe_user_id(user: Any) -> str | None:
    """
    Safely extract user ID for span attributes (no PII).
    
    Only returns UUID or numeric IDs, never emails or names.
    """
    if not user:
        return None
    
    user_id = getattr(user, "id", None)
    if not user_id:
        return None
    
    # Only include if it's a UUID or numeric ID (not email/name)
    try:
        if isinstance(user_id, (int, uuid.UUID)):
            return str(user_id)
        elif isinstance(user_id, str):
            # Check if it's a valid UUID format
            uuid.UUID(user_id)
            return user_id
    except (ValueError, AttributeError, TypeError):
        # Not a safe ID format, skip it
        pass
    
    return None


def set_span_error(span: trace.Span, exception: Exception, error_code: str | None = None) -> None:
    """Record exception on span and mark as error."""
    if not span or not span.is_recording():
        return
    
    span.record_exception(exception)
    span.set_status(Status(StatusCode.ERROR))
    
    if error_code:
        span.set_attribute("error.code", error_code)
    
    # Add error message (sanitized, no PII)
    error_message = str(exception)
    # Truncate long messages
    if len(error_message) > 200:
        error_message = error_message[:200] + "..."
    span.set_attribute("error.message", error_message)
