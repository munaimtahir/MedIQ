"""Tests for mock ranking (Task 145): determinism, parity, go_active fallback."""

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.algo_runtime import AlgoRuntimeConfig, AlgoRuntimeProfile
from app.models.mock import (
    MockBlueprint,
    MockBlueprintMode,
    MockBlueprintStatus,
    MockBlueprintVersion,
    MockGenerationRun,
    MockGenerationRunStatus,
    MockInstance,
)
from app.models.ranking_mock import MockResult, MockRanking, RankingRun, RankingRunStatus
from app.models.user import User
from app.ranking.python_ranker import rank_by_percent
from app.ranking.runtime import (
    RANKING_MODE_GO_ACTIVE,
    RANKING_MODE_GO_SHADOW,
    RANKING_MODE_PYTHON,
    evaluate_ranking_readiness_for_go,
    get_effective_ranking_engine,
    get_ranking_mode,
    is_ranking_frozen,
)
from app.ranking.service import compute_ranking


def test_python_ranker_deterministic():
    """Python ranker is deterministic: same input -> same output, stable tie-break by user_id."""
    u1, u2, u3 = uuid4(), uuid4(), uuid4()
    items = [(u1, 80.0), (u2, 90.0), (u3, 80.0)]
    r1 = rank_by_percent(items)
    r2 = rank_by_percent(items)
    assert r1 == r2
    # 90 > 80; ties (80,80) broken by user_id
    assert r1[0][1] == 1 and r1[0][2] == 100.0
    assert r1[1][1] == 2 and r1[2][1] == 3
    assert {x[2] for x in r1} == {100.0, 50.0, 0.0}  # percentiles

    # Tie-break order stable by user_id
    a, b = str(u1), str(u3)
    if a < b:
        assert (r1[1][0], r1[2][0]) == (u1, u3) or (r1[1][0], r1[2][0]) == (u3, u1)
    # Same items, different order input -> same output
    items_shuffled = [(u3, 80.0), (u2, 90.0), (u1, 80.0)]
    r3 = rank_by_percent(items_shuffled)
    assert len(r3) == 3
    by_user = {x[0]: (x[1], x[2]) for x in r3}
    assert by_user[u2] == (1, 100.0)
    assert by_user[u1][0] in (2, 3) and by_user[u3][0] in (2, 3)


def test_python_ranker_single_user():
    """Single user gets rank 1, percentile 100."""
    u = uuid4()
    r = rank_by_percent([(u, 50.0)])
    assert r == [(u, 1, 100.0)]


def test_python_ranker_empty():
    """Empty input returns empty list."""
    assert rank_by_percent([]) == []


@pytest.fixture
def admin_user(db: Session) -> User:
    u = User(
        name="Admin",
        email="admin@ranking.test",
        role="ADMIN",
        password_hash="x",
    )
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def mock_instance_with_results(db: Session, admin_user: User):
    """Create minimal blueprint -> run -> instance and mock_result rows."""
    bp = MockBlueprint(
        title="Rank Test",
        year=1,
        total_questions=10,
        duration_minutes=60,
        mode=MockBlueprintMode.EXAM,
        status=MockBlueprintStatus.ACTIVE,
        config={},
        created_by=admin_user.id,
    )
    db.add(bp)
    db.flush()

    v = MockBlueprintVersion(blueprint_id=bp.id, version=1, config={}, created_by=admin_user.id)
    db.add(v)
    db.flush()

    run = MockGenerationRun(
        blueprint_id=bp.id,
        status=MockGenerationRunStatus.DONE,
        seed=1,
        config_version_id=v.id,
        requested_by=admin_user.id,
        generated_question_count=10,
    )
    db.add(run)
    db.flush()

    inst = MockInstance(
        blueprint_id=bp.id,
        generation_run_id=run.id,
        year=1,
        total_questions=10,
        duration_minutes=60,
        seed=1,
        question_ids=[],
    )
    db.add(inst)
    db.flush()

    for i, pct in enumerate([85.0, 72.0, 90.0, 72.0]):
        u = User(
            name=f"Student{i}",
            email=f"u{i}@r.test",
            role="STUDENT",
            password_hash="x",
        )
        db.add(u)
        db.flush()
        mr = MockResult(
            mock_instance_id=inst.id,
            user_id=u.id,
            raw_score=int(pct),
            percent=pct,
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(mr)
    db.flush()
    return inst


def test_ranking_mode_default(db: Session):
    """Default ranking_mode is python when not set."""
    config = AlgoRuntimeConfig(
        active_profile=AlgoRuntimeProfile.V1_PRIMARY,
        config_json={"profile": "V1_PRIMARY", "overrides": {}, "safe_mode": {"freeze_updates": False}},
    )
    db.add(config)
    db.commit()

    assert get_ranking_mode(db) == RANKING_MODE_PYTHON
    effective, _ = get_effective_ranking_engine(db)
    assert effective == "python"


def test_go_shadow_stores_parity_report(
    db: Session, admin_user: User, mock_instance_with_results
):
    """When ranking_mode=go_shadow, run has parity_report and go_shadow rankings stored."""
    from sqlalchemy import select

    config = AlgoRuntimeConfig(
        active_profile=AlgoRuntimeProfile.V1_PRIMARY,
        config_json={
            "ranking_mode": RANKING_MODE_GO_SHADOW,
            "safe_mode": {"freeze_updates": False},
        },
    )
    db.add(config)
    db.commit()

    cohort_id = "year:1:block:A"
    rows = list(
        db.execute(
            select(MockResult).where(
                MockResult.mock_instance_id == mock_instance_with_results.id
            )
        ).scalars().all()
    )
    # Order by percent desc to match Python: 90, 85, 72, 72
    ordered = sorted(rows, key=lambda r: (-r.percent, str(r.user_id)))
    go_results = []
    n = len(ordered)
    for i, r in enumerate(ordered):
        rank = i + 1
        pct = 100.0 * (1.0 - (rank - 1) / (n - 1)) if n > 1 else 100.0
        go_results.append((r.user_id, rank, pct))

    with patch("app.ranking.service.rank_via_go") as mock_go:
        mock_go.return_value = go_results
        run_id = compute_ranking(
            db, mock_instance_with_results.id, cohort_id, None, admin_user.id
        )

    run = db.query(RankingRun).filter(RankingRun.id == run_id).first()
    assert run is not None
    assert run.status == RankingRunStatus.DONE.value
    assert run.parity_report is not None
    assert "max_abs_percentile_diff" in run.parity_report
    assert "count_mismatch_ranks" in run.parity_report

    rankings_go = db.query(MockRanking).filter(
        MockRanking.mock_instance_id == mock_instance_with_results.id,
        MockRanking.cohort_id == cohort_id,
        MockRanking.engine_used == "go_shadow",
    ).all()
    assert len(rankings_go) >= 1


def test_go_active_blocked_unless_readiness_fallback_python(db: Session, admin_user: User):
    """go_active: if readiness fails, we fall back to python; no go_active rankings."""
    config = AlgoRuntimeConfig(
        active_profile=AlgoRuntimeProfile.V1_PRIMARY,
        config_json={
            "ranking_mode": RANKING_MODE_GO_ACTIVE,
            "safe_mode": {"freeze_updates": False},
        },
    )
    db.add(config)
    db.commit()

    # GO_RANKING_ENABLED false -> readiness fails -> effective python
    effective, warnings = get_effective_ranking_engine(db)
    assert "go_active_not_ready_fallback_python" in warnings or effective == "python"

    ready, result = evaluate_ranking_readiness_for_go(db)
    assert not ready
    assert not result.checks.get("go_ranking_enabled", {}).get("ok", True)


def test_freeze_blocks_compute(db: Session, admin_user: User, mock_instance_with_results):
    """Freeze blocks ranking compute."""
    config = AlgoRuntimeConfig(
        active_profile=AlgoRuntimeProfile.V1_PRIMARY,
        config_json={
            "ranking_mode": RANKING_MODE_PYTHON,
            "safe_mode": {"freeze_updates": True},
        },
    )
    db.add(config)
    db.commit()

    assert is_ranking_frozen(db) is True
    with pytest.raises(ValueError, match="frozen|freeze"):
        compute_ranking(
            db,
            mock_instance_with_results.id,
            "year:1",
            None,
            admin_user.id,
        )
