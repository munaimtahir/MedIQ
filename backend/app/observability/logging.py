"""Structured JSON logging with OpenTelemetry correlation and audit logging."""

import logging
import os
import sys
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.trace import format_trace_id, format_span_id

from app.core.config import settings


# Keys to redact from log fields
REDACTED_KEYS = {
    "password",
    "token",
    "authorization",
    "cookie",
    "set-cookie",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "jwt_secret",
    "client_secret",
    "private_key",
    "api_secret",
}


def redact_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Redact sensitive keys from log data.
    
    Args:
        data: Dictionary to redact
        
    Returns:
        Dictionary with sensitive values redacted
    """
    redacted = {}
    for key, value in data.items():
        key_lower = key.lower()
        # Check if key contains any redacted pattern
        if any(redacted_key in key_lower for redacted_key in REDACTED_KEYS):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive_data(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value
    return redacted


def add_trace_context(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add OpenTelemetry trace context to log events."""
    try:
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid():
            span_context = span.get_span_context()
            event_dict["trace_id"] = format_trace_id(span_context.trace_id)
            event_dict["span_id"] = format_span_id(span_context.span_id)
    except Exception:
        # If trace context is not available, continue without it
        pass
    return event_dict


def setup_structured_logging() -> None:
    """Configure structured JSON logging with OpenTelemetry correlation."""
    # Get log level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Get environment and service name
    env = os.getenv("ENV", "dev")
    service_name = os.getenv("SERVICE_NAME", settings.PROJECT_NAME)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_trace_context,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )
    
    # Disable uvicorn access logs (we'll use our own middleware)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    
    # Set global context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        service_name=service_name,
        environment=env,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def get_audit_logger() -> structlog.BoundLogger:
    """Get audit logger for sensitive actions."""
    return structlog.get_logger("audit")


def audit_log(
    event: str,
    actor_id: str | None = None,
    actor_role: str | None = None,
    action: str | None = None,
    target_id: str | None = None,
    **fields: Any,
) -> None:
    """
    Log an audit event (sensitive actions).
    
    Args:
        event: Event name/type
        actor_id: Actor user ID (UUID/numeric only, no PII)
        actor_role: Actor role
        action: Action performed
        target_id: Target resource ID (UUID/numeric only, no PII)
        **fields: Additional fields (will be redacted)
    """
    logger = get_audit_logger()
    
    # Build audit log data
    audit_data: dict[str, Any] = {
        "event": event,
        "audit": True,
    }
    
    if actor_id:
        audit_data["actor_id"] = actor_id
    if actor_role:
        audit_data["actor_role"] = actor_role
    if action:
        audit_data["action"] = action
    if target_id:
        audit_data["target_id"] = target_id
    
    # Add additional fields (redacted)
    audit_data.update(redact_sensitive_data(fields))
    
    logger.warning(event, **audit_data)
