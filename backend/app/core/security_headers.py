"""Security headers middleware."""

from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Always set baseline security headers (override any existing values)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"  # Change to SAMEORIGIN if you need iframes

        # Permissions-Policy (restrictive by default)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=(), interest-cohort=()"
        )

        # Cross-Origin policies
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        # COEP is optional and can break embeds - only enable if you know you need it
        # response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

        # HSTS: Only if explicitly enabled AND in production with HTTPS
        if (
            settings.ENABLE_HSTS
            and settings.ENV == "prod"
            and request.url.scheme == "https"
        ):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # CSP: Only if explicitly enabled (default false to avoid breaking embeds)
        if settings.ENABLE_CSP:
            csp_policy = (
                "default-src 'self'; "
                "img-src 'self' data: https:; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-eval'; "
                "connect-src 'self' https: wss:; "
                "frame-ancestors 'none';"
            )
            response.headers["Content-Security-Policy"] = csp_policy

        return response
