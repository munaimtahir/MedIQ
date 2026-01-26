"""Tests for IRT (Item Response Theory) subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import numpy as np
import pytest

from app.learning_engine.irt.prob import p_2pl, p_3pl
from app.learning_engine.irt.fit import fit_irt


@dataclass
class FakeRow:
    user_id: object
    question_id: object
    correct: int
    option_count: int = 5


def test_p_2pl_constraints():
    """2PL: P = sigmoid(a*(theta - b)); a must be > 0."""
    # a > 0 enforced by softplus in fit; prob uses raw a
    theta, b = 0.0, 0.0
    p = p_2pl(theta, 1.0, b)
    assert 0 <= p <= 1
    p = p_2pl(theta, 0.5, b)
    assert 0 <= p <= 1
    p = p_2pl(theta, 2.0, b)
    assert 0 <= p <= 1


def test_p_3pl_constraints():
    """3PL: P = c + (1-c)*sigmoid(...); c in [0, 1/K]."""
    theta, a, b = 0.0, 1.0, 0.0
    for k in (1, 2, 5):
        c = 1.0 / k
        p = p_3pl(theta, a, b, c)
        assert 0 <= p <= 1
        assert c <= p


def test_fit_irt_a_always_positive():
    """Fitted a must be > 0 for all items."""
    rng = np.random.default_rng(42)
    u1, u2 = uuid4(), uuid4()
    q1, q2 = uuid4(), uuid4()
    rows = []
    for _ in range(100):
        ui = u1 if rng.random() < 0.5 else u2
        qi = q1 if rng.random() < 0.5 else q2
        correct = 1 if rng.random() < 0.6 else 0
        rows.append(FakeRow(user_id=ui, question_id=qi, correct=correct, option_count=5))
    res = fit_irt(rows, "IRT_2PL", seed=42)
    for qid, a in res.item_a.items():
        assert a > 0, f"a must be positive, got {a}"


def test_fit_irt_c_within_bounds():
    """3PL: c in [0, 1/K] for all items."""
    rng = np.random.default_rng(43)
    u1, u2 = uuid4(), uuid4()
    q1, q2 = uuid4(), uuid4()
    k = 5
    rows = []
    for _ in range(100):
        ui = u1 if rng.random() < 0.5 else u2
        qi = q1 if rng.random() < 0.5 else q2
        correct = 1 if rng.random() < 0.5 else 0
        rows.append(FakeRow(user_id=ui, question_id=qi, correct=correct, option_count=k))
    res = fit_irt(rows, "IRT_3PL", seed=43)
    cap = 1.0 / k
    for qid, c in res.item_c.items():
        assert 0 <= c <= cap + 1e-6, f"c must be in [0, 1/K], got {c}"


def test_fit_irt_synthetic_recovery():
    """Generate synthetic 2PL data, fit, verify directional recovery."""
    rng = np.random.default_rng(44)
    n_user, n_item = 20, 10
    users = [uuid4() for _ in range(n_user)]
    items = [uuid4() for _ in range(n_item)]
    true_theta = rng.standard_normal(n_user)
    true_a = np.exp(rng.standard_normal(n_item) * 0.3 + 0)
    true_b = rng.standard_normal(n_item)
    true_a = np.maximum(true_a, 0.2)
    rows = []
    for _ in range(400):
        ui = rng.integers(0, n_user)
        qi = rng.integers(0, n_item)
        th = true_theta[ui]
        a, b = true_a[qi], true_b[qi]
        p = 1.0 / (1.0 + np.exp(-a * (th - b)))
        correct = 1 if rng.random() < p else 0
        rows.append(
            FakeRow(
                user_id=users[ui],
                question_id=items[qi],
                correct=correct,
                option_count=5,
            )
        )
    res = fit_irt(rows, "IRT_2PL", seed=44)
    # Correlation between true and fitted b
    fit_b = np.array([res.item_b[q] for q in items])
    corr_b = np.corrcoef(true_b, fit_b)[0, 1]
    assert not np.isnan(corr_b), "b correlation should be defined"
    assert corr_b > 0.3, f"Expected positive correlation for b, got {corr_b}"
    # Theta correlation
    fit_th = np.array([res.user_theta[u] for u in users])
    corr_th = np.corrcoef(true_theta, fit_th)[0, 1]
    assert not np.isnan(corr_th), "theta correlation should be defined"
    assert corr_th > 0.3, f"Expected positive correlation for theta, got {corr_th}"


def test_fit_irt_determinism():
    """Same seed + same dataset_spec -> same metrics/params within tolerance."""
    rng = np.random.default_rng(99)
    users = [uuid4(), uuid4()]
    items = [uuid4(), uuid4()]
    rows = []
    for _ in range(80):
        ui = users[rng.integers(0, 2)]
        qi = items[rng.integers(0, 2)]
        correct = rng.integers(0, 2)
        rows.append(FakeRow(user_id=ui, question_id=qi, correct=correct, option_count=5))
    res1 = fit_irt(rows, "IRT_2PL", seed=123)
    res2 = fit_irt(rows, "IRT_2PL", seed=123)
    assert abs(res1.neg_loglik - res2.neg_loglik) < 1e-9
    for q in items:
        assert abs(res1.item_a[q] - res2.item_a[q]) < 1e-9
        assert abs(res1.item_b[q] - res2.item_b[q]) < 1e-9
    for u in users:
        assert abs(res1.user_theta[u] - res2.user_theta[u]) < 1e-9


def test_admin_irt_require_admin_raises_for_student():
    """require_admin raises 403 for student role."""
    from fastapi import HTTPException

    from app.api.v1.endpoints.admin_irt import require_admin

    class FakeUser:
        role = "STUDENT"

    student = FakeUser()
    with pytest.raises(HTTPException) as exc:
        require_admin(student)
    assert exc.value.status_code == 403
    assert "Admin" in (exc.value.detail or "")
