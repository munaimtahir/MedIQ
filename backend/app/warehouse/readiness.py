"""Warehouse/Snowflake readiness evaluation module (shadow gate)."""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.warehouse.exporter import _get_warehouse_mode
from app.models.warehouse import (
    WarehouseExportRun,
    WarehouseExportRunStatus,
    WarehouseExportRunType,
)

# Import transform run model when it exists
# from app.models.warehouse import SnowflakeTransformRun, SnowflakeTransformRunStatus

logger = logging.getLogger(__name__)

# Cache readiness result for ~30-60 seconds to prevent frequent Snowflake pings
_readiness_cache: dict[str, Any] = {"result": None, "timestamp": 0}
READINESS_CACHE_TTL = 60  # seconds


class ReadinessCheckResult:
    """Result of a single readiness check."""

    def __init__(self, ok: bool, details: dict[str, Any] | None = None):
        self.ok = ok
        self.details = details or {}


class WarehouseReadiness:
    """Warehouse/Snowflake readiness evaluation result."""

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


def evaluate_warehouse_readiness(db: Session) -> WarehouseReadiness:
    """
    Evaluate Warehouse/Snowflake readiness (all gates must pass).

    Checks:
    A) Runtime + Env:
       - warehouse_mode requested == "active"
       - SNOWFLAKE_ENABLED == true
       - FEATURE_ALLOW_SNOWFLAKE_CONNECT == true
       - Required credentials present
    B) Connectivity + Privileges:
       - Can connect to Snowflake (if allowed)
       - Can USE WAREHOUSE, USE DATABASE, USE SCHEMA
       - Has required privileges
    C) Stage + Load Surface:
       - External/internal stage exists and reachable
    D) Schema Integrity:
       - RAW tables exist for all required datasets
    E) Pipeline Sanity:
       - Last successful export_run within last N hours
       - Last transform run success within last N hours
    F) Error Budget:
       - No failed export runs in last M runs
       - No failed transform runs in last M runs

    Returns:
        WarehouseReadiness with check results and blocking reasons
    """
    # Check cache
    now = time.time()
    if _readiness_cache["timestamp"] > now - READINESS_CACHE_TTL:
        cached = _readiness_cache["result"]
        if cached:
            logger.debug("Returning cached warehouse readiness result")
            return cached

    checks: dict[str, ReadinessCheckResult] = {}
    blocking_reasons: list[str] = []

    # Get requested mode
    requested_mode, warehouse_freeze = _get_warehouse_mode(db)

    # Gate A: Runtime + Env
    check_a = _check_runtime_active(requested_mode)
    checks["runtime_active"] = check_a
    if not check_a.ok:
        blocking_reasons.append(f"Warehouse mode is '{requested_mode}' (must be 'active')")

    check_b = _check_snowflake_enabled_env()
    checks["snowflake_enabled_env"] = check_b
    if not check_b.ok:
        blocking_reasons.append("SNOWFLAKE_ENABLED is false")

    check_c = _check_feature_allow_connect()
    checks["feature_allow_connect"] = check_c
    if not check_c.ok:
        blocking_reasons.append("FEATURE_ALLOW_SNOWFLAKE_CONNECT is false (connection disabled by feature flag)")

    check_d = _check_credentials_present()
    checks["credentials"] = check_d
    if not check_d.ok:
        blocking_reasons.append(f"Missing required credentials: {', '.join(check_d.details.get('missing', []))}")

    # Gate B: Connectivity + Privileges (only if allowed to connect)
    if check_c.ok and check_d.ok:
        check_e = _check_connectivity()
        checks["connectivity"] = check_e
        if not check_e.ok:
            blocking_reasons.append(f"Snowflake connectivity failed: {check_e.details.get('error', 'unknown')}")

        check_f = _check_privileges()
        checks["privileges"] = check_f
        if not check_f.ok:
            blocking_reasons.append(f"Privilege check failed: {check_f.details.get('error', 'unknown')}")
    else:
        # Skip connectivity/privilege checks if not allowed to connect
        checks["connectivity"] = ReadinessCheckResult(
            ok=False,
            details={"reason": "snowflake_connect_disabled_by_feature_flag"},
        )
        checks["privileges"] = ReadinessCheckResult(
            ok=False,
            details={"reason": "snowflake_connect_disabled_by_feature_flag"},
        )

    # Gate C: Stage + Load Surface (only if connectivity passed)
    if checks.get("connectivity", ReadinessCheckResult(ok=False)).ok:
        check_g = _check_stage()
        checks["stage"] = check_g
        if not check_g.ok:
            blocking_reasons.append(f"Stage check failed: {check_g.details.get('error', 'unknown')}")
    else:
        checks["stage"] = ReadinessCheckResult(
            ok=False,
            details={"reason": "connectivity_not_passed"},
        )

    # Gate D: Schema Integrity (only if connectivity passed)
    if checks.get("connectivity", ReadinessCheckResult(ok=False)).ok:
        check_h = _check_schema_integrity()
        checks["schema_integrity"] = check_h
        if not check_h.ok:
            missing = check_h.details.get("missing", [])
            blocking_reasons.append(f"Schema missing tables: {', '.join(missing)}")
    else:
        checks["schema_integrity"] = ReadinessCheckResult(
            ok=False,
            details={"reason": "connectivity_not_passed"},
        )

    # Gate E: Pipeline Sanity
    check_i = _check_pipeline_sanity(db)
    checks["pipeline_sanity"] = check_i
    if not check_i.ok:
        blocking_reasons.append(
            f"Pipeline sanity check failed: {check_i.details.get('error', 'unknown')}"
        )

    # Gate F: Error Budget
    check_j = _check_error_budget(db)
    checks["error_budget"] = check_j
    if not check_j.ok:
        recent_failures = check_j.details.get("recent_failures", 0)
        blocking_reasons.append(
            f"Error budget exceeded: {recent_failures} failed runs in last {settings.WAREHOUSE_ERROR_BUDGET_RUNS} runs"
        )

    # All checks must pass
    ready = all(check.ok for check in checks.values())

    result = WarehouseReadiness(
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
            "Warehouse readiness passed",
            extra={
                "readiness_passed": True,
                "blocking_reasons": [],
            },
        )
    else:
        logger.warning(
            "Warehouse readiness blocked",
            extra={
                "readiness_blocked": True,
                "blocking_reasons": blocking_reasons,
            },
        )

    return result


def _check_runtime_active(requested_mode: str) -> ReadinessCheckResult:
    """Check A1: Runtime - warehouse_mode requested == 'active'."""
    ok = requested_mode == "active"
    return ReadinessCheckResult(
        ok=ok,
        details={"requested_mode": requested_mode, "required": "active"},
    )


def _check_snowflake_enabled_env() -> ReadinessCheckResult:
    """Check A2: Env - SNOWFLAKE_ENABLED == true."""
    enabled = settings.SNOWFLAKE_ENABLED
    return ReadinessCheckResult(
        ok=enabled,
        details={"enabled": enabled},
    )


def _check_feature_allow_connect() -> ReadinessCheckResult:
    """Check A3: Feature flag - FEATURE_ALLOW_SNOWFLAKE_CONNECT == true."""
    allowed = settings.FEATURE_ALLOW_SNOWFLAKE_CONNECT
    return ReadinessCheckResult(
        ok=allowed,
        details={"allowed": allowed},
    )


def _check_credentials_present() -> ReadinessCheckResult:
    """Check A4: Required credentials present."""
    required_vars = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
    ]
    missing = []
    for var in required_vars:
        value = getattr(settings, var, None)
        if not value:
            missing.append(var)

    ok = len(missing) == 0
    return ReadinessCheckResult(
        ok=ok,
        details={"missing": missing, "present": [v for v in required_vars if v not in missing]},
    )


def _check_connectivity() -> ReadinessCheckResult:
    """
    Check B1: Connectivity - Can connect to Snowflake with short timeout.

    IMPORTANT: Only called if FEATURE_ALLOW_SNOWFLAKE_CONNECT=true.
    For now, this is a stub that returns not_attempted.
    Actual Snowflake connection will be implemented when loader is built.
    """
    # TODO: Implement actual Snowflake connection check when loader is ready
    # For now, return not_attempted to indicate check is deferred
    return ReadinessCheckResult(
        ok=False,
        details={
            "reason": "not_implemented",
            "note": "Snowflake connectivity check deferred until loader is built",
        },
    )


def _check_privileges() -> ReadinessCheckResult:
    """
    Check B2: Privileges - Can USE WAREHOUSE, USE DATABASE, USE SCHEMA, and has required privileges.

    IMPORTANT: Only called if connectivity passed.
    For now, this is a stub.
    """
    # TODO: Implement actual privilege check when loader is ready
    return ReadinessCheckResult(
        ok=False,
        details={
            "reason": "not_implemented",
            "note": "Privilege check deferred until loader is built",
        },
    )


def _check_stage() -> ReadinessCheckResult:
    """
    Check C: Stage + Load Surface - External/internal stage exists and reachable.

    IMPORTANT: Only called if connectivity passed.
    For now, this is a stub.
    """
    # TODO: Implement actual stage check when loader is ready
    return ReadinessCheckResult(
        ok=False,
        details={
            "reason": "not_implemented",
            "note": "Stage check deferred until loader is built",
        },
    )


def _check_schema_integrity() -> ReadinessCheckResult:
    """
    Check D: Schema Integrity - RAW tables exist for all required datasets.

    Required tables:
    - RAW_FACT_ATTEMPT
    - RAW_FACT_EVENT
    - RAW_SNAPSHOT_MASTERY
    - RAW_SNAPSHOT_REVISION_QUEUE_DAILY
    - RAW_DIM_QUESTION
    - RAW_DIM_SYLLABUS

    IMPORTANT: Only called if connectivity passed.
    For now, this is a stub.
    """
    # TODO: Implement actual schema check when loader is ready
    required_tables = [
        "RAW_FACT_ATTEMPT",
        "RAW_FACT_EVENT",
        "RAW_SNAPSHOT_MASTERY",
        "RAW_SNAPSHOT_REVISION_QUEUE_DAILY",
        "RAW_DIM_QUESTION",
        "RAW_DIM_SYLLABUS",
    ]
    return ReadinessCheckResult(
        ok=False,
        details={
            "reason": "not_implemented",
            "required_tables": required_tables,
            "missing": required_tables,  # Assume all missing until check is implemented
            "note": "Schema integrity check deferred until loader is built",
        },
    )


def _check_pipeline_sanity(db: Session) -> ReadinessCheckResult:
    """
    Check E: Pipeline Sanity.

    - Last successful export_run within last N hours (default 24)
    - Last transform run success within last N hours (default 24)
    """
    try:
        # Check last successful export run
        last_export = (
            db.query(WarehouseExportRun)
            .filter(
                WarehouseExportRun.status.in_(
                    [WarehouseExportRunStatus.DONE, WarehouseExportRunStatus.SHADOW_DONE_FILES_ONLY]
                )
            )
            .order_by(WarehouseExportRun.finished_at.desc())
            .first()
        )

        max_age_hours = settings.WAREHOUSE_PIPELINE_FRESHNESS_HOURS
        cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)

        export_ok = False
        last_export_at = None
        if last_export and last_export.finished_at and last_export.finished_at >= cutoff:
            export_ok = True
            last_export_at = last_export.finished_at.isoformat()

        # Check last transform run (stub for now)
        # TODO: Query snowflake_transform_run when table exists
        transform_ok = False
        last_transform_at = None
        if settings.FEATURE_TRANSFORMS_OPTIONAL:
            # If transforms are optional, treat as OK if not implemented
            transform_ok = True
            last_transform_at = None
        else:
            # For now, assume transforms not implemented yet
            transform_ok = False
            last_transform_at = None

        ok = export_ok and (transform_ok or settings.FEATURE_TRANSFORMS_OPTIONAL)

        return ReadinessCheckResult(
            ok=ok,
            details={
                "last_export_at": last_export_at,
                "last_transform_at": last_transform_at,
                "max_age_hours": max_age_hours,
                "export_ok": export_ok,
                "transform_ok": transform_ok,
                "transforms_optional": settings.FEATURE_TRANSFORMS_OPTIONAL,
            },
        )
    except Exception as e:
        logger.debug(f"Failed to check pipeline sanity: {e}")
        return ReadinessCheckResult(ok=False, details={"error": str(e)})


def _check_error_budget(db: Session) -> ReadinessCheckResult:
    """
    Check F: Error Budget.

    - No failed export runs in last M runs (default 3)
    - No failed transform runs in last M runs (default 3)
    """
    try:
        max_runs = settings.WAREHOUSE_ERROR_BUDGET_RUNS

        # Check export runs
        recent_export_runs = (
            db.query(WarehouseExportRun)
            .order_by(WarehouseExportRun.created_at.desc())
            .limit(max_runs)
            .all()
        )

        failed_export_count = sum(
            1 for run in recent_export_runs if run.status == WarehouseExportRunStatus.FAILED
        )

        # Check transform runs (stub for now)
        # TODO: Query snowflake_transform_run when table exists
        failed_transform_count = 0

        total_failures = failed_export_count + failed_transform_count
        ok = total_failures == 0

        return ReadinessCheckResult(
            ok=ok,
            details={
                "recent_failures": total_failures,
                "export_failures": failed_export_count,
                "transform_failures": failed_transform_count,
                "total_checked": len(recent_export_runs),
                "max_runs_checked": max_runs,
            },
        )
    except Exception as e:
        logger.debug(f"Failed to check error budget: {e}")
        return ReadinessCheckResult(ok=False, details={"error": str(e)})
