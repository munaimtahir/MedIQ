"""Elasticsearch client wrapper with fail-open behavior."""

import logging
from typing import TYPE_CHECKING

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import (
    ConnectionError,
    RequestError,
    TransportError,
)

from app.core.config import settings

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch as ESClient

logger = logging.getLogger(__name__)

# Singleton client instance
_es_client: "ESClient | None" = None


def get_es_client() -> "ESClient | None":
    """
    Get Elasticsearch client singleton.

    Returns None if Elasticsearch is disabled or unavailable.
    All callers must handle None gracefully (fail-open).
    """
    global _es_client

    if not settings.ELASTICSEARCH_ENABLED:
        return None

    if _es_client is not None:
        return _es_client

    try:
        # Build connection kwargs
        http_auth = None
        if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
            http_auth = (settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)

        _es_client = Elasticsearch(
            [settings.ELASTICSEARCH_URL],
            http_auth=http_auth,
            request_timeout=settings.ELASTICSEARCH_REQUEST_TIMEOUT_MS / 1000.0,  # Convert ms to seconds
            max_retries=settings.ELASTICSEARCH_RETRY_MAX,
            retry_on_timeout=True,
        )

        # Test connection directly (avoid circular dependency)
        try:
            if not _es_client.ping():
                logger.warning("Elasticsearch ping failed, client will return None")
                _es_client = None
                return None
        except Exception as e:
            logger.warning(f"Elasticsearch ping failed during initialization: {e}")
            _es_client = None
            return None

        logger.debug("Elasticsearch client initialized successfully")
        return _es_client

    except Exception as e:
        logger.warning(f"Failed to initialize Elasticsearch client: {e}", exc_info=True)
        _es_client = None
        return None


def ping() -> bool:
    """
    Ping Elasticsearch to check connectivity.

    Returns False if disabled, unavailable, or ping fails.
    Never raises exceptions (fail-open).
    """
    if not settings.ELASTICSEARCH_ENABLED:
        return False

    client = get_es_client()
    if client is None:
        return False

    try:
        result = client.ping()
        logger.debug(f"Elasticsearch ping: {result}")
        return result
    except (ConnectionError, TransportError, RequestError) as e:
        logger.debug(f"Elasticsearch ping failed: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error during Elasticsearch ping: {e}", exc_info=True)
        return False


def ensure_enabled() -> bool:
    """
    Ensure Elasticsearch is enabled and available.

    Returns True if enabled and reachable, False otherwise.
    """
    if not settings.ELASTICSEARCH_ENABLED:
        return False
    return ping()


def reset_client() -> None:
    """Reset the singleton client (useful for testing)."""
    global _es_client
    _es_client = None
