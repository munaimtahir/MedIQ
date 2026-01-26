"""Request-scoped context for performance instrumentation.

We use contextvars so:
- request timing logs can correlate to DB instrumentation (request_id)
- we can compute per-request DB query counts and total DB time
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ============================================================================
# Context variables (request-scoped)
# ============================================================================

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
db_query_count_var: contextvars.ContextVar[int] = contextvars.ContextVar("db_query_count", default=0)
db_total_ms_var: contextvars.ContextVar[float] = contextvars.ContextVar("db_total_ms", default=0.0)
db_top_slow_queries_var: contextvars.ContextVar[list[dict]] = contextvars.ContextVar(
    "db_top_slow_queries", default=[]
)


def get_request_id() -> str | None:
    """Get current request id (if in a request context)."""

    return request_id_var.get()


def reset_db_counters() -> None:
    """Reset per-request DB counters (safe to call at request start)."""

    db_query_count_var.set(0)
    db_total_ms_var.set(0.0)
    db_top_slow_queries_var.set([])


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Ensure request_id exists and initialize instrumentation contextvars."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming or str(uuid.uuid4())

        # Store on request.state for handlers and error middleware
        request.state.request_id = request_id

        # Initialize contextvars
        token_request_id = request_id_var.set(request_id)
        token_db_q = db_query_count_var.set(0)
        token_db_ms = db_total_ms_var.set(0.0)
        token_db_top = db_top_slow_queries_var.set([])

        try:
            return await call_next(request)
        finally:
            # Prevent context leakage across requests
            request_id_var.reset(token_request_id)
            db_query_count_var.reset(token_db_q)
            db_total_ms_var.reset(token_db_ms)
            db_top_slow_queries_var.reset(token_db_top)

