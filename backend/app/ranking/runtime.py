"""Ranking runtime: mode, effective engine, freeze, readiness (Task 145)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.ranking_mock import RankingRun, RankingRunStatus

logger = logging.getLogger(__name__)

RANKING_MODE_DISABLED = "disabled"
RANKING_MODE_PYTHON = "python"
RANKING_MODE_GO_SHADOW = "go_shadow"
RANKING_MODE_GO_ACTIVE = "go_active"

ENGINE_PYTHON = "python"
ENGINE_GO_SHADOW = "go_shadow"
ENGINE_GO_ACTIVE = "go_active"


def _get_ranking_config(db: Session) -> tuple[str, bool]:
    """
    Get ranking_mode and freeze from algo_runtime_config.

    Returns:
        (ranking_mode, freeze). ranking_mode default "python".
    """
    row = db.query(AlgoRuntimeConfig).order_by(AlgoRuntimeConfig.updated_at.desc()).first()
    if not row:
        return RANKING_MODE_PYTHON, False

    cfg = row.config_json or {}
    mode = cfg.get("ranking_mode", RANKING_MODE_PYTHON)
    safe = cfg.get("safe_mode", {})
    freeze = safe.get("freeze_updates", False)
    return mode, freeze


def get_ranking_mode(db: Session) -> str:
    """Return requested ranking_mode (disabled|python|go_shadow|go_active)."""
    mode, _ = _get_ranking_config(db)
    return mode


def is_ranking_frozen(db: Session) -> bool:
    """True if freeze flag is set (updates blocked)."""
    _, freeze = _get_ranking_config(db)
    return freeze


def get_effective_ranking_engine(
    db: Session,
    *,
    requested_mode: str | None = None,
) -> tuple[str, list[str]]:
    """
    Compute effective engine from requested mode, freeze, and readiness.

    Rules:
    - python => effective python
    - go_shadow => compute both, store both; python authoritative (effective python for UI)
    - go_active => only if readiness passes; else fallback python

    Returns:
        (effective_engine, warnings)
    """
    mode = requested_mode or get_ranking_mode(db)
    _, freeze = _get_ranking_config(db)
    warnings: list[str] = []

    if mode == RANKING_MODE_DISABLED:
        return ENGINE_PYTHON, warnings  # No ranking; caller may block compute

    if freeze:
        warnings.append("ranking_frozen_fallback")
        return ENGINE_PYTHON, warnings

    if mode == RANKING_MODE_PYTHON:
        return ENGINE_PYTHON, warnings

    if mode == RANKING_MODE_GO_SHADOW:
        # Shadow: we run both, but python is authoritative for UI
        return ENGINE_PYTHON, warnings

    if mode == RANKING_MODE_GO_ACTIVE:
        ready, _ = evaluate_ranking_readiness_for_go(db)
        if not ready:
            warnings.append("go_active_not_ready_fallback_python")
            return ENGINE_PYTHON, warnings
        return ENGINE_GO_ACTIVE, warnings

    return ENGINE_PYTHON, warnings


@dataclass
class RankingReadinessResult:
    """Result of ranking readiness evaluation for go_active."""

    ready: bool
    checks: dict[str, dict[str, Any]]
    blocking_reasons: list[str]


def evaluate_ranking_readiness_for_go(db: Session) -> tuple[bool, RankingReadinessResult]:
    """
    Evaluate readiness for go_active.

    Checks:
    - GO_RANKING_ENABLED env true
    - Go service health reachable
    - Parity within epsilon on last K runs (default K=10)
    - Error budget: no failures in last 3 runs

    Returns:
        (ready, RankingReadinessResult)
    """
    checks: dict[str, dict[str, Any]] = {}
    blocking: list[str] = []

    # 1) GO_RANKING_ENABLED
    go_ok = settings.GO_RANKING_ENABLED
    checks["go_ranking_enabled"] = {"ok": go_ok, "value": go_ok}
    if not go_ok:
        blocking.append("GO_RANKING_ENABLED is false")

    # 2) Service health
    health_ok = False
    try:
        from app.ranking.go_client import check_go_ranking_health

        health_ok = check_go_ranking_health()
    except Exception as e:
        logger.warning("Go ranking health check failed: %s", e)
    checks["go_service_health"] = {"ok": health_ok}
    if not health_ok:
        blocking.append("Go ranking service health check failed or disabled")

    # 3) Parity last K runs (go_shadow runs have parity_report set; engine_effective=python)
    K = settings.RANKING_PARITY_K
    eps = settings.RANKING_PARITY_EPSILON
    stmt = (
        select(RankingRun)
        .where(RankingRun.status == RankingRunStatus.DONE.value)
        .where(RankingRun.parity_report.isnot(None))
        .order_by(desc(RankingRun.created_at))
        .limit(K)
    )
    runs = list(db.execute(stmt).scalars().all())
    parity_ok = True
    for row in runs:
        pr = row.parity_report or {}
        max_diff = pr.get("max_abs_percentile_diff")
        if max_diff is not None and max_diff > eps:
            parity_ok = False
            blocking.append(
                f"Parity max_abs_percentile_diff {max_diff} > epsilon {eps} in run {row.id}"
            )
            break
    checks["parity_last_k"] = {
        "ok": parity_ok,
        "runs_checked": len(runs),
        "K": K,
        "epsilon": eps,
    }

    # 4) Error budget: no failures in last N runs (use engine_requested to include shadow)
    N = settings.RANKING_ERROR_BUDGET_RUNS
    stmt_err = (
        select(RankingRun)
        .where(
            RankingRun.engine_requested.in_(
                [RANKING_MODE_GO_SHADOW, RANKING_MODE_GO_ACTIVE]
            )
        )
        .order_by(desc(RankingRun.created_at))
        .limit(N)
    )
    err_runs = list(db.execute(stmt_err).scalars().all())
    _status = lambda r: getattr(r.status, "value", r.status) if r.status else None
    failed = sum(1 for row in err_runs if _status(row) == RankingRunStatus.FAILED.value)
    error_budget_ok = failed == 0
    checks["error_budget"] = {"ok": error_budget_ok, "failures_in_last_N": failed, "N": N}
    if not error_budget_ok:
        blocking.append(f"Found {failed} failed run(s) in last {N} go shadow/active runs")

    ready = go_ok and health_ok and parity_ok and error_budget_ok
    result = RankingReadinessResult(ready=ready, checks=checks, blocking_reasons=blocking)
    return ready, result


def get_recent_parity(db: Session) -> dict[str, Any]:
    """
    Compute recent parity summary from last K runs with parity_report.

    Returns:
        {
            "k": int,
            "pass": bool,
            "max_abs_percentile_diff": float | None,
            "rank_mismatch_count": int | None,
            "last_checked_at": str | None,  # ISO datetime of latest run
        }
    """
    K = settings.RANKING_PARITY_K
    eps = settings.RANKING_PARITY_EPSILON
    stmt = (
        select(RankingRun)
        .where(RankingRun.status == RankingRunStatus.DONE.value)
        .where(RankingRun.parity_report.isnot(None))
        .order_by(desc(RankingRun.created_at))
        .limit(K)
    )
    runs = list(db.execute(stmt).scalars().all())
    out: dict[str, Any] = {
        "k": K,
        "epsilon": eps,
        "pass": True,
        "max_abs_percentile_diff": None,
        "rank_mismatch_count": None,
        "last_checked_at": None,
    }
    if not runs:
        return out

    last = runs[0]
    out["last_checked_at"] = last.created_at.isoformat() if last.created_at else None
    max_diff = 0.0
    total_mismatch = 0
    for row in runs:
        pr = row.parity_report or {}
        d = pr.get("max_abs_percentile_diff")
        m = pr.get("count_mismatch_ranks", 0)
        if d is not None and d > max_diff:
            max_diff = d
        total_mismatch += m
    out["max_abs_percentile_diff"] = max_diff
    out["rank_mismatch_count"] = total_mismatch
    out["pass"] = max_diff <= eps and total_mismatch == 0
    return out
