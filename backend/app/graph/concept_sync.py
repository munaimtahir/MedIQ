"""Neo4j concept graph sync job (incremental + full rebuild).

This module implements idempotent sync from Postgres to Neo4j for the concept graph.
"""

import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.graph.cypher import upsert_concept_node, upsert_prereq_edge
from app.graph.neo4j_client import ping, run_read, run_write
from app.graph.schema import ensure_constraints_and_indexes
from app.graph.sync_source import (
    get_all_active_concepts,
    get_all_active_prereq_edges,
    get_concepts_since_watermark,
    get_inactive_concepts_since_watermark,
    get_inactive_edges_since_watermark,
    get_prereq_edges_since_watermark,
)
from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.neo4j_sync import Neo4jSyncRun, Neo4jSyncRunStatus, Neo4jSyncRunType

logger = logging.getLogger(__name__)


def _check_freeze_updates(db: Session) -> bool:
    """
    Check if freeze_updates is enabled (sync version).

    Returns:
        True if freeze_updates is enabled
    """
    config = db.query(AlgoRuntimeConfig).first()
    if not config:
        return False

    config_json = config.config_json or {}
    safe_mode = config_json.get("safe_mode", {})
    return safe_mode.get("freeze_updates", False)


def _get_last_incremental_watermark(db: Session) -> datetime | None:
    """
    Get last successful incremental sync watermark.

    Returns:
        finished_at timestamp of last successful incremental run, or None
    """
    last_run = (
        db.query(Neo4jSyncRun)
        .filter(
            Neo4jSyncRun.run_type == Neo4jSyncRunType.INCREMENTAL,
            Neo4jSyncRun.status == Neo4jSyncRunStatus.DONE,
        )
        .order_by(Neo4jSyncRun.finished_at.desc())
        .first()
    )

    if last_run and last_run.finished_at:
        return last_run.finished_at

    return None


def _detect_cycles() -> tuple[bool, list[dict[str, Any]]]:
    """
    Detect cycles in the prerequisite graph.

    Returns:
        Tuple of (has_cycles, cycle_samples)
    """
    if not settings.NEO4J_ENABLED:
        return False, []

    try:
        # Find cycles: paths that start and end at the same node
        cypher = """
        MATCH p = (start:Concept)-[:PREREQ*1..]->(start)
        RETURN start.concept_id as concept_id, length(p) as cycle_length
        LIMIT 10
        """
        results = run_read(cypher)

        cycles = [r for r in results]
        has_cycles = len(cycles) > 0

        return has_cycles, cycles
    except Exception as e:
        logger.debug(f"Cycle detection failed: {e}")
        return False, []


def _inactivate_node(concept_id: str) -> bool:
    """
    Soft-deactivate a Concept node in Neo4j.

    Args:
        concept_id: Concept ID to inactivate

    Returns:
        True if successful
    """
    if not settings.NEO4J_ENABLED:
        return False

    try:
        cypher = """
        MATCH (c:Concept {concept_id: $concept_id})
        SET c.is_active = false,
            c.updated_at = $updated_at
        RETURN c.concept_id as concept_id
        """
        params = {
            "concept_id": concept_id,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        run_write(cypher, params)
        return True
    except Exception as e:
        logger.warning(f"Failed to inactivate node {concept_id}: {e}")
        return False


def _inactivate_edge(from_id: str, to_id: str) -> bool:
    """
    Soft-deactivate a PREREQ edge in Neo4j.

    Args:
        from_id: Source concept ID
        to_id: Target concept ID

    Returns:
        True if successful
    """
    if not settings.NEO4J_ENABLED:
        return False

    try:
        cypher = """
        MATCH (from:Concept {concept_id: $from_id})-[r:PREREQ]->(to:Concept {concept_id: $to_id})
        SET r.is_active = false,
            r.updated_at = $updated_at
        RETURN from.concept_id as from_id, to.concept_id as to_id
        """
        params = {
            "from_id": from_id,
            "to_id": to_id,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        run_write(cypher, params)
        return True
    except Exception as e:
        logger.warning(f"Failed to inactivate edge {from_id} -> {to_id}: {e}")
        return False


def run_incremental_sync(db: Session, actor_user_id: UUID | None = None) -> UUID:
    """
    Run incremental sync from Postgres to Neo4j.

    Args:
        db: Database session
        actor_user_id: Optional user ID who triggered the sync

    Returns:
        Sync run ID

    Behavior:
        - If NEO4J_ENABLED=false => status=disabled
        - If freeze_updates=true => status=blocked_frozen
        - If Neo4j unreachable => status=failed
    """
    start_time = time.time()

    # Create sync run record
    sync_run = Neo4jSyncRun(
        id=uuid4(),
        run_type=Neo4jSyncRunType.INCREMENTAL,
        status=Neo4jSyncRunStatus.QUEUED,
    )
    db.add(sync_run)
    db.commit()
    db.refresh(sync_run)

    run_id = sync_run.id

    # Check if Neo4j is enabled
    if not settings.NEO4J_ENABLED:
        sync_run.status = Neo4jSyncRunStatus.DISABLED
        sync_run.finished_at = datetime.now(UTC)
        sync_run.last_error = "Neo4j is disabled"
        db.commit()
        logger.info(f"Neo4j sync run {run_id} skipped: Neo4j disabled")
        return run_id

    # Check freeze_updates
    if _check_freeze_updates(db):
        sync_run.status = Neo4jSyncRunStatus.BLOCKED_FROZEN
        sync_run.finished_at = datetime.now(UTC)
        sync_run.last_error = "Updates frozen (freeze_updates=true)"
        db.commit()
        logger.info(f"Neo4j sync run {run_id} blocked: freeze_updates enabled")
        return run_id

    # Check Neo4j reachability
    is_reachable, _, ping_details = ping()
    if not is_reachable:
        sync_run.status = Neo4jSyncRunStatus.FAILED
        sync_run.finished_at = datetime.now(UTC)
        sync_run.last_error = f"Neo4j unreachable: {ping_details.get('error', 'unknown')}"
        db.commit()
        logger.warning(f"Neo4j sync run {run_id} failed: Neo4j unreachable")
        return run_id

    # Start sync
    sync_run.status = Neo4jSyncRunStatus.RUNNING
    sync_run.started_at = datetime.now(UTC)
    db.commit()

    try:
        # Ensure schema exists
        ensure_constraints_and_indexes()

        # Get watermark
        watermark = _get_last_incremental_watermark(db)

        # Get concepts and edges updated since watermark
        concepts = get_concepts_since_watermark(db, watermark)
        edges = get_prereq_edges_since_watermark(db, watermark)

        # Get inactive concepts/edges
        inactive_concept_ids = get_inactive_concepts_since_watermark(db, watermark)
        inactive_edge_pairs = get_inactive_edges_since_watermark(db, watermark)

        # Upsert concepts
        nodes_upserted = 0
        for concept in concepts:
            try:
                cypher, params = upsert_concept_node(concept)
                run_write(cypher, params)
                nodes_upserted += 1
            except Exception as e:
                logger.warning(f"Failed to upsert concept {concept.get('concept_id')}: {e}")

        # Upsert edges
        edges_upserted = 0
        for edge in edges:
            try:
                cypher, params = upsert_prereq_edge(edge["from_id"], edge["to_id"], edge["props"])
                run_write(cypher, params)
                edges_upserted += 1
            except ValueError as e:
                # Self-loop rejected
                logger.warning(f"Skipping self-loop edge: {e}")
            except Exception as e:
                logger.warning(f"Failed to upsert edge {edge['from_id']} -> {edge['to_id']}: {e}")

        # Inactivate nodes
        nodes_inactivated = 0
        for concept_id in inactive_concept_ids:
            if _inactivate_node(concept_id):
                nodes_inactivated += 1

        # Inactivate edges
        edges_inactivated = 0
        for from_id, to_id in inactive_edge_pairs:
            if _inactivate_edge(from_id, to_id):
                edges_inactivated += 1

        # Cycle detection
        has_cycles, cycle_samples = _detect_cycles()

        # Get final counts
        node_count_result = run_read("MATCH (c:Concept) RETURN count(c) as count")
        edge_count_result = run_read("MATCH ()-[r:PREREQ]->() RETURN count(r) as count")

        node_count = node_count_result[0].get("count", 0) if node_count_result else 0
        edge_count = edge_count_result[0].get("count", 0) if edge_count_result else 0

        duration_ms = int((time.time() - start_time) * 1000)

        # Update sync run
        sync_run.status = Neo4jSyncRunStatus.DONE
        sync_run.finished_at = datetime.now(UTC)
        sync_run.nodes_upserted = nodes_upserted
        sync_run.edges_upserted = edges_upserted
        sync_run.nodes_inactivated = nodes_inactivated
        sync_run.edges_inactivated = edges_inactivated
        sync_run.cycle_detected = has_cycles
        sync_run.details = {
            "node_count": node_count,
            "edge_count": edge_count,
            "duration_ms": duration_ms,
            "watermark": watermark.isoformat() if watermark else None,
            "cycle_samples": cycle_samples[:5],  # Store first 5 cycles
        }
        db.commit()

        logger.info(
            f"Neo4j incremental sync completed: run_id={run_id}, "
            f"nodes_upserted={nodes_upserted}, edges_upserted={edges_upserted}, "
            f"duration_ms={duration_ms}, cycle_detected={has_cycles}"
        )

    except Exception as e:
        logger.error(f"Neo4j incremental sync failed: {e}", exc_info=True)
        sync_run.status = Neo4jSyncRunStatus.FAILED
        sync_run.finished_at = datetime.now(UTC)
        sync_run.last_error = str(e)
        db.commit()

    return run_id


def run_full_rebuild(db: Session, actor_user_id: UUID | None = None) -> UUID:
    """
    Run full rebuild of Neo4j concept graph from Postgres.

    Args:
        db: Database session
        actor_user_id: Optional user ID who triggered the sync

    Returns:
        Sync run ID

    Behavior:
        - If NEO4J_ENABLED=false => status=disabled
        - If freeze_updates=true => status=blocked_frozen
        - If Neo4j unreachable => status=failed
        - Uses Option A: DETACH DELETE all nodes, then upsert all active
    """
    start_time = time.time()

    # Create sync run record
    sync_run = Neo4jSyncRun(
        id=uuid4(),
        run_type=Neo4jSyncRunType.FULL,
        status=Neo4jSyncRunStatus.QUEUED,
    )
    db.add(sync_run)
    db.commit()
    db.refresh(sync_run)

    run_id = sync_run.id

    # Check if Neo4j is enabled
    if not settings.NEO4J_ENABLED:
        sync_run.status = Neo4jSyncRunStatus.DISABLED
        sync_run.finished_at = datetime.now(UTC)
        sync_run.last_error = "Neo4j is disabled"
        db.commit()
        logger.info(f"Neo4j full rebuild {run_id} skipped: Neo4j disabled")
        return run_id

    # Check freeze_updates
    if _check_freeze_updates(db):
        sync_run.status = Neo4jSyncRunStatus.BLOCKED_FROZEN
        sync_run.finished_at = datetime.now(UTC)
        sync_run.last_error = "Updates frozen (freeze_updates=true)"
        db.commit()
        logger.info(f"Neo4j full rebuild {run_id} blocked: freeze_updates enabled")
        return run_id

    # Check Neo4j reachability
    is_reachable, _, ping_details = ping()
    if not is_reachable:
        sync_run.status = Neo4jSyncRunStatus.FAILED
        sync_run.finished_at = datetime.now(UTC)
        sync_run.last_error = f"Neo4j unreachable: {ping_details.get('error', 'unknown')}"
        db.commit()
        logger.warning(f"Neo4j full rebuild {run_id} failed: Neo4j unreachable")
        return run_id

    # Start sync
    sync_run.status = Neo4jSyncRunStatus.RUNNING
    sync_run.started_at = datetime.now(UTC)
    db.commit()

    try:
        # Ensure schema exists
        ensure_constraints_and_indexes()

        # Option A: Delete all nodes (DETACH DELETE removes nodes and relationships)
        logger.info("Deleting all existing Concept nodes and relationships")
        delete_cypher = "MATCH (n:Concept) DETACH DELETE n"
        run_write(delete_cypher)

        # Get all active concepts and edges
        concepts = get_all_active_concepts(db)
        edges = get_all_active_prereq_edges(db)

        # Upsert all concepts
        nodes_upserted = 0
        for concept in concepts:
            try:
                cypher, params = upsert_concept_node(concept)
                run_write(cypher, params)
                nodes_upserted += 1
            except Exception as e:
                logger.warning(f"Failed to upsert concept {concept.get('concept_id')}: {e}")

        # Upsert all edges
        edges_upserted = 0
        for edge in edges:
            try:
                cypher, params = upsert_prereq_edge(edge["from_id"], edge["to_id"], edge["props"])
                run_write(cypher, params)
                edges_upserted += 1
            except ValueError as e:
                # Self-loop rejected
                logger.warning(f"Skipping self-loop edge: {e}")
            except Exception as e:
                logger.warning(f"Failed to upsert edge {edge['from_id']} -> {edge['to_id']}: {e}")

        # Cycle detection
        has_cycles, cycle_samples = _detect_cycles()

        # Get final counts
        node_count_result = run_read("MATCH (c:Concept) RETURN count(c) as count")
        edge_count_result = run_read("MATCH ()-[r:PREREQ]->() RETURN count(r) as count")

        node_count = node_count_result[0].get("count", 0) if node_count_result else 0
        edge_count = edge_count_result[0].get("count", 0) if edge_count_result else 0

        duration_ms = int((time.time() - start_time) * 1000)

        # Update sync run
        sync_run.status = Neo4jSyncRunStatus.DONE
        sync_run.finished_at = datetime.now(UTC)
        sync_run.nodes_upserted = nodes_upserted
        sync_run.edges_upserted = edges_upserted
        sync_run.nodes_inactivated = 0  # Full rebuild doesn't inactivate
        sync_run.edges_inactivated = 0
        sync_run.cycle_detected = has_cycles
        sync_run.details = {
            "node_count": node_count,
            "edge_count": edge_count,
            "duration_ms": duration_ms,
            "cycle_samples": cycle_samples[:5],
        }
        db.commit()

        logger.info(
            f"Neo4j full rebuild completed: run_id={run_id}, "
            f"nodes_upserted={nodes_upserted}, edges_upserted={edges_upserted}, "
            f"duration_ms={duration_ms}, cycle_detected={has_cycles}"
        )

    except Exception as e:
        logger.error(f"Neo4j full rebuild failed: {e}", exc_info=True)
        sync_run.status = Neo4jSyncRunStatus.FAILED
        sync_run.finished_at = datetime.now(UTC)
        sync_run.last_error = str(e)
        db.commit()

    return run_id
