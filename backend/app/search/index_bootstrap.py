"""Index bootstrap utilities for Elasticsearch indices."""

import logging
from datetime import UTC, datetime
from typing import Any

from elasticsearch.exceptions import ConnectionError, RequestError, TransportError

from app.core.config import settings
from app.search.es_client import get_es_client

logger = logging.getLogger(__name__)


def build_questions_v1_mapping() -> dict[str, Any]:
    """
    Build Elasticsearch mapping for questions v1 index.

    Returns a mapping dictionary with:
    - keyword fields for filtering (IDs, status, taxonomy)
    - text fields with english analyzer for searchable content
    - multi-fields for names (text + keyword)
    """
    return {
        "properties": {
            # Identifiers
            "question_id": {"type": "keyword"},
            "version_id": {"type": "keyword"},
            "status": {"type": "keyword"},
            "published_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "is_active": {"type": "boolean"},
            # Syllabus
            "year": {"type": "integer"},
            "block_id": {"type": "keyword"},
            "block_name": {
                "type": "text",
                "analyzer": "english",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "theme_id": {"type": "keyword"},
            "theme_name": {
                "type": "text",
                "analyzer": "english",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "topic_id": {"type": "keyword"},
            "topic_name": {
                "type": "text",
                "analyzer": "english",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "concept_ids": {"type": "keyword"},
            # Pedagogy
            "cognitive_level": {"type": "keyword"},
            "difficulty_label": {"type": "keyword"},
            "source_book": {"type": "keyword"},
            "source_page": {"type": "integer"},
            "source_ref": {"type": "keyword"},
            # Content
            "stem": {"type": "text", "analyzer": "english"},
            "options": {"type": "text", "analyzer": "english"},
            "explanation_md": {"type": "text", "analyzer": "english"},
            "explanation_plain": {"type": "text", "analyzer": "english"},
            "tags_text": {"type": "text", "analyzer": "english"},
        }
    }


def build_questions_v1_settings() -> dict[str, Any]:
    """
    Build index settings for questions v1.

    Returns settings with shards/replicas configurable via env (defaults for dev).
    """
    # For dev, use 1 shard and 0 replicas
    # In production, these should be configurable
    number_of_shards = 1
    number_of_replicas = 0

    return {
        "number_of_shards": number_of_shards,
        "number_of_replicas": number_of_replicas,
        "analysis": {
            "analyzer": {
                "default": {
                    "type": "english",
                }
            }
        },
    }


def get_questions_read_alias() -> str:
    """Get the read alias name for questions."""
    return f"{settings.ELASTICSEARCH_INDEX_PREFIX}_questions_read"


def get_questions_write_alias() -> str:
    """Get the write alias name for questions."""
    return f"{settings.ELASTICSEARCH_INDEX_PREFIX}_questions_write"


def generate_questions_index_name(timestamp: datetime | None = None) -> str:
    """
    Generate a versioned index name for questions.

    Args:
        timestamp: Optional timestamp. If None, uses current UTC time.

    Returns:
        Index name like: platform_questions_v1_20260123T120000Z
    """
    if timestamp is None:
        timestamp = datetime.now(UTC)
    timestamp_str = timestamp.strftime("%Y%m%dT%H%M%SZ")
    return f"{settings.ELASTICSEARCH_INDEX_PREFIX}_questions_v1_{timestamp_str}"


def create_questions_index(timestamp: datetime | None = None) -> str:
    """
    Create a new questions index with v1 mapping.

    Args:
        timestamp: Optional timestamp for index name. If None, uses current time.

    Returns:
        The created index name.

    Raises:
        Exception if Elasticsearch is disabled or creation fails.
    """
    client = get_es_client()
    if client is None:
        raise ValueError("Elasticsearch is disabled or unavailable")

    index_name = generate_questions_index_name(timestamp)
    mapping = build_questions_v1_mapping()
    settings_dict = build_questions_v1_settings()

    try:
        client.indices.create(
            index=index_name,
            body={
                "settings": settings_dict,
                "mappings": mapping,
            },
        )
        logger.info(f"Created questions index: {index_name}")
        return index_name
    except (ConnectionError, TransportError, RequestError) as e:
        logger.error(f"Failed to create questions index {index_name}: {e}")
        raise


def get_current_questions_index() -> str | None:
    """
    Get the current questions index name from the write alias.

    Returns:
        Index name if alias exists, None otherwise.
    """
    client = get_es_client()
    if client is None:
        return None

    write_alias = get_questions_write_alias()

    try:
        aliases = client.indices.get_alias(name=write_alias)
        if aliases:
            # Return the first (and should be only) index name
            return list(aliases.keys())[0]
        return None
    except (ConnectionError, TransportError, RequestError) as e:
        logger.debug(f"Failed to get current questions index: {e}")
        return None


def swap_questions_aliases(new_index_name: str) -> None:
    """
    Atomically swap read and write aliases to point to a new index.

    This is done atomically to ensure no downtime during reindexing.

    Args:
        new_index_name: The new index name to point aliases to.

    Raises:
        Exception if swap fails.
    """
    client = get_es_client()
    if client is None:
        raise ValueError("Elasticsearch is disabled or unavailable")

    read_alias = get_questions_read_alias()
    write_alias = get_questions_write_alias()

    # Get current index (if any)
    current_index = get_current_questions_index()

    # Build alias actions
    actions = []

    # Remove old aliases if they exist
    if current_index:
        actions.append({"remove": {"index": current_index, "alias": read_alias}})
        actions.append({"remove": {"index": current_index, "alias": write_alias}})

    # Add new aliases
    actions.append({"add": {"index": new_index_name, "alias": read_alias}})
    actions.append({"add": {"index": new_index_name, "alias": write_alias}})

    try:
        client.indices.update_aliases(body={"actions": actions})
        logger.info(
            f"Swapped questions aliases: {read_alias} and {write_alias} now point to {new_index_name}"
        )
    except (ConnectionError, TransportError, RequestError) as e:
        logger.error(f"Failed to swap questions aliases: {e}")
        raise


def ensure_questions_aliases_exist() -> dict[str, Any]:
    """
    Ensure questions aliases exist, creating index if needed.

    If aliases don't exist, creates a new index and sets both aliases.

    Returns:
        Dictionary with:
        - created: bool (whether index was created)
        - index_name: str (current index name)
        - read_alias: str
        - write_alias: str

    Raises:
        Exception if Elasticsearch is disabled or operation fails.
    """
    if not settings.ELASTICSEARCH_ENABLED:
        logger.debug("Elasticsearch disabled, skipping alias creation")
        return {
            "created": False,
            "index_name": None,
            "read_alias": get_questions_read_alias(),
            "write_alias": get_questions_write_alias(),
        }

    client = get_es_client()
    if client is None:
        raise ValueError("Elasticsearch is enabled but unavailable")

    read_alias = get_questions_read_alias()
    write_alias = get_questions_write_alias()

    # Check if aliases exist
    current_index = get_current_questions_index()

    if current_index:
        logger.debug(f"Questions aliases already exist, pointing to {current_index}")
        return {
            "created": False,
            "index_name": current_index,
            "read_alias": read_alias,
            "write_alias": write_alias,
        }

    # Create new index and set aliases
    logger.info("Creating initial questions index and aliases")
    index_name = create_questions_index()
    swap_questions_aliases(index_name)

    return {
        "created": True,
        "index_name": index_name,
        "read_alias": read_alias,
        "write_alias": write_alias,
    }
