"""Cypher query helpers for concept graph operations."""

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def upsert_concept_node(concept: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """
    Build Cypher query to upsert a Concept node.

    Args:
        concept: Dictionary with:
            - concept_id (required, string)
            - name (string)
            - year (int, nullable)
            - block_id (string, nullable)
            - theme_id (string, nullable)
            - topic_id (string, nullable)
            - level (enum: THEME|TOPIC|CONCEPT)
            - is_active (bool)
            - updated_at (datetime ISO string)

    Returns:
        Tuple of (cypher_query, params_dict)

    Raises:
        ValueError: If concept_id is missing
    """
    if "concept_id" not in concept or not concept["concept_id"]:
        raise ValueError("concept_id is required for Concept node")

    concept_id = concept["concept_id"]
    updated_at = concept.get("updated_at") or datetime.now(UTC).isoformat()

    cypher = """
    MERGE (c:Concept {concept_id: $concept_id})
    SET c.name = $name,
        c.year = $year,
        c.block_id = $block_id,
        c.theme_id = $theme_id,
        c.topic_id = $topic_id,
        c.level = $level,
        c.is_active = $is_active,
        c.updated_at = $updated_at
    RETURN c.concept_id as concept_id
    """

    params = {
        "concept_id": concept_id,
        "name": concept.get("name", ""),
        "year": concept.get("year"),
        "block_id": concept.get("block_id"),
        "theme_id": concept.get("theme_id"),
        "topic_id": concept.get("topic_id"),
        "level": concept.get("level", "CONCEPT"),
        "is_active": concept.get("is_active", True),
        "updated_at": updated_at,
    }

    return cypher, params


def upsert_prereq_edge(
    from_id: str,
    to_id: str,
    props: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Build Cypher query to upsert a PREREQ relationship.

    Args:
        from_id: Source concept_id
        to_id: Target concept_id
        props: Dictionary with:
            - weight (float, default 1.0)
            - source (enum: MANUAL|IMPORTED|INFERRED, default MANUAL)
            - is_active (bool, default True)
            - created_at (datetime ISO string, optional)
            - updated_at (datetime ISO string, optional)
            - notes (string, nullable)

    Returns:
        Tuple of (cypher_query, params_dict)

    Raises:
        ValueError: If from_id == to_id (self-loop not allowed)
    """
    if from_id == to_id:
        raise ValueError("Self-loop edges are not allowed (from_id == to_id)")

    props = props or {}
    now = datetime.now(UTC).isoformat()

    # Ensure both nodes exist (MERGE minimally if needed)
    # But prefer calling upsert_concept_node first in application code
    cypher = """
    // Ensure both nodes exist (minimal merge)
    MERGE (from:Concept {concept_id: $from_id})
    MERGE (to:Concept {concept_id: $to_id})
    
    // Upsert the relationship
    MERGE (from)-[r:PREREQ]->(to)
    ON CREATE SET
        r.weight = $weight,
        r.source = $source,
        r.is_active = $is_active,
        r.created_at = $created_at,
        r.updated_at = $updated_at,
        r.notes = $notes
    ON MATCH SET
        r.weight = $weight,
        r.source = $source,
        r.is_active = $is_active,
        r.updated_at = $updated_at,
        r.notes = $notes
    RETURN from.concept_id as from_id, to.concept_id as to_id, r.weight as weight
    """

    params = {
        "from_id": from_id,
        "to_id": to_id,
        "weight": props.get("weight", 1.0),
        "source": props.get("source", "MANUAL"),
        "is_active": props.get("is_active", True),
        "created_at": props.get("created_at", now),
        "updated_at": props.get("updated_at", now),
        "notes": props.get("notes"),
    }

    return cypher, params


def deactivate_missing_edges(edge_ids: list[tuple[str, str]]) -> tuple[str, dict[str, Any]]:
    """
    Build Cypher query to soft-deactivate PREREQ edges not in the provided list.

    This is a stub for Task 134. For now, it returns a query that does nothing.

    Args:
        edge_ids: List of (from_id, to_id) tuples representing active edges

    Returns:
        Tuple of (cypher_query, params_dict)
    """
    # Stub implementation - will be expanded in Task 134
    # For now, return a no-op query
    cypher = """
    // Stub: deactivate_missing_edges
    // This will be implemented in Task 134
    RETURN 0 as deactivated_count
    """

    params = {
        "edge_ids": edge_ids,
    }

    return cypher, params
