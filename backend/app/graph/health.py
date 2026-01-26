"""Neo4j graph health check utilities."""

import logging
from typing import Any

from app.core.config import settings
from app.graph.neo4j_client import get_driver, ping, run_read
from app.graph.schema import ensure_constraints_and_indexes

logger = logging.getLogger(__name__)


def get_graph_health() -> dict[str, Any]:
    """
    Get Neo4j graph health information.

    Returns:
        Dictionary with:
        - enabled: bool
        - reachable: bool
        - latency_ms: int | None
        - database: str
        - schema_ok: bool
        - node_count: int | None
        - edge_count: int | None

    Behavior:
        - If disabled => all fields set to safe defaults (no crash)
        - If enabled but down => reachable=false with details
    """
    if not settings.NEO4J_ENABLED:
        return {
            "enabled": False,
            "reachable": False,
            "latency_ms": None,
            "database": settings.NEO4J_DATABASE,
            "schema_ok": False,
            "node_count": None,
            "edge_count": None,
        }

    # Check connectivity
    is_reachable, latency_ms, ping_details = ping()

    if not is_reachable:
        return {
            "enabled": True,
            "reachable": False,
            "latency_ms": None,
            "database": settings.NEO4J_DATABASE,
            "schema_ok": False,
            "node_count": None,
            "edge_count": None,
            "error": ping_details.get("error", "unreachable"),
        }

    # Check schema
    schema_result = ensure_constraints_and_indexes()
    schema_ok = (
        len(schema_result.get("constraints_created", [])) > 0
        or len(schema_result.get("indexes_created", [])) > 0
    ) and "error" not in schema_result

    # Get node and edge counts
    node_count = None
    edge_count = None

    try:
        # Count Concept nodes
        node_result = run_read("MATCH (c:Concept) RETURN count(c) as count")
        if node_result:
            node_count = node_result[0].get("count", 0)

        # Count PREREQ edges
        edge_result = run_read("MATCH ()-[r:PREREQ]->() RETURN count(r) as count")
        if edge_result:
            edge_count = edge_result[0].get("count", 0)
    except Exception as e:
        logger.debug(f"Failed to get graph counts: {e}")

    return {
        "enabled": True,
        "reachable": True,
        "latency_ms": latency_ms,
        "database": settings.NEO4J_DATABASE,
        "schema_ok": schema_ok,
        "node_count": node_count,
        "edge_count": edge_count,
    }
