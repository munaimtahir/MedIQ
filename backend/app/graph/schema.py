"""Neo4j schema management (constraints and indexes)."""

import logging
from typing import Any

from app.core.config import settings
from app.graph.neo4j_client import get_driver, run_write

logger = logging.getLogger(__name__)


def ensure_constraints_and_indexes() -> dict[str, Any]:
    """
    Ensure Neo4j constraints and indexes exist (idempotent).

    Creates:
    - UNIQUE constraint on Concept.concept_id
    - INDEX on Concept.level
    - INDEX on Concept.theme_id
    - INDEX on Concept.block_id

    Returns:
        Dictionary with created status for each constraint/index
    """
    if not settings.NEO4J_ENABLED:
        logger.debug("Neo4j disabled, skipping schema creation")
        return {
            "enabled": False,
            "constraints_created": [],
            "indexes_created": [],
        }

    driver = get_driver()
    if driver is None:
        logger.warning("Neo4j driver unavailable, cannot create schema")
        return {
            "enabled": True,
            "constraints_created": [],
            "indexes_created": [],
            "error": "driver_unavailable",
        }

    results: dict[str, Any] = {
        "enabled": True,
        "constraints_created": [],
        "indexes_created": [],
    }

    try:
        # Create UNIQUE constraint on concept_id (idempotent with IF NOT EXISTS)
        # Note: Neo4j 5.x syntax uses CREATE CONSTRAINT ... IF NOT EXISTS
        constraint_cypher = """
        CREATE CONSTRAINT concept_id_unique IF NOT EXISTS
        FOR (c:Concept)
        REQUIRE c.concept_id IS UNIQUE
        """
        run_write(constraint_cypher)
        results["constraints_created"].append("concept_id_unique")
        logger.info("Created/verified constraint: concept_id_unique")

        # Create indexes (idempotent with IF NOT EXISTS)
        indexes = [
            ("level", "Concept", "level"),
            ("theme_id", "Concept", "theme_id"),
            ("block_id", "Concept", "block_id"),
        ]

        for index_name, label, property_name in indexes:
            # Neo4j 5.x syntax for index creation
            index_cypher = f"""
            CREATE INDEX {index_name}_index IF NOT EXISTS
            FOR (c:{label})
            ON (c.{property_name})
            """
            run_write(index_cypher)
            results["indexes_created"].append(f"{index_name}_index")
            logger.info(f"Created/verified index: {index_name}_index")

        return results

    except Exception as e:
        logger.error(f"Failed to create Neo4j schema: {e}", exc_info=True)
        results["error"] = str(e)
        return results
