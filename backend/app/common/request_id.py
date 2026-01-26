"""Request ID middleware and performance tracking."""

import random
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Performance sampling rate (0.0 to 1.0)
PERF_SAMPLE_RATE = float(getattr(settings, "PERF_SAMPLE_RATE", 0.05))  # 5% default


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and track request IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request start
        start_time = time.time()
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
            },
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "latency_ms": elapsed_ms,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        # Calculate latency
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Add request ID to response header
        response.headers["X-Request-ID"] = request_id

        # Extract route name (if available)
        route_name = getattr(request.scope.get("route"), "name", None) or request.url.path

        # Get user info if authenticated
        user_id = None
        user_role = None
        if hasattr(request.state, "user"):
            user_id = str(getattr(request.state.user, "id", None) or "")
            user_role = getattr(request.state.user, "role", None)

        # Log request completion with structured data
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "route": route_name,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": elapsed_ms,
                "user_id": user_id,
                "user_role": user_role,
                "correlation_id": request_id,  # Alias for compatibility
            },
        )

        # Sample performance data (write to DB if enabled)
        if random.random() < PERF_SAMPLE_RATE:
            try:
                _sample_performance(
                    route=route_name,
                    method=request.method,
                    status_code=response.status_code,
                    duration_ms=elapsed_ms,
                    user_role=user_role,
                )
            except Exception as e:
                # Don't fail request if sampling fails
                logger.warning(f"Failed to sample performance: {e}")

        return response


def _sample_performance(
    route: str,
    method: str,
    status_code: int,
    duration_ms: int,
    user_role: str | None,
) -> None:
    """
    Sample performance data to database (async, fire-and-forget).

    Args:
        route: Route name or path
        method: HTTP method
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        user_role: User role if authenticated
    """
    # This will be called asynchronously in background
    # For now, just log - actual DB write can be done via background task
    # TODO: Implement async DB write via background task queue
    pass
