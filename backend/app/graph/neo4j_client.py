"""Neo4j client singleton with fail-open behavior."""

import logging
import time
from typing import Any

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton driver instance
_driver: Driver | None = None


def get_driver() -> Driver | None:
    """
    Get Neo4j driver singleton (only if enabled).

    Returns:
        Driver instance if enabled and available, None otherwise.
    """
    global _driver

    if not settings.NEO4J_ENABLED:
        return None

    if _driver is None:
        try:
            _driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                max_connection_lifetime=settings.NEO4J_MAX_CONNECTION_LIFETIME,
            )
            logger.info(f"Neo4j driver initialized: {settings.NEO4J_URI}")
        except Exception as e:
            logger.warning(f"Failed to initialize Neo4j driver: {e}")
            _driver = None

    return _driver


def reset_driver() -> None:
    """Reset driver singleton (for testing)."""
    global _driver
    if _driver:
        try:
            _driver.close()
        except Exception:
            pass
    _driver = None


def ping() -> tuple[bool, int | None, dict[str, Any]]:
    """
    Ping Neo4j to check connectivity.

    Returns:
        Tuple of (ok, latency_ms, details)
    """
    if not settings.NEO4J_ENABLED:
        return False, None, {"enabled": False}

    driver = get_driver()
    if driver is None:
        return False, None, {"enabled": True, "error": "driver_unavailable"}

    try:
        start = time.time()
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.consume()
        latency_ms = int((time.time() - start) * 1000)
        return True, latency_ms, {"enabled": True, "reachable": True}
    except (ServiceUnavailable, AuthError) as e:
        logger.debug(f"Neo4j ping failed: {e}")
        return False, None, {"enabled": True, "reachable": False, "error": str(e)}
    except Exception as e:
        logger.warning(f"Unexpected error during Neo4j ping: {e}")
        return False, None, {"enabled": True, "reachable": False, "error": str(e)}


def run_read(cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Execute a read-only Cypher query.

    Args:
        cypher: Cypher query string
        params: Query parameters

    Returns:
        List of result records (as dictionaries)

    Behavior:
        - If disabled, returns empty list (fail-open)
        - If driver unavailable, returns empty list (fail-open)
    """
    if not settings.NEO4J_ENABLED:
        return []

    driver = get_driver()
    if driver is None:
        logger.debug("Neo4j driver unavailable, returning empty result")
        return []

    try:
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]
    except Exception as e:
        logger.warning(f"Neo4j read query failed: {e}", exc_info=True)
        return []  # Fail-open


def run_write(cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Execute a write Cypher query (in a transaction).

    Args:
        cypher: Cypher query string
        params: Query parameters

    Returns:
        List of result records (as dictionaries)

    Behavior:
        - If disabled, returns empty list (fail-open)
        - If driver unavailable, returns empty list (fail-open)
    """
    if not settings.NEO4J_ENABLED:
        return []

    driver = get_driver()
    if driver is None:
        logger.debug("Neo4j driver unavailable, returning empty result")
        return []

    try:
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.write_transaction(lambda tx: tx.run(cypher, params or {}))
            return [record.data() for record in result]
    except Exception as e:
        logger.warning(f"Neo4j write query failed: {e}", exc_info=True)
        return []  # Fail-open


# Compatibility functions for existing graph_revision code
def is_neo4j_available() -> bool:
    """
    Check if Neo4j is available (compatibility function).

    Returns:
        True if enabled and reachable, False otherwise
    """
    if not settings.NEO4J_ENABLED:
        return False
    ok, _, _ = ping()
    return ok


def get_graph_stats() -> dict[str, Any]:
    """
    Get graph statistics (compatibility function).

    Returns:
        Dictionary with node_count, edge_count, and available flag
    """
    if not settings.NEO4J_ENABLED:
        return {
            "available": False,
            "node_count": 0,
            "edge_count": 0,
            "error": "Neo4j disabled",
        }

    try:
        node_result = run_read("MATCH (c:Concept) RETURN count(c) as count")
        edge_result = run_read("MATCH ()-[r:PREREQ]->() RETURN count(r) as count")

        node_count = node_result[0].get("count", 0) if node_result else 0
        edge_count = edge_result[0].get("count", 0) if edge_result else 0

        return {
            "available": True,
            "node_count": node_count,
            "edge_count": edge_count,
        }
    except Exception as e:
        logger.debug(f"Failed to get graph stats: {e}")
        return {
            "available": False,
            "node_count": 0,
            "edge_count": 0,
            "error": str(e),
        }


def detect_cycles() -> dict[str, Any]:
    """
    Detect cycles in the prerequisite graph (compatibility function).

    Returns:
        Dictionary with has_cycles, cycles, cycle_count, and error (if any)
    """
    if not settings.NEO4J_ENABLED:
        return {
            "has_cycles": False,
            "cycles": [],
            "cycle_count": 0,
            "error": "Neo4j disabled",
        }

    try:
        # Simple cycle detection: find paths that start and end at the same node
        cypher = """
        MATCH path = (start:Concept)-[:PREREQ*]->(start)
        WHERE length(path) > 0
        RETURN start.concept_id as concept_id, length(path) as cycle_length
        LIMIT 100
        """
        results = run_read(cypher)

        cycles = [r for r in results]
        has_cycles = len(cycles) > 0

        return {
            "has_cycles": has_cycles,
            "cycles": cycles,
            "cycle_count": len(cycles),
        }
    except Exception as e:
        logger.debug(f"Failed to detect cycles: {e}")
        return {
            "has_cycles": False,
            "cycles": [],
            "cycle_count": 0,
            "error": str(e),
        }
