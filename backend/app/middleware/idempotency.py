"""Idempotency support for mobile-safe API contracts.

Implements Idempotency-Key header support for POST/PUT/PATCH endpoints.
Stores idempotency records in Redis with TTL.
"""

import hashlib
import json
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.redis_client import get_redis_client
from app.core.logging import get_logger

logger = get_logger(__name__)

# Redis key prefix for idempotency records
IDEMPOTENCY_KEY_PREFIX = "idempotency:"
# TTL for idempotency records (24 hours)
IDEMPOTENCY_TTL_SECONDS = 86400


def compute_payload_hash(body: bytes) -> str:
    """Compute SHA-256 hash of request body for idempotency checks."""
    return hashlib.sha256(body).hexdigest()


class IdempotencyContext:
    """Context for idempotency handling within a request."""
    
    def __init__(
        self,
        key: str | None,
        payload_hash: str | None = None,
        cached_response: dict[str, Any] | None = None,
    ):
        self.key = key
        self.payload_hash = payload_hash
        self.cached_response = cached_response
    
    def has_cached_response(self) -> bool:
        """Check if we have a cached response to return."""
        return self.cached_response is not None


async def check_idempotency_dependency(
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> IdempotencyContext:
    """
    FastAPI dependency to check idempotency.
    
    Returns IdempotencyContext with cached response if found.
    Raises 409 if key reused with different payload.
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(
            ...,
            idempotency: IdempotencyContext = Depends(check_idempotency_dependency)
        ):
            if idempotency.has_cached_response():
                return JSONResponse(**idempotency.cached_response)
            # ... process request ...
            # Store response after processing (see store_idempotency_response)
    """
    # Only check for POST/PUT/PATCH
    if request.method not in ("POST", "PUT", "PATCH"):
        return IdempotencyContext(key=None)
    
    if not idempotency_key:
        return IdempotencyContext(key=None)
    
    redis_client = get_redis_client()
    if not redis_client:
        logger.warning("Idempotency-Key provided but Redis unavailable - skipping idempotency check")
        return IdempotencyContext(key=idempotency_key)
    
    # Read request body (store it for later hashing)
    body = await request.body()
    payload_hash = compute_payload_hash(body)
    
    # Redis key: idempotency:{key}
    redis_key = f"{IDEMPOTENCY_KEY_PREFIX}{idempotency_key}"
    
    try:
        stored_data = redis_client.get(redis_key)
        if stored_data:
            # Parse stored response
            stored = json.loads(stored_data)
            stored_hash = stored.get("payload_hash")
            
            # Check if payload matches
            if stored_hash == payload_hash:
                # Same request - return cached response
                logger.info(f"Idempotency hit for key: {idempotency_key[:8]}...")
                return IdempotencyContext(
                    key=idempotency_key,
                    payload_hash=payload_hash,
                    cached_response={
                        "content": stored.get("response_body"),
                        "status_code": stored.get("status_code", 200),
                        "headers": stored.get("headers", {}),
                    },
                )
            else:
                # Different payload with same key - conflict
                logger.warning(f"Idempotency key conflict: {idempotency_key[:8]}...")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "IDEMPOTENCY_KEY_CONFLICT",
                        "message": "Idempotency-Key was used with a different request payload",
                        "details": {
                            "idempotency_key": idempotency_key[:8] + "...",  # Truncate for security
                        },
                    },
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking idempotency: {e}")
        # Fail open - allow request to proceed
        return IdempotencyContext(key=idempotency_key, payload_hash=payload_hash)
    
    return IdempotencyContext(key=idempotency_key, payload_hash=payload_hash)


async def store_idempotency_response(
    idempotency_context: IdempotencyContext,
    response_body: dict | list | str,
    status_code: int,
    headers: dict[str, str] | None = None,
) -> None:
    """
    Store idempotency response in Redis.
    
    Called after successful request processing to cache the response.
    
    Args:
        idempotency_context: Context from check_idempotency_dependency
        response_body: Response body to cache
        status_code: HTTP status code
        headers: Response headers to cache
    """
    if not idempotency_context.key or not idempotency_context.payload_hash:
        return
    
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    redis_key = f"{IDEMPOTENCY_KEY_PREFIX}{idempotency_context.key}"
    
    try:
        # Serialize response
        if isinstance(response_body, (dict, list)):
            response_json = json.dumps(response_body)
        else:
            response_json = str(response_body)
        
        stored_data = {
            "payload_hash": idempotency_context.payload_hash,
            "response_body": json.loads(response_json) if response_json else response_body,
            "status_code": status_code,
            "headers": headers or {},
        }
        
        # Store with TTL
        redis_client.setex(
            redis_key,
            IDEMPOTENCY_TTL_SECONDS,
            json.dumps(stored_data),
        )
        logger.debug(f"Stored idempotency response for key: {idempotency_context.key[:8]}...")
    except Exception as e:
        logger.error(f"Error storing idempotency response: {e}")
        # Fail silently - idempotency is best-effort
