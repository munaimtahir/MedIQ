"""Graph revision activation eligibility gates.

Checks integrity and safety criteria before allowing activation.
"""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.neo4j_client import detect_cycles, get_graph_stats, is_neo4j_available
from app.learning_engine.graph_revision.planner import get_planner_config
from app.models.graph_revision import GraphRevisionConfig, PrereqEdge, ShadowRevisionPlan
from app.models.syllabus import Theme

logger = logging.getLogger(__name__)


async def is_graph_revision_eligible_for_activation(
    db: AsyncSession,
) -> tuple[bool, list[str]]:
    """
    Check if graph revision is eligible for activation.

    Gates:
    1. Cycle check: No cycles OR cycles handled with explicit policy
    2. Coverage: % themes with at least one prereq edge >= threshold
    3. Neo4j availability: Success rate >= threshold in last 7 days

    Args:
        db: Database session

    Returns:
        Tuple of (eligible: bool, reasons: list[str])
    """
    reasons = []
    config = await get_planner_config(db)
    coverage_threshold = config.get("coverage_threshold", 0.50)
    neo4j_availability_threshold = config.get("neo4j_availability_threshold", 0.95)
    cycle_check_enabled = config.get("cycle_check_enabled", True)

    # Gate 1: Cycle check
    if cycle_check_enabled:
        cycle_report = detect_cycles()
        if cycle_report.get("has_cycles", False):
            reasons.append(f"Cycle check failed: {cycle_report.get('cycle_count', 0)} cycles detected")
            return False, reasons

    # Gate 2: Coverage
    # Count themes with at least one prereq edge
    stmt = select(func.count(func.distinct(PrereqEdge.to_theme_id))).where(PrereqEdge.is_active == True)
    result = await db.execute(stmt)
    themes_with_prereqs = result.scalar_one()

    stmt = select(func.count(Theme.id)).where(Theme.is_active == True)
    result = await db.execute(stmt)
    total_themes = result.scalar_one()

    if total_themes == 0:
        reasons.append("No active themes found")
        return False, reasons

    coverage = themes_with_prereqs / total_themes if total_themes > 0 else 0.0
    if coverage < coverage_threshold:
        reasons.append(f"Coverage too low: {coverage:.2%} < {coverage_threshold:.2%}")

    # Gate 3: Neo4j availability
    # For now, just check current availability (can be enhanced with historical tracking)
    if not is_neo4j_available():
        reasons.append("Neo4j currently unavailable")
        return False, reasons

    # All gates passed
    if not reasons:
        return True, ["All gates passed"]

    return False, reasons
