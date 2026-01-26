"""Tests for BKT (Bayesian Knowledge Tracing) implementation."""

from uuid import uuid4

from app.learning_engine.bkt.core import (
    apply_learning_transition,
    check_degeneracy,
    clamp_probability,
    posterior_given_obs,
    predict_correct,
    update_mastery,
    validate_bkt_params,
)
from app.learning_engine.bkt.training import TrainingDataset, apply_parameter_constraints


class TestBKTCore:
    """Test core BKT math functions."""

    def test_clamp_probability(self):
        """Test probability clamping."""
        assert clamp_probability(0.5) == 0.5
        assert clamp_probability(-0.1) > 0
        assert clamp_probability(1.5) < 1
        assert clamp_probability(0.0) > 0
        assert clamp_probability(1.0) < 1

    def test_predict_correct(self):
        """Test prediction of correct answer probability."""
        # Known state: p_L=0.8, p_S=0.1, p_G=0.2
        # P(Correct) = 0.8 * (1 - 0.1) + (1 - 0.8) * 0.2 = 0.72 + 0.04 = 0.76
        p_correct = predict_correct(p_L=0.8, p_S=0.1, p_G=0.2)
        assert abs(p_correct - 0.76) < 0.01

        # Edge case: p_L=0 (unlearned)
        # P(Correct) = 0 * (1 - 0.1) + 1 * 0.2 = 0.2
        p_correct = predict_correct(p_L=0.0, p_S=0.1, p_G=0.2)
        assert abs(p_correct - 0.2) < 0.01

        # Edge case: p_L=1 (fully learned)
        # P(Correct) = 1 * (1 - 0.1) + 0 * 0.2 = 0.9
        p_correct = predict_correct(p_L=1.0, p_S=0.1, p_G=0.2)
        assert abs(p_correct - 0.9) < 0.01

    def test_posterior_given_correct(self):
        """Test posterior probability given correct answer."""
        # Start with p_L=0.5, p_S=0.1, p_G=0.2
        # P(Correct) = 0.5 * 0.9 + 0.5 * 0.2 = 0.55
        # P(L|Correct) = (0.5 * 0.9) / 0.55 = 0.45 / 0.55 ≈ 0.818
        posterior = posterior_given_obs(p_L=0.5, correct=True, p_S=0.1, p_G=0.2)
        assert abs(posterior - 0.818) < 0.01

        # Correct answer should increase mastery probability
        assert posterior > 0.5

    def test_posterior_given_wrong(self):
        """Test posterior probability given wrong answer."""
        # Start with p_L=0.5, p_S=0.1, p_G=0.2
        # P(Wrong) = 1 - 0.55 = 0.45
        # P(L|Wrong) = (0.5 * 0.1) / 0.45 = 0.05 / 0.45 ≈ 0.111
        posterior = posterior_given_obs(p_L=0.5, correct=False, p_S=0.1, p_G=0.2)
        assert abs(posterior - 0.111) < 0.01

        # Wrong answer should decrease mastery probability
        assert posterior < 0.5

    def test_apply_learning_transition(self):
        """Test learning transition."""
        # p_L_given_obs=0.8, p_T=0.2
        # P(L_next) = 0.8 + (1 - 0.8) * 0.2 = 0.8 + 0.04 = 0.84
        p_L_next = apply_learning_transition(p_L_given_obs=0.8, p_T=0.2)
        assert abs(p_L_next - 0.84) < 0.01

        # Learning should always increase or maintain mastery
        assert p_L_next >= 0.8

    def test_update_mastery_correct(self):
        """Test full mastery update with correct answer."""
        # Start with low mastery
        p_L = 0.3
        p_T = 0.2
        p_S = 0.1
        p_G = 0.2

        # Correct answer should increase mastery
        p_L_next, _ = update_mastery(p_L, correct=True, p_T=p_T, p_S=p_S, p_G=p_G)
        assert p_L_next > p_L
        assert 0 < p_L_next < 1

    def test_update_mastery_wrong(self):
        """Test full mastery update with wrong answer."""
        # Start with moderate mastery
        p_L = 0.6
        p_T = 0.2
        p_S = 0.1
        p_G = 0.2

        # Wrong answer should decrease mastery (but learning still applies)
        p_L_next, _ = update_mastery(p_L, correct=False, p_T=p_T, p_S=p_S, p_G=p_G)
        # Note: Due to learning transition, p_L_next might still be > p_L
        # But it should be less than if the answer was correct
        p_L_next_if_correct, _ = update_mastery(p_L, correct=True, p_T=p_T, p_S=p_S, p_G=p_G)
        assert p_L_next < p_L_next_if_correct
        assert 0 < p_L_next < 1

    def test_update_mastery_sequence(self):
        """Test mastery progression over a sequence of attempts."""
        p_L = 0.1  # Start with low mastery
        p_T = 0.3
        p_S = 0.1
        p_G = 0.2

        # Sequence of correct answers should increase mastery
        sequence = [True, True, True, True, True]
        for correct in sequence:
            p_L, _ = update_mastery(p_L, correct, p_T, p_S, p_G)

        # After 5 correct answers, mastery should be high
        assert p_L > 0.7

    def test_validate_bkt_params_valid(self):
        """Test validation of valid BKT parameters."""
        is_valid, msg = validate_bkt_params(p_L0=0.1, p_T=0.2, p_S=0.1, p_G=0.2)
        assert is_valid
        assert msg == ""

    def test_validate_bkt_params_out_of_range(self):
        """Test validation catches out-of-range parameters."""
        # p_L0 > 1
        is_valid, msg = validate_bkt_params(p_L0=1.5, p_T=0.2, p_S=0.1, p_G=0.2)
        assert not is_valid
        assert "L0" in msg

        # p_T < 0
        is_valid, msg = validate_bkt_params(p_L0=0.1, p_T=-0.1, p_S=0.1, p_G=0.2)
        assert not is_valid
        assert "T" in msg

    def test_validate_bkt_params_sum_constraint(self):
        """Test validation catches S+G >= 1."""
        # S + G = 0.6 + 0.5 = 1.1 >= 1, which violates the constraint
        # The constraint is: (1 - S) > G, which means 1 - S - G > 0, so S + G < 1
        is_valid, msg = validate_bkt_params(p_L0=0.1, p_T=0.2, p_S=0.6, p_G=0.5)
        assert not is_valid
        # Should mention that learned performance must be better than unlearned
        assert ("learned" in msg.lower() and "unlearned" in msg.lower()) or ("slip" in msg.lower() and "guess" in msg.lower())

    def test_validate_bkt_params_degeneracy(self):
        """Test validation catches degeneracy."""
        # P(Correct|Learned) = 1 - 0.5 = 0.5
        # P(Correct|Unlearned) = 0.5
        # These are equal, which violates the constraint that learned > unlearned
        is_valid, msg = validate_bkt_params(p_L0=0.1, p_T=0.2, p_S=0.5, p_G=0.5)
        assert not is_valid
        # Should mention that learned performance must be better
        assert ("learned" in msg.lower() and "unlearned" in msg.lower()) or "degeneracy" in msg.lower() or "distinguish" in msg.lower()

    def test_check_degeneracy(self):
        """Test degeneracy detection."""
        # Non-degenerate case
        # Note: check_degeneracy returns (is_non_degenerate, warning_message)
        # So True means non-degenerate (good), False means degenerate (bad)
        is_non_degenerate, msg = check_degeneracy(p_L0=0.1, p_T=0.2, p_S=0.1, p_G=0.2)
        assert is_non_degenerate, f"Expected non-degenerate, got message: {msg}"

        # Degenerate case: P(Correct|Learned) <= P(Correct|Unlearned)
        # S=0.5, G=0.5 means (1-S)=0.5, so (1-S) - G = 0, which is < 0.1 threshold
        is_non_degenerate, msg = check_degeneracy(p_L0=0.1, p_T=0.2, p_S=0.5, p_G=0.5)
        assert not is_non_degenerate, f"Expected degenerate, got message: {msg}"
        assert "distinguish" in msg.lower() or "gap" in msg.lower()

        # Very low learning rate
        is_non_degenerate, msg = check_degeneracy(p_L0=0.1, p_T=0.0001, p_S=0.1, p_G=0.2)
        assert not is_non_degenerate, f"Expected degenerate (low learning rate), got message: {msg}"
        assert "transition" in msg.lower() or "learning" in msg.lower()


class TestTrainingDataset:
    """Test training dataset builder."""

    def test_empty_dataset(self):
        """Test empty dataset."""
        dataset = TrainingDataset(concept_id=uuid4())
        assert dataset.total_attempts == 0
        assert dataset.unique_users == 0
        assert not dataset.is_sufficient()

    def test_add_sequence(self):
        """Test adding sequences to dataset."""
        dataset = TrainingDataset(concept_id=uuid4())

        user1 = uuid4()
        user2 = uuid4()

        dataset.add_sequence(user1, [1, 0, 1, 1])
        dataset.add_sequence(user2, [0, 0, 1])

        assert dataset.total_attempts == 7
        assert dataset.unique_users == 2

    def test_is_sufficient(self):
        """Test sufficiency check."""
        dataset = TrainingDataset(concept_id=uuid4())

        # Not sufficient: too few attempts
        dataset.add_sequence(uuid4(), [1, 0, 1])
        assert not dataset.is_sufficient(min_attempts=10, min_users=2)

        # Not sufficient: too few users
        dataset.add_sequence(uuid4(), [1, 0, 1, 1, 1, 1, 1])
        assert dataset.total_attempts >= 10
        assert not dataset.is_sufficient(min_attempts=10, min_users=3)

        # Sufficient
        dataset.add_sequence(uuid4(), [1, 1])
        assert dataset.is_sufficient(min_attempts=10, min_users=3)

    def test_summary(self):
        """Test dataset summary."""
        dataset = TrainingDataset(concept_id=uuid4())

        dataset.add_sequence(uuid4(), [1, 0, 1, 1])
        dataset.add_sequence(uuid4(), [0, 0])
        dataset.add_sequence(uuid4(), [1, 1, 1])

        summary = dataset.summary()
        assert summary["total_attempts"] == 9
        assert summary["unique_users"] == 3
        assert summary["avg_sequence_length"] == 3.0
        assert summary["min_sequence_length"] == 2
        assert summary["max_sequence_length"] == 4


class TestParameterConstraints:
    """Test parameter constraint application."""

    def test_no_violations(self):
        """Test parameters within constraints."""
        params = {"p_L0": 0.1, "p_T": 0.2, "p_S": 0.1, "p_G": 0.2}
        constraints = {
            "L0_min": 0.001,
            "L0_max": 0.5,
            "T_min": 0.001,
            "T_max": 0.5,
            "S_min": 0.001,
            "S_max": 0.4,
            "G_min": 0.001,
            "G_max": 0.4,
        }

        constrained, is_valid, msg = apply_parameter_constraints(params, constraints)
        assert is_valid
        assert constrained == params
        assert "satisfied" in msg.lower()

    def test_clamp_to_min(self):
        """Test clamping to minimum."""
        params = {"p_L0": 0.0001, "p_T": 0.2, "p_S": 0.1, "p_G": 0.2}
        constraints = {
            "L0_min": 0.01,
            "L0_max": 0.5,
            "T_min": 0.001,
            "T_max": 0.5,
            "S_min": 0.001,
            "S_max": 0.4,
            "G_min": 0.001,
            "G_max": 0.4,
        }

        constrained, is_valid, msg = apply_parameter_constraints(params, constraints)
        assert constrained["p_L0"] == 0.01
        assert "L0" in msg

    def test_clamp_to_max(self):
        """Test clamping to maximum."""
        params = {"p_L0": 0.1, "p_T": 0.2, "p_S": 0.5, "p_G": 0.2}
        constraints = {
            "L0_min": 0.001,
            "L0_max": 0.5,
            "T_min": 0.001,
            "T_max": 0.5,
            "S_min": 0.001,
            "S_max": 0.4,
            "G_min": 0.001,
            "G_max": 0.4,
        }

        constrained, is_valid, msg = apply_parameter_constraints(params, constraints)
        assert constrained["p_S"] == 0.4
        assert "S" in msg

    def test_invalid_after_constraints(self):
        """Test detection of invalid parameters even after constraints."""
        # Create params that, when clamped to max, violate (1-S) > G constraint
        # S=0.6, G=0.6 will clamp to S=0.5, G=0.5, which violates (1-S) > G (0.5 > 0.5 is False)
        params = {"p_L0": 0.1, "p_T": 0.2, "p_S": 0.6, "p_G": 0.6}
        constraints = {
            "L0_min": 0.001,
            "L0_max": 0.5,
            "T_min": 0.001,
            "T_max": 0.5,
            "S_min": 0.001,
            "S_max": 0.5,  # Will clamp S from 0.6 to 0.5
            "G_min": 0.001,
            "G_max": 0.5,  # Will clamp G from 0.6 to 0.5
        }

        constrained, is_valid, msg = apply_parameter_constraints(params, constraints)
        assert not is_valid, f"Expected invalid after clamping, but got valid. Message: {msg}"
        assert "validation" in msg.lower() or "degeneracy" in msg.lower() or "learned" in msg.lower()


class TestBKTInvariants:
    """Property-based tests for BKT invariants."""

    def test_mastery_always_in_range(self):
        """Test that mastery probability always stays in [0, 1]."""
        import random

        for _ in range(100):
            # Random valid parameters
            p_L = random.uniform(0.01, 0.99)
            p_T = random.uniform(0.01, 0.4)
            p_S = random.uniform(0.01, 0.3)
            p_G = random.uniform(0.01, 0.3)

            # Ensure S+G < 1 and 1-S > G
            if p_S + p_G >= 1 or (1 - p_S) <= p_G:
                continue

            # Random correctness
            correct = random.choice([True, False])

            # Update mastery
            p_L_next, _ = update_mastery(p_L, correct, p_T, p_S, p_G)

            # Invariant: mastery in [0, 1]
            assert 0 <= p_L_next <= 1, f"Mastery out of range: {p_L_next}"

    def test_correct_increases_mastery_more_than_wrong(self):
        """Test that correct answers increase mastery more than wrong answers."""
        import random

        for _ in range(50):
            # Random valid parameters
            p_L = random.uniform(0.1, 0.9)
            p_T = random.uniform(0.1, 0.4)
            p_S = random.uniform(0.05, 0.2)
            p_G = random.uniform(0.05, 0.2)

            # Ensure valid
            if p_S + p_G >= 1 or (1 - p_S) <= p_G:
                continue

            # Update with correct and wrong
            p_L_correct, _ = update_mastery(p_L, True, p_T, p_S, p_G)
            p_L_wrong, _ = update_mastery(p_L, False, p_T, p_S, p_G)

            # Invariant: correct answer increases mastery more
            assert (
                p_L_correct >= p_L_wrong
            ), f"Correct ({p_L_correct}) should be >= wrong ({p_L_wrong})"

    def test_mastery_converges_with_consistent_performance(self):
        """Test that mastery converges with consistent correct/wrong answers."""
        p_L = 0.5
        p_T = 0.2
        p_S = 0.1
        p_G = 0.2

        # All correct answers should converge to high mastery
        for _ in range(20):
            p_L, _ = update_mastery(p_L, True, p_T, p_S, p_G)

        assert p_L > 0.9, f"Mastery should converge high with all correct: {p_L}"

        # All wrong answers should converge to low mastery
        p_L = 0.5
        for _ in range(20):
            p_L, _ = update_mastery(p_L, False, p_T, p_S, p_G)

        assert p_L < 0.3, f"Mastery should converge low with all wrong: {p_L}"


# Integration tests would go here, testing:
# - Database persistence of BKTSkillParams
# - Database persistence of BKTUserSkillState
# - Training dataset builder from real session data
# - Full recompute flow
# - API endpoints with RBAC
# These require database fixtures and are omitted for brevity
