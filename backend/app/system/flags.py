"""System flags accessor with caching for non-blocking reads."""

import logging
import threading
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.system_flags import SystemFlag

logger = logging.getLogger(__name__)

# Per-process cache (thread-safe)
_cache_lock = threading.Lock()
_cache: dict[str, dict] = {
    "EXAM_MODE": {
        "value": False,
        "last_checked_at": None,
        "updated_at": None,
        "updated_by": None,
        "reason": None,
    },
    "FREEZE_UPDATES": {
        "value": False,
        "last_checked_at": None,
        "updated_at": None,
        "updated_by": None,
        "reason": None,
    },
}

# Cache TTL in seconds (configurable via env, default 10s)
CACHE_TTL_SECONDS = int(getattr(settings, "SYSTEM_FLAGS_CACHE_TTL_SECONDS", 10))


def _is_cache_fresh(key: str) -> bool:
    """Check if cache entry is still fresh (within TTL)."""
    with _cache_lock:
        entry = _cache.get(key)
        if not entry or not entry.get("last_checked_at"):
            return False
        age = (datetime.utcnow() - entry["last_checked_at"]).total_seconds()
        return age < CACHE_TTL_SECONDS


def _get_from_db(db: Session, key: str) -> SystemFlag | None:
    """Read flag from database (non-blocking, may fail)."""
    try:
        return db.query(SystemFlag).filter(SystemFlag.key == key).first()
    except Exception as e:
        logger.warning(f"Failed to read system flag {key} from DB: {e}")
        return None


def _update_cache(key: str, flag: SystemFlag | None, source: Literal["db", "fallback"]) -> bool:
    """Update cache with new value. Returns True if value changed."""
    with _cache_lock:
        old_value = _cache.get(key, {}).get("value", False)
        new_value = flag.value if flag else False
        
        _cache[key] = {
            "value": new_value,
            "last_checked_at": datetime.utcnow(),
            "updated_at": flag.updated_at if flag else None,
            "updated_by": flag.updated_by if flag else None,
            "reason": flag.reason if flag else None,
            "source": source,
        }
        
        return old_value != new_value


def is_exam_mode(db: Session | None = None) -> bool:
    """
    Check if exam mode is enabled (cached, non-blocking).
    Uses in-memory cache with TTL; falls back to last known value if DB fails.
    Never raises.
    """
    return _get_flag_cached("EXAM_MODE", db)


def get_exam_mode_state(db: Session | None = None) -> dict:
    """
    Get detailed exam mode state including metadata.
    
    Returns:
        {
            "enabled": bool,
            "updated_at": str | None,
            "updated_by": str | None,
            "reason": str | None,
            "source": "db" | "cache" | "fallback"
        }
    """
    key = "EXAM_MODE"
    
    # Try to refresh from DB if cache expired
    if db is not None and not _is_cache_fresh(key):
        flag = _get_from_db(db, key)
        if flag is not None:
            _update_cache(key, flag, "db")
    
    with _cache_lock:
        entry = _cache.get(key, {})
        return {
            "enabled": entry.get("value", False),
            "updated_at": entry.get("updated_at").isoformat() if entry.get("updated_at") else None,
            "updated_by": str(entry.get("updated_by")) if entry.get("updated_by") else None,
            "reason": entry.get("reason"),
            "source": entry.get("source", "fallback"),
        }


def refresh_exam_mode_cache(db: Session) -> bool:
    """
    Force refresh exam mode cache from database.
    
    Call this after toggling exam mode to ensure immediate consistency.
    
    Args:
        db: Database session
    
    Returns:
        True if value changed, False otherwise
    """
    key = "EXAM_MODE"
    flag = _get_from_db(db, key)
    return _update_cache(key, flag, "db")


def get_flag(db: Session, key: str) -> SystemFlag | None:
    """Get system flag by key (direct DB read, no cache)."""
    return db.query(SystemFlag).filter(SystemFlag.key == key).first()


def set_flag(
    db: Session,
    key: str,
    value: bool,
    updated_by: str | None = None,
    reason: str | None = None,
) -> SystemFlag:
    """
    Set system flag value.
    
    Args:
        db: Database session
        key: Flag key (e.g., "EXAM_MODE")
        value: New value
        updated_by: User ID who made the change
        reason: Reason for the change
    
    Returns:
        Updated SystemFlag
    """
    flag = db.query(SystemFlag).filter(SystemFlag.key == key).first()
    
    if flag:
        flag.value = value
        flag.updated_by = updated_by
        flag.reason = reason
        flag.updated_at = datetime.utcnow()
    else:
        flag = SystemFlag(
            key=key,
            value=value,
            updated_by=updated_by,
            reason=reason,
        )
        db.add(flag)
    
    db.commit()
    db.refresh(flag)
    
    # Force cache refresh for immediate consistency
    if key == "EXAM_MODE":
        refresh_exam_mode_cache(db)
    elif key == "FREEZE_UPDATES":
        refresh_freeze_updates_cache(db)

    return flag


def _get_flag_cached(key: str, db: Session | None) -> bool:
    """Generic cached flag read (EXAM_MODE, FREEZE_UPDATES)."""
    if _is_cache_fresh(key):
        with _cache_lock:
            return _cache[key]["value"]
    if db is not None:
        flag = _get_from_db(db, key)
        if flag is not None:
            _update_cache(key, flag, "db")
            return flag.value
        logger.warning(f"DB read failed for {key}, using cached value")
    with _cache_lock:
        return _cache.get(key, {}).get("value", False)


def is_freeze_updates(db: Session | None = None) -> bool:
    """
    Check if freeze updates is enabled (cached, non-blocking).
    When true, learning state mutations are blocked; decision reads allowed.
    """
    return _get_flag_cached("FREEZE_UPDATES", db)


def get_freeze_updates_state(db: Session | None = None) -> dict:
    """Get detailed freeze-updates state (enabled, updated_at, updated_by, reason, source)."""
    key = "FREEZE_UPDATES"
    if db is not None and not _is_cache_fresh(key):
        flag = _get_from_db(db, key)
        if flag is not None:
            _update_cache(key, flag, "db")
    with _cache_lock:
        entry = _cache.get(key, {})
        return {
            "enabled": entry.get("value", False),
            "updated_at": entry.get("updated_at").isoformat() if entry.get("updated_at") else None,
            "updated_by": str(entry.get("updated_by")) if entry.get("updated_by") else None,
            "reason": entry.get("reason"),
            "source": entry.get("source", "fallback"),
        }


def refresh_freeze_updates_cache(db: Session) -> bool:
    """Force refresh freeze-updates cache from database."""
    key = "FREEZE_UPDATES"
    flag = _get_from_db(db, key)
    return _update_cache(key, flag, "db")
