"""Ranking service: compute_ranking, parity harness, persist (Task 145)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ranking_mock import MockRanking, MockResult, RankingRun, RankingRunStatus
from app.ranking.go_client import GoRankingDisabledError, rank_via_go
from app.ranking.python_ranker import rank_by_percent
from app.ranking.runtime import (
    ENGINE_GO_ACTIVE,
    ENGINE_GO_SHADOW,
    ENGINE_PYTHON,
    get_effective_ranking_engine,
    get_ranking_mode,
    is_ranking_frozen,
)

logger = logging.getLogger(__name__)


def _fetch_results(db: Session, mock_instance_id: UUID) -> list[tuple[UUID, float]]:
    """Fetch (user_id, percent) for mock_instance from mock_result."""
    stmt = select(MockResult).where(MockResult.mock_instance_id == mock_instance_id)
    rows = db.execute(stmt).scalars().all()
    return [(r.user_id, r.percent) for r in rows]


def _compute_parity_report(
    python_results: list[tuple[UUID, int, float]],
    go_results: list[tuple[UUID, int, float]],
) -> dict:
    """Compute max_abs_percentile_diff and count_mismatch_ranks."""
    by_user_py = {uid: (rank, pct) for uid, rank, pct in python_results}
    by_user_go = {uid: (rank, pct) for uid, rank, pct in go_results}

    max_abs = 0.0
    mismatch = 0
    for uid, (_, py_pct) in by_user_py.items():
        if uid not in by_user_go:
            continue
        _, go_pct = by_user_go[uid]
        diff = abs(py_pct - go_pct)
        if diff > max_abs:
            max_abs = diff
    for uid, (py_rank, _) in by_user_py.items():
        if uid not in by_user_go:
            continue
        go_rank, _ = by_user_go[uid]
        if py_rank != go_rank:
            mismatch += 1

    return {
        "max_abs_percentile_diff": max_abs,
        "count_mismatch_ranks": mismatch,
        "n_users": len(by_user_py),
    }


def _upsert_rankings(
    db: Session,
    mock_instance_id: UUID,
    cohort_id: str,
    results: list[tuple[UUID, int, float]],
    engine_used: str,
) -> None:
    """Insert or update mock_ranking rows."""
    now = datetime.now(UTC)
    for user_id, rank, percentile in results:
        stmt = select(MockRanking).where(
            MockRanking.mock_instance_id == mock_instance_id,
            MockRanking.cohort_id == cohort_id,
            MockRanking.user_id == user_id,
            MockRanking.engine_used == engine_used,
        )
        r = db.execute(stmt).scalars().first()
        if r:
            r.rank = rank
            r.percentile = percentile
            r.computed_at = now
        else:
            row = MockRanking(
                mock_instance_id=mock_instance_id,
                cohort_id=cohort_id,
                user_id=user_id,
                rank=rank,
                percentile=percentile,
                engine_used=engine_used,
                computed_at=now,
            )
            db.add(row)


def compute_ranking(
    db: Session,
    mock_instance_id: UUID,
    cohort_id: str,
    engine_requested: str | None,
    actor_id: UUID | None,
) -> UUID:
    """
    Compute ranking for (mock_instance_id, cohort_id). Creates ranking_run, persists mock_ranking.

    - Respects ranking_mode, freeze, effective engine.
    - go_shadow: run python + go, store both, parity_report on run; python authoritative for UI.
    - go_active: use go only if readiness ok, else fallback python.

    Returns:
        ranking_run id.
    """
    mode = get_ranking_mode(db)
    if mode == "disabled":
        raise ValueError("Ranking is disabled")

    if is_ranking_frozen(db):
        raise ValueError("Ranking updates frozen (freeze flag)")

    effective, warnings = get_effective_ranking_engine(db, requested_mode=engine_requested or mode)
    if warnings:
        logger.info("Ranking effective engine warnings: %s", warnings)

    items = _fetch_results(db, mock_instance_id)
    n_users = len(items)

    run = RankingRun(
        mock_instance_id=mock_instance_id,
        cohort_id=cohort_id,
        status=RankingRunStatus.RUNNING.value,
        engine_requested=engine_requested or mode,
        engine_effective=None,
        started_at=datetime.now(UTC),
        n_users=n_users,
    )
    db.add(run)
    db.flush()

    try:
        python_results = rank_by_percent(items)
        _upsert_rankings(db, mock_instance_id, cohort_id, python_results, ENGINE_PYTHON)

        parity_report = None
        go_ran = False

        if mode == "go_shadow":
            run.engine_effective = ENGINE_PYTHON  # authoritative for UI
            try:
                go_results = rank_via_go(cohort_id, items)
                go_ran = True
                _upsert_rankings(db, mock_instance_id, cohort_id, go_results, ENGINE_GO_SHADOW)
                parity_report = _compute_parity_report(python_results, go_results)
            except GoRankingDisabledError:
                logger.debug("Go ranking disabled, skip shadow")
            except Exception as e:
                logger.warning("Go shadow rank failed: %s", e)
                run.last_error = str(e)
                run.status = RankingRunStatus.DONE.value
                run.finished_at = datetime.now(UTC)
                run.parity_report = {"error": str(e)}
                db.commit()
                return run.id

        elif mode == "go_active" and effective == ENGINE_GO_ACTIVE:
            try:
                go_results = rank_via_go(cohort_id, items)
                go_ran = True
                _upsert_rankings(db, mock_instance_id, cohort_id, go_results, ENGINE_GO_ACTIVE)
                run.engine_effective = ENGINE_GO_ACTIVE
            except Exception as e:
                logger.warning("Go active rank failed, fallback to python: %s", e)
                run.last_error = str(e)
                run.engine_effective = ENGINE_PYTHON
        else:
            run.engine_effective = ENGINE_PYTHON

        if not run.engine_effective:
            run.engine_effective = ENGINE_PYTHON
        run.status = RankingRunStatus.DONE.value
        run.finished_at = datetime.now(UTC)
        run.parity_report = parity_report
        db.commit()
        return run.id

    except Exception as e:
        run.status = RankingRunStatus.FAILED.value
        run.finished_at = datetime.now(UTC)
        run.last_error = str(e)
        db.commit()
        raise
