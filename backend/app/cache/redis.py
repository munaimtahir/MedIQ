"""Redis cache helpers (fail-open).

We deliberately keep this tiny and safe:
- Any Redis error must NOT break endpoint responses.
- Use short, bounded TTLs for user-specific caches.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.core.redis_client import get_redis_client

logger = get_logger(__name__)


def get_json(key: str) -> Any | None:
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if not raw:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning("redis_get_json_failed", extra={"event": "redis_get_json_failed", "key": key, "error": str(e)})
        return None


def set_json(key: str, value: Any, ttl_seconds: int) -> bool:
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.setex(key, int(ttl_seconds), json.dumps(value))
        return True
    except Exception as e:
        logger.warning("redis_set_json_failed", extra={"event": "redis_set_json_failed", "key": key, "error": str(e)})
        return False


def delete(key: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception:
        return


def delete_pattern(pattern: str, max_delete: int = 5000) -> int:
    """Delete keys matching a pattern using SCAN (safe-ish; admin-only paths)."""

    client = get_redis_client()
    if client is None:
        return 0
    deleted = 0
    try:
        pipe = client.pipeline(transaction=False)
        for key in client.scan_iter(match=pattern, count=500):
            pipe.delete(key)
            deleted += 1
            if deleted % 200 == 0:
                pipe.execute()
            if deleted >= max_delete:
                break
        if deleted % 200 != 0:
            pipe.execute()
    except Exception as e:
        logger.warning(
            "redis_delete_pattern_failed",
            extra={"event": "redis_delete_pattern_failed", "pattern": pattern, "error": str(e)},
        )
        return 0
    return deleted

