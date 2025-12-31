"""Request ID middleware and utilities."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)


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

        # Log request completion
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": elapsed_ms,
            },
        )

        return response

