"""Health check utilities for Elasticsearch."""

import logging
from typing import Any

from elasticsearch.exceptions import ConnectionError, RequestError, TransportError

from app.core.config import settings
from app.search.es_client import get_es_client, ping
from app.search.index_bootstrap import (
    get_current_questions_index,
    get_questions_read_alias,
    get_questions_write_alias,
)
from app.search.typing import IndexHealth

logger = logging.getLogger(__name__)


def get_health_info() -> dict[str, Any]:
    """
    Get Elasticsearch health information.

    Returns a dictionary with health status, indices, and aliases.
    Never raises exceptions (fail-open).
    """
    if not settings.ELASTICSEARCH_ENABLED:
        return {
            "enabled": False,
            "reachable": False,
            "url": settings.ELASTICSEARCH_URL,
            "index_prefix": settings.ELASTICSEARCH_INDEX_PREFIX,
            "indices": [],
            "aliases": None,
            "last_sync_run": None,
            "pending_outbox": None,
        }

    client = get_es_client()
    if client is None:
        return {
            "enabled": True,
            "reachable": False,
            "url": settings.ELASTICSEARCH_URL,
            "index_prefix": settings.ELASTICSEARCH_INDEX_PREFIX,
            "indices": [],
            "aliases": None,
            "last_sync_run": None,
            "pending_outbox": None,
        }

    try:
        # Get cluster health
        cluster_health = client.cluster.health()
        is_reachable = cluster_health.get("status") in ("green", "yellow", "red")

        # Get indices with prefix
        indices_info = []
        try:
            indices = client.indices.get(index=f"{settings.ELASTICSEARCH_INDEX_PREFIX}*")
            for index_name, index_meta in indices.items():
                stats = client.indices.stats(index=index_name)
                doc_count = stats["indices"][index_name]["total"]["docs"]["count"]
                health: IndexHealth = cluster_health.get("status", "red")
                indices_info.append(
                    {
                        "name": index_name,
                        "doc_count": doc_count,
                        "health": health,
                    }
                )
        except (ConnectionError, TransportError, RequestError) as e:
            logger.debug(f"Failed to get indices info: {e}")
            indices_info = []

        # Get aliases
        aliases = None
        try:
            read_alias = get_questions_read_alias()
            write_alias = get_questions_write_alias()
            current_index = get_current_questions_index()
            aliases = {
                "questions_read": current_index if current_index else None,
                "questions_write": current_index if current_index else None,
            }
        except Exception as e:
            logger.debug(f"Failed to get aliases: {e}")
            aliases = {
                "questions_read": None,
                "questions_write": None,
            }

        # Last sync run and pending outbox (stub for now)
        # These will be populated when sync jobs are implemented
        last_sync_run = None
        pending_outbox = None

        return {
            "enabled": True,
            "reachable": is_reachable,
            "url": settings.ELASTICSEARCH_URL,
            "index_prefix": settings.ELASTICSEARCH_INDEX_PREFIX,
            "indices": indices_info,
            "aliases": aliases,
            "last_sync_run": last_sync_run,
            "pending_outbox": pending_outbox,
        }

    except (ConnectionError, TransportError, RequestError) as e:
        logger.debug(f"Elasticsearch health check failed: {e}")
        return {
            "enabled": True,
            "reachable": False,
            "url": settings.ELASTICSEARCH_URL,
            "index_prefix": settings.ELASTICSEARCH_INDEX_PREFIX,
            "indices": [],
            "aliases": None,
            "last_sync_run": None,
            "pending_outbox": None,
        }
    except Exception as e:
        logger.warning(f"Unexpected error during Elasticsearch health check: {e}", exc_info=True)
        return {
            "enabled": True,
            "reachable": False,
            "url": settings.ELASTICSEARCH_URL,
            "index_prefix": settings.ELASTICSEARCH_INDEX_PREFIX,
            "indices": [],
            "aliases": None,
            "last_sync_run": None,
            "pending_outbox": None,
        }
