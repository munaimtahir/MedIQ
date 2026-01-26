"""Cache-safe headers middleware for CDN compatibility.

Ensures API responses are never cached by CDN/proxy, while allowing
static assets to be cached appropriately.
"""

import os
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set cache-safe headers for API endpoints.
    
    Rules:
    - All /v1/* API endpoints: Cache-Control: no-store
    - Health endpoints (/health, /ready): Cache-Control: no-store
    - All other endpoints: no-store (safe default)
    
    Also adds debug headers:
    - X-Origin: "api"
    - X-Request-ID: (from request state if available)
    - X-App-Version: from GIT_SHA or BUILD_ID env var (if set)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add cache headers to response."""
        response = await call_next(request)

        path = request.url.path

        # Determine if this is an API endpoint
        is_api_endpoint = path.startswith("/v1/") or path.startswith("/api/")
        is_health_endpoint = path in ("/health", "/ready")

        # Set cache headers for API and health endpoints
        if is_api_endpoint or is_health_endpoint:
            # NEVER cache API responses or health checks
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        else:
            # Safe default: no-store for any other endpoint
            # (Next.js will override for static assets)
            response.headers["Cache-Control"] = "no-store"

        # Add debug headers
        response.headers["X-Origin"] = "api"

        # Add request ID if available
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = str(request_id)

        # Add app version if available (from env, no secrets)
        git_sha = os.getenv("GIT_SHA") or os.getenv("BUILD_ID")
        if git_sha:
            # Only include first 8 chars to avoid leaking full commit hash
            # (though commit hashes are not secrets, keeping it short is good practice)
            response.headers["X-App-Version"] = git_sha[:8]

        return response
