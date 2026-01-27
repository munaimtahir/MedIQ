"""Redis-based distributed locking for concurrency control."""

from contextlib import contextmanager
from typing import Generator

from app.core.redis_client import get_redis_client
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default lock TTL (5 seconds - enough for refresh operation)
DEFAULT_LOCK_TTL = 5


@contextmanager
def redis_lock(lock_key: str, ttl_seconds: int = DEFAULT_LOCK_TTL) -> Generator[bool, None, None]:
    """
    Acquire a Redis lock with automatic release.
    
    Usage:
        with redis_lock("refresh:token_hash") as acquired:
            if acquired:
                # Critical section
                pass
            else:
                # Lock not acquired
                pass
    
    Args:
        lock_key: Redis key for the lock
        ttl_seconds: Lock TTL in seconds (auto-releases after this time)
    
    Yields:
        True if lock acquired, False otherwise
    """
    redis_client = get_redis_client()
    acquired = False
    
    if not redis_client:
        # Redis unavailable - fail open (allow operation)
        logger.warning(f"Redis unavailable, cannot acquire lock: {lock_key}")
        yield True  # Fail open
        return
    
    try:
        # Try to acquire lock (SET NX EX - set if not exists with expiry)
        # Returns True if key was set (lock acquired), False if key exists (lock held)
        acquired = redis_client.set(
            lock_key,
            "1",
            nx=True,  # Only set if not exists
            ex=ttl_seconds,  # Expire after TTL
        )
        
        if acquired:
            logger.debug(f"Acquired lock: {lock_key}")
        else:
            logger.debug(f"Lock already held: {lock_key}")
        
        yield acquired
    except Exception as e:
        logger.error(f"Error acquiring/releasing lock {lock_key}: {e}")
        # Fail open - allow operation to proceed
        yield True
    finally:
        # Release lock if we acquired it
        if acquired and redis_client:
            try:
                redis_client.delete(lock_key)
                logger.debug(f"Released lock: {lock_key}")
            except Exception as e:
                logger.error(f"Error releasing lock {lock_key}: {e}")
