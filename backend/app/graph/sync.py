"""Neo4j sync job: sync prerequisite edges from Postgres to Neo4j.

This job is idempotent and can be run multiple times safely.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.graph.neo4j_client import get_driver, is_neo4j_available
from app.models.graph_revision import PrereqEdge, PrereqSyncRun, PrereqSyncStatus

logger = logging.getLogger(__name__)


async def sync_prereq_edges_to_neo4j(
    db: AsyncSession,
    created_by_user_id: UUID | None = None,
) -> PrereqSyncRun:
    """
    Sync active prerequisite edges from Postgres to Neo4j.

    This is an idempotent operation:
    - Upserts all active themes as nodes
    - Upserts all active prereq edges
    - Removes edges that are no longer active

    Args:
        db: Database session
        created_by_user_id: Optional user ID who triggered the sync

    Returns:
        PrereqSyncRun record with status and details
    """
    sync_run = PrereqSyncRun(
        id=uuid4(),
        status=PrereqSyncStatus.QUEUED,
        started_at=None,
        finished_at=None,
        details_json=None,
    )
    db.add(sync_run)
    await db.commit()
    await db.refresh(sync_run)

    if not is_neo4j_available():
        sync_run.status = PrereqSyncStatus.FAILED
        sync_run.finished_at = datetime.now(UTC)
        sync_run.details_json = {"error": "Neo4j unavailable"}
        await db.commit()
        return sync_run

    sync_run.status = PrereqSyncStatus.RUNNING
    sync_run.started_at = datetime.now(UTC)
    await db.commit()

    try:
        # Fetch active themes and edges from Postgres
        stmt = select(PrereqEdge).where(PrereqEdge.is_active == True)
        result = await db.execute(stmt)
        edges = result.scalars().all()

        # Get unique theme IDs
        theme_ids = set()
        for edge in edges:
            theme_ids.add(edge.from_theme_id)
            theme_ids.add(edge.to_theme_id)

        # Also fetch themes from themes table to ensure all are present
        from app.models.syllabus import Theme

        theme_stmt = select(Theme).where(Theme.is_active == True)
        theme_result = await db.execute(theme_stmt)
        themes = theme_result.scalars().all()
        for theme in themes:
            theme_ids.add(theme.id)

        driver = get_driver()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Upsert all theme nodes (with theme name if available)
            node_count = 0
            theme_map = {t.id: t for t in themes}
            for theme_id in theme_ids:
                theme = theme_map.get(theme_id)
                session.run(
                    """
                    MERGE (t:Theme {theme_id: $theme_id})
                    SET t.updated_at = datetime(),
                        t.name = $name
                    """,
                    theme_id=str(theme_id),
                    name=theme.title if theme else None,
                    timeout=5.0,
                )
                node_count += 1

            # Upsert all edges
            edge_count = 0
            for edge in edges:
                session.run(
                    """
                    MATCH (from:Theme {theme_id: $from_id})
                    MATCH (to:Theme {theme_id: $to_id})
                    MERGE (from)-[r:PREREQ_OF]->(to)
                    SET r.weight = $weight,
                        r.source = $source,
                        r.confidence = $confidence,
                        r.updated_at = datetime()
                    """,
                    from_id=str(edge.from_theme_id),
                    to_id=str(edge.to_theme_id),
                    weight=edge.weight,
                    source=edge.source,
                    confidence=edge.confidence,
                    timeout=5.0,
                )
                edge_count += 1

            # Remove edges that are no longer active
            # Get all edges in Neo4j and check if they're still active in Postgres
            active_edge_pairs = {(e.from_theme_id, e.to_theme_id) for e in edges}
            all_neo4j_edges = session.run(
                """
                MATCH (from:Theme)-[r:PREREQ_OF]->(to:Theme)
                RETURN from.theme_id AS from_id, to.theme_id AS to_id
                """,
                timeout=10.0,
            )
            removed_count = 0
            for record in all_neo4j_edges:
                from_id = int(record["from_id"])
                to_id = int(record["to_id"])
                if (from_id, to_id) not in active_edge_pairs:
                    session.run(
                        """
                        MATCH (from:Theme {theme_id: $from_id})-[r:PREREQ_OF]->(to:Theme {theme_id: $to_id})
                        DELETE r
                        """,
                        from_id=str(from_id),
                        to_id=str(to_id),
                        timeout=5.0,
                    )
                    removed_count += 1

            session.commit()

        sync_run.status = PrereqSyncStatus.DONE
        sync_run.finished_at = datetime.now(UTC)
        sync_run.details_json = {
            "node_count": node_count,
            "edge_count": edge_count,
            "removed_edge_count": removed_count,
        }
        await db.commit()

        logger.info(
            f"Neo4j sync completed: {node_count} nodes, {edge_count} edges, {removed_count} removed"
        )

    except Exception as e:
        logger.error(f"Neo4j sync failed: {e}", exc_info=True)
        sync_run.status = PrereqSyncStatus.FAILED
        sync_run.finished_at = datetime.now(UTC)
        sync_run.details_json = {"error": str(e)}
        await db.commit()

    return sync_run
