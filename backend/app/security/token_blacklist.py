"""Redis blacklist for fast token revocation checks."""

from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_redis_client

logger = get_logger(__name__)


def blacklist_session(session_id: str, ttl_seconds: int) -> bool:
    """
    Blacklist a session in Redis for fast revocation checks.
    
    Args:
        session_id: Session UUID as string
        ttl_seconds: TTL in seconds (should be until max refresh token expiry)
    
    Returns:
        True if blacklisted successfully, False if Redis unavailable
    """
    redis_client = get_redis_client()
    if redis_client is None:
        logger.warning(f"Redis unavailable, cannot blacklist session {session_id}")
        return False
    
    try:
        key = f"bl:session:{session_id}"
        redis_client.setex(key, ttl_seconds, "1")
        return True
    except Exception as e:
        logger.error(f"Failed to blacklist session {session_id}: {e}", exc_info=True)
        return False


def is_session_blacklisted(session_id: str) -> bool:
    """
    Check if a session is blacklisted in Redis.
    
    Args:
        session_id: Session UUID as string
    
    Returns:
        True if blacklisted, False if not blacklisted or Redis unavailable
    """
    redis_client = get_redis_client()
    if redis_client is None:
        # If Redis unavailable, fall back to DB checks (caller should handle)
        return False
    
    try:
        key = f"bl:session:{session_id}"
        result = redis_client.get(key)
        return result is not None
    except Exception as e:
        logger.error(f"Failed to check blacklist for session {session_id}: {e}", exc_info=True)
        return False


def blacklist_refresh_token(token_hash: str, ttl_seconds: int) -> bool:
    """
    Blacklist a refresh token hash in Redis (optional, for extra security).
    
    Args:
        token_hash: Hashed refresh token
        ttl_seconds: TTL in seconds
    
    Returns:
        True if blacklisted successfully, False if Redis unavailable
    """
    redis_client = get_redis_client()
    if redis_client is None:
        logger.warning(f"Redis unavailable, cannot blacklist refresh token")
        return False
    
    try:
        key = f"bl:refresh:{token_hash}"
        redis_client.setex(key, ttl_seconds, "1")
        return True
    except Exception as e:
        logger.error(f"Failed to blacklist refresh token: {e}", exc_info=True)
        return False


def is_refresh_token_blacklisted(token_hash: str) -> bool:
    """
    Check if a refresh token hash is blacklisted in Redis.
    
    Args:
        token_hash: Hashed refresh token
    
    Returns:
        True if blacklisted, False if not blacklisted or Redis unavailable
    """
    redis_client = get_redis_client()
    if redis_client is None:
        return False
    
    try:
        key = f"bl:refresh:{token_hash}"
        result = redis_client.get(key)
        return result is not None
    except Exception as e:
        logger.error(f"Failed to check blacklist for refresh token: {e}", exc_info=True)
        return False


def calculate_blacklist_ttl(expires_at: datetime) -> int:
    """
    Calculate TTL for blacklist entry based on token expiry.
    
    Args:
        expires_at: Token expiry datetime
    
    Returns:
        TTL in seconds (at least 1 second, max 7 days)
    """
    now = datetime.now(UTC)
    if expires_at <= now:
        return 1  # Already expired, minimal TTL
    
    delta = expires_at - now
    ttl_seconds = int(delta.total_seconds())
    
    # Cap at 7 days (604800 seconds) to prevent very long-lived keys
    max_ttl = 7 * 24 * 60 * 60
    return min(ttl_seconds, max_ttl)


def batch_blacklist_sessions(session_ids: list[str], ttl_seconds: int) -> int:
    """
    Blacklist multiple sessions in a batch operation.
    
    Args:
        session_ids: List of session UUIDs as strings
        ttl_seconds: TTL in seconds
    
    Returns:
        Number of sessions successfully blacklisted
    """
    redis_client = get_redis_client()
    if redis_client is None:
        logger.warning("Redis unavailable, cannot blacklist sessions")
        return 0
    
    try:
        pipe = redis_client.pipeline()
        for session_id in session_ids:
            key = f"bl:session:{session_id}"
            pipe.setex(key, ttl_seconds, "1")
        pipe.execute()
        return len(session_ids)
    except Exception as e:
        logger.error(f"Failed to batch blacklist sessions: {e}", exc_info=True)
        return 0
