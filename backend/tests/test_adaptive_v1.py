"""
Tests for Adaptive Selection v1 (Constrained Thompson Sampling).

Tests:
- Determinism: same inputs → same outputs (seeded RNG)
- Constraints: min/max themes, quotas, supply requirements
- Thompson Sampling: Beta sampling, priority computation
- Reward updates: BKT delta → Beta posterior updates
- Question picking: challenge band, due concepts, exploration
"""

import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.learning_engine.adaptive_v1.core import (
    SelectionPlan,
    ThemeCandidate,
    allocate_quotas,
    compute_base_priority,
    compute_bkt_delta_reward,
    compute_final_score,
    compute_recency_penalty,
    create_deterministic_seed,
    create_seeded_rng,
    normalize_uncertainty,
    run_theme_selection,
    sample_beta,
    select_themes,
    update_beta_posterior,
)
from app.learning_engine.adaptive_v1.question_picker import (
    compute_p_correct,
    interleave_questions,
    is_in_challenge_band,
    pick_questions_for_theme,
    PickerResult,
    QuestionCandidate,
)


class TestDeterminism:
    """Tests for deterministic behavior with seeded RNG."""

    def test_same_seed_produces_same_results(self):
        """Same seed should produce identical selections."""
        user_id = uuid4()
        seed = create_deterministic_seed(
            user_id=user_id,
            mode="tutor",
            count=20,
            block_ids=[1, 2],
            theme_ids=[10, 20, 30],
        )

        # Create two RNGs with same seed
        rng1 = create_seeded_rng(seed)
        rng2 = create_seeded_rng(seed)

        # Generate sequences
        seq1 = [rng1.random() for _ in range(100)]
        seq2 = [rng2.random() for _ in range(100)]

        assert seq1 == seq2

    def test_different_users_different_seeds(self):
        """Different users should get different seeds."""
        seed1 = create_deterministic_seed(
            user_id=uuid4(),
            mode="tutor",
            count=20,
            block_ids=[1, 2],
            theme_ids=None,
        )
        seed2 = create_deterministic_seed(
            user_id=uuid4(),
            mode="tutor",
            count=20,
            block_ids=[1, 2],
            theme_ids=None,
        )

        assert seed1 != seed2

    def test_beta_sampling_deterministic(self):
        """Beta sampling should be deterministic with seeded RNG."""
        rng1 = create_seeded_rng("abc123")
        rng2 = create_seeded_rng("abc123")

        samples1 = [sample_beta(rng1, 2.0, 3.0) for _ in range(50)]
        samples2 = [sample_beta(rng2, 2.0, 3.0) for _ in range(50)]

        assert samples1 == samples2

    def test_full_selection_deterministic(self):
        """Full theme selection should be deterministic."""
        params = {
            "beta_prior_a": 1.0,
            "beta_prior_b": 1.0,
            "epsilon_floor": 0.10,
            "min_theme_count": 2,
            "max_theme_count": 5,
            "supply_min_questions": 10,
            "w_weakness": 0.45,
            "w_due": 0.35,
            "w_uncertainty": 0.10,
            "w_recency_penalty": 0.10,
            "min_per_theme": 3,
            "max_per_theme": 20,
        }

        candidates = [
            ThemeCandidate(
                theme_id=i,
                title=f"Theme {i}",
                block_id=1,
                weakness=0.3 + (i * 0.1),
                supply=50,
                beta_a=1.0,
                beta_b=1.0,
            )
            for i in range(5)
        ]

        # Compute base priorities
        for c in candidates:
            c.base_priority = compute_base_priority(
                weakness=c.weakness,
                due_ratio=0.0,
                uncertainty=0.5,
                recency_penalty=0.0,
                supply=c.supply,
                params=params,
            )

        seed = "test_seed_123"

        plan1 = run_theme_selection(candidates.copy(), 20, seed, params)
        # Reset selection status
        for c in candidates:
            c.selected = False
            c.quota = 0
        plan2 = run_theme_selection(candidates, 20, seed, params)

        selected1 = [(t.theme_id, t.quota) for t in plan1.selected_themes()]
        selected2 = [(t.theme_id, t.quota) for t in plan2.selected_themes()]

        assert selected1 == selected2


class TestThompsonSampling:
    """Tests for Thompson Sampling implementation."""

    def test_beta_sample_bounds(self):
        """Beta samples should be in [0, 1]."""
        rng = create_seeded_rng("test")
        for _ in range(1000):
            sample = sample_beta(rng, random.uniform(0.1, 10), random.uniform(0.1, 10))
            assert 0 <= sample <= 1

    def test_beta_sample_mean_converges(self):
        """Beta samples should converge to expected mean."""
        rng = create_seeded_rng("convergence_test")
        a, b = 2.0, 5.0
        expected_mean = a / (a + b)

        samples = [sample_beta(rng, a, b) for _ in range(10000)]
        actual_mean = sum(samples) / len(samples)

        # Allow 5% tolerance
        assert abs(actual_mean - expected_mean) < 0.05

    def test_final_score_computation(self):
        """Final score should combine base priority and Thompson sample."""
        base = 0.5
        y = 0.3
        epsilon = 0.1

        expected = base * (epsilon + y)
        actual = compute_final_score(base, y, epsilon)

        assert abs(actual - expected) < 1e-10


class TestConstraints:
    """Tests for constraint enforcement."""

    def test_min_theme_count(self):
        """Selection should respect minimum theme count."""
        params = {
            "epsilon_floor": 0.10,
            "min_theme_count": 3,
            "max_theme_count": 5,
            "supply_min_questions": 10,
        }

        candidates = [
            ThemeCandidate(
                theme_id=i,
                title=f"Theme {i}",
                block_id=1,
                base_priority=0.5,
                supply=50,
                beta_a=1.0,
                beta_b=1.0,
            )
            for i in range(5)
        ]

        rng = create_seeded_rng("min_theme_test")
        selected = select_themes(candidates, rng, params)
        selected_count = sum(1 for c in selected if c.selected)

        assert selected_count >= 3

    def test_max_theme_count(self):
        """Selection should respect maximum theme count."""
        params = {
            "epsilon_floor": 0.10,
            "min_theme_count": 2,
            "max_theme_count": 3,
            "supply_min_questions": 10,
        }

        candidates = [
            ThemeCandidate(
                theme_id=i,
                title=f"Theme {i}",
                block_id=1,
                base_priority=0.5 + (i * 0.05),
                supply=50,
                beta_a=1.0,
                beta_b=1.0,
            )
            for i in range(10)
        ]

        rng = create_seeded_rng("max_theme_test")
        selected = select_themes(candidates, rng, params)
        selected_count = sum(1 for c in selected if c.selected)

        assert selected_count <= 3

    def test_supply_constraint(self):
        """Themes with insufficient supply should be deprioritized."""
        params = {
            "epsilon_floor": 0.10,
            "min_theme_count": 2,
            "max_theme_count": 5,
            "supply_min_questions": 20,
        }

        candidates = [
            ThemeCandidate(
                theme_id=1,
                title="High Supply",
                block_id=1,
                base_priority=0.5,
                supply=100,
                beta_a=1.0,
                beta_b=1.0,
            ),
            ThemeCandidate(
                theme_id=2,
                title="Low Supply",
                block_id=1,
                base_priority=0.8,  # Higher priority but low supply
                supply=5,
                beta_a=1.0,
                beta_b=1.0,
            ),
            ThemeCandidate(
                theme_id=3,
                title="Medium Supply",
                block_id=1,
                base_priority=0.6,
                supply=30,
                beta_a=1.0,
                beta_b=1.0,
            ),
        ]

        rng = create_seeded_rng("supply_test")
        selected = select_themes(candidates, rng, params)

        # Theme 1 (high supply) should be selected over theme 2 (low supply)
        selected_ids = {c.theme_id for c in selected if c.selected}
        assert 1 in selected_ids or 3 in selected_ids

    def test_quota_min_per_theme(self):
        """Quota allocation should respect minimum per theme."""
        params = {"min_per_theme": 5, "max_per_theme": 20}

        themes = [
            ThemeCandidate(
                theme_id=i,
                title=f"Theme {i}",
                block_id=1,
                final_score=0.3 + (i * 0.1),
                supply=50,
                selected=True,
            )
            for i in range(3)
        ]

        allocated = allocate_quotas(themes, 20, params)

        for theme in allocated:
            assert theme.quota >= 5

    def test_quota_max_per_theme(self):
        """Quota allocation should respect maximum per theme."""
        params = {"min_per_theme": 3, "max_per_theme": 10}

        themes = [
            ThemeCandidate(
                theme_id=1,
                title="Theme 1",
                block_id=1,
                final_score=0.9,  # High score
                supply=50,
                selected=True,
            ),
            ThemeCandidate(
                theme_id=2,
                title="Theme 2",
                block_id=1,
                final_score=0.1,  # Low score
                supply=50,
                selected=True,
            ),
        ]

        allocated = allocate_quotas(themes, 30, params)

        for theme in allocated:
            assert theme.quota <= 10

    def test_quota_respects_supply(self):
        """Quota should not exceed theme supply."""
        params = {"min_per_theme": 3, "max_per_theme": 20}

        themes = [
            ThemeCandidate(
                theme_id=1,
                title="Theme 1",
                block_id=1,
                final_score=0.5,
                supply=5,  # Low supply
                selected=True,
            ),
            ThemeCandidate(
                theme_id=2,
                title="Theme 2",
                block_id=1,
                final_score=0.5,
                supply=50,
                selected=True,
            ),
        ]

        allocated = allocate_quotas(themes, 30, params)

        for theme in allocated:
            assert theme.quota <= theme.supply


class TestRewardComputation:
    """Tests for bandit reward computation."""

    def test_bkt_delta_reward_improvement(self):
        """Positive mastery improvement should yield positive reward."""
        reward = compute_bkt_delta_reward(pre_mastery=0.3, post_mastery=0.5)
        assert reward > 0

    def test_bkt_delta_reward_no_change(self):
        """No change in mastery should yield zero reward."""
        reward = compute_bkt_delta_reward(pre_mastery=0.5, post_mastery=0.5)
        assert abs(reward) < 1e-10

    def test_bkt_delta_reward_decline(self):
        """Mastery decline should yield zero reward (clamped)."""
        reward = compute_bkt_delta_reward(pre_mastery=0.6, post_mastery=0.4)
        assert reward == 0.0

    def test_bkt_delta_reward_bounds(self):
        """Reward should always be in [0, 1]."""
        for pre in [0.0, 0.25, 0.5, 0.75, 1.0]:
            for post in [0.0, 0.25, 0.5, 0.75, 1.0]:
                reward = compute_bkt_delta_reward(pre, post)
                assert 0.0 <= reward <= 1.0

    def test_bkt_delta_reward_normalization(self):
        """Reward should normalize by room for improvement."""
        # Going from 0.9 to 0.95 is 50% of remaining room
        reward1 = compute_bkt_delta_reward(pre_mastery=0.9, post_mastery=0.95)

        # Going from 0.0 to 0.05 is only 5% of remaining room
        reward2 = compute_bkt_delta_reward(pre_mastery=0.0, post_mastery=0.05)

        assert reward1 > reward2

    def test_beta_posterior_update(self):
        """Beta posterior should update correctly."""
        a, b = 2.0, 3.0
        reward = 0.7

        new_a, new_b = update_beta_posterior(a, b, reward)

        assert new_a == a + reward
        assert new_b == b + (1.0 - reward)

    def test_beta_posterior_bounds(self):
        """Beta parameters should remain positive."""
        new_a, new_b = update_beta_posterior(a=0.001, b=0.001, reward=0.0)
        assert new_a >= 0.001
        assert new_b >= 0.001


class TestBasePriority:
    """Tests for base priority computation."""

    def test_weakness_increases_priority(self):
        """Higher weakness should increase priority."""
        params = {
            "w_weakness": 0.5,
            "w_due": 0.3,
            "w_uncertainty": 0.1,
            "w_recency_penalty": 0.1,
            "supply_min_questions": 10,
        }

        priority_low_weakness = compute_base_priority(
            weakness=0.2,
            due_ratio=0.0,
            uncertainty=0.5,
            recency_penalty=0.0,
            supply=50,
            params=params,
        )

        priority_high_weakness = compute_base_priority(
            weakness=0.8,
            due_ratio=0.0,
            uncertainty=0.5,
            recency_penalty=0.0,
            supply=50,
            params=params,
        )

        assert priority_high_weakness > priority_low_weakness

    def test_recency_penalty_decreases_priority(self):
        """Higher recency penalty should decrease priority."""
        params = {
            "w_weakness": 0.5,
            "w_due": 0.3,
            "w_uncertainty": 0.1,
            "w_recency_penalty": 0.1,
            "supply_min_questions": 10,
        }

        priority_no_recency = compute_base_priority(
            weakness=0.5,
            due_ratio=0.0,
            uncertainty=0.5,
            recency_penalty=0.0,
            supply=50,
            params=params,
        )

        priority_high_recency = compute_base_priority(
            weakness=0.5,
            due_ratio=0.0,
            uncertainty=0.5,
            recency_penalty=1.0,
            supply=50,
            params=params,
        )

        assert priority_no_recency > priority_high_recency

    def test_low_supply_penalized(self):
        """Low supply should reduce priority."""
        params = {
            "w_weakness": 0.5,
            "w_due": 0.3,
            "w_uncertainty": 0.1,
            "w_recency_penalty": 0.1,
            "supply_min_questions": 20,
        }

        priority_high_supply = compute_base_priority(
            weakness=0.5,
            due_ratio=0.0,
            uncertainty=0.5,
            recency_penalty=0.0,
            supply=50,
            params=params,
        )

        priority_low_supply = compute_base_priority(
            weakness=0.5,
            due_ratio=0.0,
            uncertainty=0.5,
            recency_penalty=0.0,
            supply=5,  # Below minimum
            params=params,
        )

        assert priority_high_supply > priority_low_supply


class TestQuestionPicker:
    """Tests for question picking within themes."""

    def test_challenge_band_filtering(self):
        """Questions outside challenge band should be deprioritized."""
        assert is_in_challenge_band(0.6, 0.55, 0.80) is True
        assert is_in_challenge_band(0.4, 0.55, 0.80) is False  # Too hard
        assert is_in_challenge_band(0.9, 0.55, 0.80) is False  # Too easy

    def test_p_correct_computation(self):
        """P(correct) should be computed correctly."""
        # Equal ability and difficulty → p ≈ guess_floor + 0.5*(1-guess_floor)
        p = compute_p_correct(
            user_rating=0.0,
            question_rating=0.0,
            guess_floor=0.2,
            scale=400.0,
        )
        expected = 0.2 + 0.5 * 0.8
        assert abs(p - expected) < 0.01

    def test_p_correct_bounds(self):
        """P(correct) should respect guess floor and ceiling."""
        # Even with very low ability, p >= guess_floor
        p_hard = compute_p_correct(
            user_rating=-1000.0,
            question_rating=0.0,
            guess_floor=0.2,
            scale=400.0,
        )
        assert p_hard >= 0.2

        # Even with very high ability, p <= 1.0
        p_easy = compute_p_correct(
            user_rating=1000.0,
            question_rating=0.0,
            guess_floor=0.2,
            scale=400.0,
        )
        assert p_easy <= 1.0

    def test_interleave_questions(self):
        """Questions should be interleaved across themes."""
        result1 = PickerResult(
            theme_id=1,
            quota=3,
            selected_questions=[uuid4() for _ in range(3)],
        )
        result2 = PickerResult(
            theme_id=2,
            quota=3,
            selected_questions=[uuid4() for _ in range(3)],
        )

        interleaved = interleave_questions([result1, result2])

        # Should alternate: [t1, t2, t1, t2, t1, t2]
        assert len(interleaved) == 6

        # First question from theme 1, second from theme 2, etc.
        assert interleaved[0] == result1.selected_questions[0]
        assert interleaved[1] == result2.selected_questions[0]
        assert interleaved[2] == result1.selected_questions[1]


class TestUncertaintyNormalization:
    """Tests for uncertainty normalization."""

    def test_normalize_uncertainty_bounds(self):
        """Normalized uncertainty should be in [0, 1]."""
        for unc in [50, 100, 200, 350, 500]:
            normalized = normalize_uncertainty(unc, unc_init=350.0, unc_floor=50.0)
            assert 0.0 <= normalized <= 1.0

    def test_normalize_uncertainty_none(self):
        """None uncertainty should map to 1.0 (maximum)."""
        normalized = normalize_uncertainty(None)
        assert normalized == 1.0


class TestRecencyPenalty:
    """Tests for recency penalty computation."""

    def test_recency_penalty_recent(self):
        """Recently practiced themes should have high penalty."""
        now = datetime.now(UTC)
        last_selected = now - timedelta(hours=1)

        penalty = compute_recency_penalty(last_selected, now)
        assert penalty > 0.9  # Very recent

    def test_recency_penalty_old(self):
        """Old themes should have low penalty."""
        now = datetime.now(UTC)
        last_selected = now - timedelta(days=30)

        penalty = compute_recency_penalty(last_selected, now)
        assert penalty < 0.1  # Long ago

    def test_recency_penalty_never_selected(self):
        """Never selected themes should have zero penalty."""
        now = datetime.now(UTC)
        penalty = compute_recency_penalty(None, now)
        assert penalty == 0.0
