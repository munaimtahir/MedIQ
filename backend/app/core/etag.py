"""ETag support for content caching (mobile-safe API contracts)."""

import hashlib
from typing import Any

from fastapi import Header, Request, status
from fastapi.responses import Response


def compute_etag(content: str | bytes) -> str:
    """Compute ETag from content (weak ETag with W/ prefix)."""
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    else:
        content_bytes = content
    
    hash_value = hashlib.md5(content_bytes).hexdigest()
    return f'W/"{hash_value}"'


def check_if_none_match(request: Request, etag: str) -> bool:
    """
    Check If-None-Match header against computed ETag.
    
    Returns True if client has matching ETag (should return 304).
    """
    if_none_match = request.headers.get("If-None-Match")
    if not if_none_match:
        return False
    
    # Remove quotes and W/ prefix for comparison
    client_etag = if_none_match.strip().strip('"').replace('W/', '')
    server_etag = etag.strip().strip('"').replace('W/', '')
    
    return client_etag == server_etag


def create_not_modified_response(etag: str) -> Response:
    """Create 304 Not Modified response with ETag header."""
    return Response(
        status_code=status.HTTP_304_NOT_MODIFIED,
        headers={"ETag": etag},
    )
