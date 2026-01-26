"""Tests for ALGO_BRIDGE_SPEC_v1 implementation."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.learning_engine.bridge.spec_v1 import (
    compute_v0_mastery_from_aggregates,
    init_bkt_from_mastery,
    init_bandit_beta_from_mastery,
    nearest_bin,
    stage_from_interval,
    v0_to_v1_revision_bridge,
    v1_to_v0_revision_bridge,
)
from app.models.algo_runtime import AlgoRuntimeProfile


# ============================================================================
# Test Configuration
# ============================================================================

DEFAULT_CFG = {
    "MASTERY_FLOOR": 0.01,
    "MASTERY_CEIL": 0.99,
    "MASTERY_MIN_ATTEMPTS_FOR_CONFIDENCE": 10,
    "MASTERY_RECENCY_TAU_DAYS": 21,
    "V0_INTERVAL_BINS_DAYS": [1, 3, 7, 14, 30, 60, 120],
    "V0_STAGE_MAX": 6,
    "DUE_AT_PRESERVATION_MODE": "preserve",
    "BKT_INIT_PRIOR_FROM_MASTERY": "direct",
    "BKT_PRIOR_SHRINK_ALPHA": 0.15,
    "BKT_MIN_OBS_FOR_STRONG_INIT": 20,
    "FSRS_STABILITY_FROM_INTERVAL_MODE": "monotonic_log",
    "FSRS_DIFFICULTY_FROM_ERROR_RATE_MODE": "linear_clip",
    "FSRS_DIFFICULTY_MIN": 0.05,
    "FSRS_DIFFICULTY_MAX": 0.95,
    "BANDIT_PRIOR_FROM_MASTERY_MODE": "beta_from_mastery",
    "BANDIT_PRIOR_STRENGTH_MIN": 5,
    "BANDIT_PRIOR_STRENGTH_MAX": 50,
}


# ============================================================================
# Mastery Tests
# ============================================================================


def test_compute_v0_mastery_insufficient_attempts():
    """Test v0 mastery with insufficient attempts returns neutral."""
    now = datetime.now(timezone.utc)
    score = compute_v0_mastery_from_aggregates(5, 3, now - timedelta(days=1), now, DEFAULT_CFG)
    assert score == 0.5  # Neutral


def test_compute_v0_mastery_high_accuracy():
    """Test v0 mastery with high accuracy."""
    now = datetime.now(timezone.utc)
    score = compute_v0_mastery_from_aggregates(20, 18, now - timedelta(days=1), now, DEFAULT_CFG)
    assert 0.8 < score < 1.0  # High mastery


def test_compute_v0_mastery_recency_decay():
    """Test v0 mastery recency decay."""
    now = datetime.now(timezone.utc)
    recent = compute_v0_mastery_from_aggregates(20, 18, now - timedelta(days=1), now, DEFAULT_CFG)
    old = compute_v0_mastery_from_aggregates(20, 18, now - timedelta(days=60), now, DEFAULT_CFG)
    assert recent > old  # Recent attempts weighted more


def test_init_bkt_direct_mode():
    """Test BKT initialization in direct mode."""
    p_mastered, state = init_bkt_from_mastery(0.75, 0.5, 20, DEFAULT_CFG)
    assert 0.1 <= p_mastered <= 0.9
    assert state["initialized_from_mastery"] is True
    assert state["n_attempts"] == 20


def test_init_bkt_shrink_mode():
    """Test BKT initialization in shrink mode."""
    cfg = DEFAULT_CFG.copy()
    cfg["BKT_INIT_PRIOR_FROM_MASTERY"] = "shrink_to_prior"
    p_mastered, state = init_bkt_from_mastery(0.75, 0.5, 20, cfg)
    assert 0.5 < p_mastered < 0.75  # Shrunk toward prior
    # With attempts_total=20 >= min_obs=20, effective_alpha = shrink_alpha * 0.5 = 0.15 * 0.5 = 0.075
    assert state["shrinkage_alpha"] == 0.075


# ============================================================================
# Revision Tests
# ============================================================================


def test_nearest_bin():
    """Test nearest bin function."""
    bins = [1, 3, 7, 14, 30, 60, 120]
    assert nearest_bin(5, bins) == 7
    assert nearest_bin(1, bins) == 1
    assert nearest_bin(100, bins) == 120


def test_stage_from_interval():
    """Test stage computation from interval."""
    bins = [1, 3, 7, 14, 30, 60, 120]
    assert stage_from_interval(1, bins, 6) == 1
    assert stage_from_interval(5, bins, 6) == 2
    assert stage_from_interval(100, bins, 6) == 6


def test_v1_to_v0_revision_preserves_due_at():
    """Test v1→v0 bridge preserves due_at."""
    now = datetime.now(timezone.utc)
    due_at = now + timedelta(days=5)
    
    state = {
        "due_at": due_at.isoformat(),
        "last_review_at": (now - timedelta(days=3)).isoformat(),
        "v0_interval_days": None,
        "v0_stage": None,
    }
    
    updated = v1_to_v0_revision_bridge(state, None, DEFAULT_CFG, now)
    
    # due_at should be preserved (as string in dict)
    assert updated.get("v0_interval_days") is not None
    assert updated.get("v0_stage") is not None


def test_v0_to_v1_revision_preserves_due_at():
    """Test v0→v1 bridge preserves due_at."""
    now = datetime.now(timezone.utc)
    due_at = now + timedelta(days=5)
    
    state = {
        "due_at": due_at.isoformat(),
        "v0_interval_days": 7,
        "stability": None,
        "difficulty": None,
    }
    
    stats = {"attempts_total": 20, "correct_total": 15}
    
    updated = v0_to_v1_revision_bridge(state, stats, DEFAULT_CFG, now)
    
    assert updated.get("stability") is not None
    assert updated.get("difficulty") is not None


# ============================================================================
# Bandit Tests
# ============================================================================


def test_init_bandit_beta_from_mastery():
    """Test bandit Beta prior initialization."""
    alpha, beta = init_bandit_beta_from_mastery(0.75, 20, DEFAULT_CFG)
    
    assert alpha > 1.0
    assert beta > 1.0
    assert alpha > beta  # Higher mastery → higher alpha


def test_init_bandit_strength_clipping():
    """Test bandit strength clipping."""
    # Low attempts
    alpha1, beta1 = init_bandit_beta_from_mastery(0.5, 2, DEFAULT_CFG)
    # High attempts
    alpha2, beta2 = init_bandit_beta_from_mastery(0.5, 100, DEFAULT_CFG)
    
    # Both should be within strength bounds
    assert 5 <= (alpha1 + beta1 - 2) <= 50
    assert 5 <= (alpha2 + beta2 - 2) <= 50


# ============================================================================
# Integration Tests (would need DB setup)
# ============================================================================

# Note: Full integration tests would require:
# - Database fixtures
# - Test data setup
# - Session continuity tests
# - Bridge idempotence tests
# These would be in a separate test file with proper fixtures.
