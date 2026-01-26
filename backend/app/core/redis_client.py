"""Redis client module with connection pooling."""

import redis
from redis.exceptions import ConnectionError, RedisError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global Redis client instance
_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis | None:
    """Get Redis client instance. Returns None if Redis is disabled or unavailable."""
    global _redis_client

    if not settings.REDIS_ENABLED:
        return None

    if _redis_client is None:
        if not settings.REDIS_URL:
            if settings.REDIS_REQUIRED:
                raise ValueError("REDIS_URL must be set when REDIS_REQUIRED=true")
            logger.warning("Redis enabled but REDIS_URL not set. Redis features will be disabled.")
            return None

        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,  # Fast fail on connect (production hardening)
                socket_timeout=1,  # Fast fail on operations (production hardening)
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis connection established")
        except (ConnectionError, RedisError) as e:
            if settings.REDIS_REQUIRED:
                raise ConnectionError(
                    f"Redis connection failed and REDIS_REQUIRED=true: {e}"
                ) from e
            logger.warning(f"Redis connection failed (non-fatal): {e}")
            _redis_client = None

    return _redis_client


def is_redis_available() -> bool:
    """Check if Redis is available."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.ping()
        return True
    except Exception:
        return False


def init_redis() -> None:
    """Initialize Redis connection on startup."""
    if settings.REDIS_ENABLED:
        try:
            get_redis_client()
        except Exception as e:
            if settings.REDIS_REQUIRED:
                raise
            logger.warning(f"Redis initialization failed (non-fatal): {e}")
