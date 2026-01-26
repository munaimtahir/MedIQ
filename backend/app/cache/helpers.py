"""Cache key helpers and invalidation hooks."""

from __future__ import annotations

from datetime import date

from app.cache.redis import delete_pattern


def syllabus_blocks_key(year: str) -> str:
    return f"syllabus:{year}:blocks"


def syllabus_themes_key(block_id: int) -> str:
    return f"syllabus:block:{block_id}:themes"


def revdash_key(user_id: str, day: date) -> str:
    return f"revdash:{user_id}:{day.isoformat()}"


def invalidate_syllabus_cache() -> None:
    # Invalidate broadly (admin mutations are rare; keep invalidation simple and correct).
    delete_pattern("syllabus:*:blocks")
    delete_pattern("syllabus:block:*:themes")

