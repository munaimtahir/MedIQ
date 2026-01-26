"""Elasticsearch readiness evaluation module (shadow gate)."""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.question_cms import Question, QuestionStatus
from app.models.search_indexing import SearchSyncRun, SearchSyncRunStatus, SearchSyncRunType
from app.search.es_client import get_es_client, ping
from app.search.index_bootstrap import get_current_questions_index, get_questions_read_alias

logger = logging.getLogger(__name__)

# Cache readiness result for ~30 seconds to avoid hammering ES
_readiness_cache: dict[str, Any] = {"result": None, "timestamp": 0}
READINESS_CACHE_TTL = 30  # seconds


class ReadinessCheckResult:
    """Result of a single readiness check."""

    def __init__(self, ok: bool, details: dict[str, Any] | None = None):
        self.ok = ok
        self.details = details or {}


class ElasticsearchReadiness:
    """Elasticsearch readiness evaluation result."""

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


def evaluate_elasticsearch_readiness(db: Session) -> ElasticsearchReadiness:
    """
    Evaluate Elasticsearch readiness (all gates must pass).

    Returns:
        ElasticsearchReadiness with check results and blocking reasons
    """
    # Check cache
    now = time.time()
    if _readiness_cache["timestamp"] > now - READINESS_CACHE_TTL:
        cached = _readiness_cache["result"]
        if cached:
            logger.debug("Returning cached readiness result")
            return cached

    checks: dict[str, ReadinessCheckResult] = {}
    blocking_reasons: list[str] = []

    # Gate A: Service Health
    check_a = _check_service_health()
    checks["env_enabled"] = check_a
    if not check_a.ok:
        blocking_reasons.append("Elasticsearch not enabled in environment")

    check_b = _check_reachability()
    checks["reachable"] = check_b
    if not check_b.ok:
        blocking_reasons.append("Elasticsearch unreachable")

    # Gate B: Index Integrity
    check_c = _check_alias_exists()
    checks["alias_exists"] = check_c
    if not check_c.ok:
        blocking_reasons.append("questions_read alias does not exist")

    check_d = _check_index_health()
    checks["index_health"] = check_d
    if not check_d.ok:
        blocking_reasons.append(f"Index health is {check_d.details.get('status', 'unknown')} (must be green or yellow)")

    # Gate C: Data Sufficiency
    check_e = _check_doc_count(db)
    checks["doc_count"] = check_e
    if not check_e.ok:
        blocking_reasons.append(
            f"Insufficient documents: {check_e.details.get('count', 0)} < {check_e.details.get('expected_min', 0)}"
        )

    # Gate D: Sync Freshness
    check_f = _check_sync_freshness(db)
    checks["sync_freshness"] = check_f
    if not check_f.ok:
        blocking_reasons.append(
            f"Last successful sync too old: {check_f.details.get('last_run_at', 'never')}"
        )

    # Gate E: Error Budget
    check_g = _check_error_budget(db)
    checks["error_budget"] = check_g
    if not check_g.ok:
        blocking_reasons.append(
            f"Recent failures detected: {check_g.details.get('recent_failures', 0)} failed runs in last {settings.ELASTICSEARCH_ERROR_BUDGET_RUNS} runs"
        )

    # All checks must pass
    ready = all(check.ok for check in checks.values())

    result = ElasticsearchReadiness(
        ready=ready,
        checks=checks,
        blocking_reasons=blocking_reasons,
    )

    # Cache result
    _readiness_cache["result"] = result
    _readiness_cache["timestamp"] = now

    # Audit logging
    if ready:
        logger.info(
            "Elasticsearch readiness passed",
            extra={
                "readiness_passed": True,
                "blocking_reasons": [],
            },
        )
    else:
        logger.warning(
            "Elasticsearch readiness blocked",
            extra={
                "readiness_blocked": True,
                "blocking_reasons": blocking_reasons,
            },
        )

    return result


def _check_service_health() -> ReadinessCheckResult:
    """Check A: Service Health - ELASTICSEARCH_ENABLED == true."""
    enabled = settings.ELASTICSEARCH_ENABLED
    return ReadinessCheckResult(
        ok=enabled,
        details={"enabled": enabled},
    )


def _check_reachability() -> ReadinessCheckResult:
    """Check B: Service Health - ES reachable (ping success within timeout)."""
    if not settings.ELASTICSEARCH_ENABLED:
        return ReadinessCheckResult(ok=False, details={"reachable": False, "reason": "disabled"})

    try:
        start = time.time()
        is_reachable = ping()
        latency_ms = int((time.time() - start) * 1000)
        return ReadinessCheckResult(
            ok=is_reachable,
            details={"reachable": is_reachable, "latency_ms": latency_ms if is_reachable else None},
        )
    except Exception as e:
        logger.debug(f"ES ping failed: {e}")
        return ReadinessCheckResult(ok=False, details={"reachable": False, "error": str(e)})


def _check_alias_exists() -> ReadinessCheckResult:
    """Check C: Index Integrity - questions_read alias exists and points to concrete index."""
    if not settings.ELASTICSEARCH_ENABLED:
        return ReadinessCheckResult(ok=False, details={"alias": None, "index": None})

    client = get_es_client()
    if client is None:
        return ReadinessCheckResult(ok=False, details={"alias": None, "index": None, "reason": "client_unavailable"})

    try:
        read_alias = get_questions_read_alias()
        current_index = get_current_questions_index()

        if current_index is None:
            return ReadinessCheckResult(
                ok=False,
                details={"alias": read_alias, "index": None, "reason": "alias_points_to_nothing"},
            )

        # Verify alias actually points to this index
        aliases = client.indices.get_alias(name=read_alias)
        if not aliases or current_index not in aliases:
            return ReadinessCheckResult(
                ok=False,
                details={"alias": read_alias, "index": current_index, "reason": "alias_mismatch"},
            )

        return ReadinessCheckResult(
            ok=True,
            details={"alias": read_alias, "index": current_index},
        )
    except Exception as e:
        logger.debug(f"Failed to check alias: {e}")
        return ReadinessCheckResult(ok=False, details={"alias": None, "index": None, "error": str(e)})


def _check_index_health() -> ReadinessCheckResult:
    """Check D: Index Integrity - index health is green or yellow (NOT red)."""
    if not settings.ELASTICSEARCH_ENABLED:
        return ReadinessCheckResult(ok=False, details={"status": "unknown", "reason": "disabled"})

    client = get_es_client()
    if client is None:
        return ReadinessCheckResult(ok=False, details={"status": "unknown", "reason": "client_unavailable"})

    try:
        current_index = get_current_questions_index()
        if current_index is None:
            return ReadinessCheckResult(ok=False, details={"status": "unknown", "reason": "no_index"})

        # Get cluster health (includes index health)
        cluster_health = client.cluster.health(index=current_index, level="indices")
        index_health = cluster_health.get("indices", {}).get(current_index, {}).get("status", "red")

        # Also check overall cluster health
        overall_health = cluster_health.get("status", "red")

        # Index health must be green or yellow
        is_healthy = index_health in ("green", "yellow") and overall_health in ("green", "yellow")

        return ReadinessCheckResult(
            ok=is_healthy,
            details={"status": index_health, "cluster_status": overall_health},
        )
    except Exception as e:
        logger.debug(f"Failed to check index health: {e}")
        return ReadinessCheckResult(ok=False, details={"status": "unknown", "error": str(e)})


def _check_doc_count(db: Session) -> ReadinessCheckResult:
    """Check E: Data Sufficiency - doc_count >= MIN_PUBLISHED_QUESTIONS or >= DB_COUNT * 0.95."""
    if not settings.ELASTICSEARCH_ENABLED:
        return ReadinessCheckResult(ok=False, details={"count": 0, "expected_min": 0})

    client = get_es_client()
    if client is None:
        return ReadinessCheckResult(ok=False, details={"count": 0, "expected_min": 0, "reason": "client_unavailable"})

    try:
        current_index = get_current_questions_index()
        if current_index is None:
            return ReadinessCheckResult(ok=False, details={"count": 0, "expected_min": settings.ELASTICSEARCH_MIN_PUBLISHED_QUESTIONS})

        # Get doc count from ES
        stats = client.indices.stats(index=current_index)
        es_doc_count = stats["indices"][current_index]["total"]["docs"]["count"]

        # Get published count from DB
        db_published_count = (
            db.query(func.count(Question.id))
            .filter(Question.status == QuestionStatus.PUBLISHED)
            .scalar()
            or 0
        )

        # Calculate expected minimum
        min_required = settings.ELASTICSEARCH_MIN_PUBLISHED_QUESTIONS
        tolerance_min = int(db_published_count * 0.95)

        # Must meet either absolute minimum OR 95% of DB count
        expected_min = max(min_required, tolerance_min) if db_published_count > 0 else min_required

        is_sufficient = es_doc_count >= expected_min

        return ReadinessCheckResult(
            ok=is_sufficient,
            details={
                "count": es_doc_count,
                "db_published_count": db_published_count,
                "expected_min": expected_min,
                "tolerance_min": tolerance_min,
            },
        )
    except Exception as e:
        logger.debug(f"Failed to check doc count: {e}")
        return ReadinessCheckResult(ok=False, details={"count": 0, "expected_min": settings.ELASTICSEARCH_MIN_PUBLISHED_QUESTIONS, "error": str(e)})


def _check_sync_freshness(db: Session) -> ReadinessCheckResult:
    """Check F: Sync Freshness - Last successful nightly reindex within N hours OR all outbox processed."""
    if not settings.ELASTICSEARCH_ENABLED:
        return ReadinessCheckResult(ok=False, details={"last_run_at": None})

    try:
        # Check last successful nightly reindex
        last_nightly = (
            db.query(SearchSyncRun)
            .filter(
                SearchSyncRun.run_type == SearchSyncRunType.NIGHTLY,
                SearchSyncRun.status == SearchSyncRunStatus.DONE,
            )
            .order_by(SearchSyncRun.finished_at.desc())
            .first()
        )

        max_age_hours = settings.ELASTICSEARCH_SYNC_FRESHNESS_HOURS
        cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)

        if last_nightly and last_nightly.finished_at and last_nightly.finished_at >= cutoff:
            # Recent successful nightly reindex
            return ReadinessCheckResult(
                ok=True,
                details={
                    "last_run_at": last_nightly.finished_at.isoformat(),
                    "run_id": str(last_nightly.id),
                    "run_type": "nightly",
                },
            )

        # Check if all outbox events are processed (no pending)
        from app.models.search_indexing import SearchOutbox, SearchOutboxStatus

        pending_count = (
            db.query(func.count(SearchOutbox.id))
            .filter(SearchOutbox.status == SearchOutboxStatus.PENDING)
            .scalar()
            or 0
        )

        if pending_count == 0 and last_nightly:
            # All incremental syncs processed, and we have at least one nightly run
            return ReadinessCheckResult(
                ok=True,
                details={
                    "last_run_at": last_nightly.finished_at.isoformat() if last_nightly.finished_at else None,
                    "run_id": str(last_nightly.id),
                    "run_type": "incremental",
                    "pending_outbox": 0,
                },
            )

        # Not fresh
        last_run_at = last_nightly.finished_at.isoformat() if last_nightly and last_nightly.finished_at else None
        return ReadinessCheckResult(
            ok=False,
            details={
                "last_run_at": last_run_at,
                "max_age_hours": max_age_hours,
                "pending_outbox": pending_count,
            },
        )
    except Exception as e:
        logger.debug(f"Failed to check sync freshness: {e}")
        return ReadinessCheckResult(ok=False, details={"last_run_at": None, "error": str(e)})


def _check_error_budget(db: Session) -> ReadinessCheckResult:
    """Check G: Error Budget - No failed search_sync_run in last M runs."""
    if not settings.ELASTICSEARCH_ENABLED:
        return ReadinessCheckResult(ok=False, details={"recent_failures": 0})

    try:
        max_runs = settings.ELASTICSEARCH_ERROR_BUDGET_RUNS

        # Get last M runs (any type)
        recent_runs = (
            db.query(SearchSyncRun)
            .order_by(SearchSyncRun.created_at.desc())
            .limit(max_runs)
            .all()
        )

        if not recent_runs:
            # No runs yet - consider this a pass (initial state)
            return ReadinessCheckResult(ok=True, details={"recent_failures": 0, "total_runs": 0})

        failed_count = sum(1 for run in recent_runs if run.status == SearchSyncRunStatus.FAILED)

        is_ok = failed_count == 0

        return ReadinessCheckResult(
            ok=is_ok,
            details={
                "recent_failures": failed_count,
                "total_runs": len(recent_runs),
                "max_runs_checked": max_runs,
            },
        )
    except Exception as e:
        logger.debug(f"Failed to check error budget: {e}")
        return ReadinessCheckResult(ok=False, details={"recent_failures": 0, "error": str(e)})
