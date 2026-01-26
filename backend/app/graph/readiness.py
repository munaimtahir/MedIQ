"""Neo4j graph readiness evaluation module (shadow gate)."""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.graph.health import get_graph_health
from app.graph.neo4j_client import ping
from app.graph.schema import ensure_constraints_and_indexes
from app.models.neo4j_sync import Neo4jSyncRun, Neo4jSyncRunStatus, Neo4jSyncRunType

logger = logging.getLogger(__name__)

# Cache readiness result for ~30 seconds to avoid hammering Neo4j
_readiness_cache: dict[str, Any] = {"result": None, "timestamp": 0}
READINESS_CACHE_TTL = 30  # seconds


class ReadinessCheckResult:
    """Result of a single readiness check."""

    def __init__(self, ok: bool, details: dict[str, Any] | None = None):
        self.ok = ok
        self.details = details or {}


class GraphReadiness:
    """Neo4j graph readiness evaluation result."""

    def __init__(
        self,
        ready: bool,
        checks: dict[str, ReadinessCheckResult],
        blocking_reasons: list[str],
    ):
        self.ready = ready
        self.checks = checks
        self.blocking_reasons = blocking_reasons

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "ready": self.ready,
            "checks": {
                name: {
                    "ok": check.ok,
                    "details": check.details,
                }
                for name, check in self.checks.items()
            },
            "blocking_reasons": self.blocking_reasons,
        }


def evaluate_graph_readiness(db: Session) -> GraphReadiness:
    """
    Evaluate Neo4j graph readiness (all gates must pass).

    Checks:
    - NEO4J_ENABLED env true
    - reachable ping ok
    - schema constraints OK (unique concept_id exists)
    - node_count >= MIN_GRAPH_NODES (default 200)
    - edge_count >= MIN_GRAPH_EDGES (default 100)
    - last successful neo4j_sync_run within last 24h (configurable)
    - error budget: no failed sync runs in last 3 runs

    Returns:
        GraphReadiness with check results and blocking reasons
    """
    # Check cache
    now = time.time()
    if _readiness_cache["timestamp"] > now - READINESS_CACHE_TTL:
        cached = _readiness_cache["result"]
        if cached:
            logger.debug("Returning cached graph readiness result")
            return cached

    checks: dict[str, ReadinessCheckResult] = {}
    blocking_reasons: list[str] = []

    # Gate A: Service Health
    check_a = _check_env_enabled()
    checks["env_enabled"] = check_a
    if not check_a.ok:
        blocking_reasons.append("Neo4j not enabled in environment")

    check_b = _check_reachability()
    checks["reachable"] = check_b
    if not check_b.ok:
        blocking_reasons.append("Neo4j unreachable")

    # Gate B: Schema Integrity
    check_c = _check_schema_ok()
    checks["schema_ok"] = check_c
    if not check_c.ok:
        blocking_reasons.append("Schema constraints not present or invalid")

    # Gate C: Data Sufficiency
    check_d = _check_node_count()
    checks["node_count"] = check_d
    if not check_d.ok:
        blocking_reasons.append(
            f"Node count ({check_d.details.get('count', 0)}) below minimum ({settings.MIN_GRAPH_NODES})"
        )

    check_e = _check_edge_count()
    checks["edge_count"] = check_e
    if not check_e.ok:
        blocking_reasons.append(
            f"Edge count ({check_e.details.get('count', 0)}) below minimum ({settings.MIN_GRAPH_EDGES})"
        )

    # Gate D: Sync Freshness
    check_f = _check_sync_freshness(db)
    checks["sync_freshness"] = check_f
    if not check_f.ok:
        blocking_reasons.append(
            f"Last successful sync was {check_f.details.get('hours_ago', 'unknown')} hours ago (max {settings.GRAPH_SYNC_FRESHNESS_HOURS})"
        )

    # Gate E: Error Budget
    check_g = _check_error_budget(db)
    checks["error_budget"] = check_g
    if not check_g.ok:
        blocking_reasons.append(
            f"Recent sync failures detected ({check_g.details.get('failed_count', 0)} of last {settings.GRAPH_ERROR_BUDGET_RUNS} runs)"
        )

    ready = len(blocking_reasons) == 0

    result = GraphReadiness(ready=ready, checks=checks, blocking_reasons=blocking_reasons)

    # Cache result
    _readiness_cache["result"] = result
    _readiness_cache["timestamp"] = now

    # Log readiness result
    if ready:
        logger.info("Graph readiness check passed")
    else:
        logger.warning(f"Graph readiness check failed: {', '.join(blocking_reasons)}")

    return result


def _check_env_enabled() -> ReadinessCheckResult:
    """Check if Neo4j is enabled in environment."""
    enabled = settings.NEO4J_ENABLED
    return ReadinessCheckResult(ok=enabled, details={"enabled": enabled})


def _check_reachability() -> ReadinessCheckResult:
    """Check if Neo4j is reachable."""
    if not settings.NEO4J_ENABLED:
        return ReadinessCheckResult(ok=False, details={"enabled": False})

    is_reachable, latency_ms, ping_details = ping()
    return ReadinessCheckResult(
        ok=is_reachable,
        details={
            "reachable": is_reachable,
            "latency_ms": latency_ms,
            **ping_details,
        },
    )


def _check_schema_ok() -> ReadinessCheckResult:
    """Check if schema constraints are present."""
    if not settings.NEO4J_ENABLED:
        return ReadinessCheckResult(ok=False, details={"enabled": False})

    try:
        schema_result = ensure_constraints_and_indexes()
        schema_ok = schema_result.get("enabled", False) and len(schema_result.get("constraints_created", [])) > 0
        return ReadinessCheckResult(
            ok=schema_ok,
            details={
                "constraints_created": schema_result.get("constraints_created", []),
                "indexes_created": schema_result.get("indexes_created", []),
            },
        )
    except Exception as e:
        logger.warning(f"Schema check failed: {e}")
        return ReadinessCheckResult(ok=False, details={"error": str(e)})


def _check_node_count() -> ReadinessCheckResult:
    """Check if node count meets minimum threshold."""
    if not settings.NEO4J_ENABLED:
        return ReadinessCheckResult(ok=False, details={"enabled": False})

    try:
        health = get_graph_health()
        node_count = health.get("node_count", 0) or 0
        min_nodes = settings.MIN_GRAPH_NODES
        ok = node_count >= min_nodes
        return ReadinessCheckResult(
            ok=ok,
            details={
                "count": node_count,
                "minimum": min_nodes,
            },
        )
    except Exception as e:
        logger.warning(f"Node count check failed: {e}")
        return ReadinessCheckResult(ok=False, details={"error": str(e)})


def _check_edge_count() -> ReadinessCheckResult:
    """Check if edge count meets minimum threshold."""
    if not settings.NEO4J_ENABLED:
        return ReadinessCheckResult(ok=False, details={"enabled": False})

    try:
        health = get_graph_health()
        edge_count = health.get("edge_count", 0) or 0
        min_edges = settings.MIN_GRAPH_EDGES
        ok = edge_count >= min_edges
        return ReadinessCheckResult(
            ok=ok,
            details={
                "count": edge_count,
                "minimum": min_edges,
            },
        )
    except Exception as e:
        logger.warning(f"Edge count check failed: {e}")
        return ReadinessCheckResult(ok=False, details={"error": str(e)})


def _check_sync_freshness(db: Session) -> ReadinessCheckResult:
    """Check if last successful sync is within freshness window."""
    if not settings.NEO4J_ENABLED:
        return ReadinessCheckResult(ok=False, details={"enabled": False})

    try:
        last_success = (
            db.query(Neo4jSyncRun)
            .filter(
                Neo4jSyncRun.status == Neo4jSyncRunStatus.DONE,
                Neo4jSyncRun.run_type.in_([Neo4jSyncRunType.INCREMENTAL, Neo4jSyncRunType.FULL]),
            )
            .order_by(Neo4jSyncRun.finished_at.desc())
            .first()
        )

        if not last_success or not last_success.finished_at:
            return ReadinessCheckResult(
                ok=False,
                details={"error": "No successful sync runs found"},
            )

        hours_ago = (datetime.now(UTC) - last_success.finished_at).total_seconds() / 3600
        max_hours = settings.GRAPH_SYNC_FRESHNESS_HOURS
        ok = hours_ago <= max_hours

        return ReadinessCheckResult(
            ok=ok,
            details={
                "last_sync_at": last_success.finished_at.isoformat(),
                "hours_ago": round(hours_ago, 2),
                "max_hours": max_hours,
            },
        )
    except Exception as e:
        logger.warning(f"Sync freshness check failed: {e}")
        return ReadinessCheckResult(ok=False, details={"error": str(e)})


def _check_error_budget(db: Session) -> ReadinessCheckResult:
    """Check error budget: no failed runs in last N runs."""
    if not settings.NEO4J_ENABLED:
        return ReadinessCheckResult(ok=False, details={"enabled": False})

    try:
        recent_runs = (
            db.query(Neo4jSyncRun)
            .order_by(Neo4jSyncRun.created_at.desc())
            .limit(settings.GRAPH_ERROR_BUDGET_RUNS)
            .all()
        )

        failed_count = sum(1 for run in recent_runs if run.status == Neo4jSyncRunStatus.FAILED)
        ok = failed_count == 0

        return ReadinessCheckResult(
            ok=ok,
            details={
                "failed_count": failed_count,
                "total_checked": len(recent_runs),
                "max_allowed": 0,
            },
        )
    except Exception as e:
        logger.warning(f"Error budget check failed: {e}")
        return ReadinessCheckResult(ok=False, details={"error": str(e)})
