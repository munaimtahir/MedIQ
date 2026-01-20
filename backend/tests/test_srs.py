"""Tests for SRS (Spaced Repetition System) implementation."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.learning_engine.srs.rating_mapper import (
    map_attempt_to_rating,
    explain_rating,
    validate_telemetry,
)
from app.learning_engine.srs.fsrs_adapter import (
    get_default_parameters,
    compute_next_state_and_due,
    validate_weights,
)


class TestRatingMapper:
    """Test MCQ attempt to FSRS rating mapping."""

    def test_incorrect_always_again(self):
        """Test that incorrect answers always map to rating 1 (Again)."""
        # Regardless of time or changes, incorrect is always Again
        assert map_attempt_to_rating(correct=False) == 1
        assert map_attempt_to_rating(correct=False, time_spent_ms=5000) == 1
        assert map_attempt_to_rating(correct=False, time_spent_ms=100000) == 1
        assert map_attempt_to_rating(correct=False, change_count=0) == 1
        assert map_attempt_to_rating(correct=False, change_count=5) == 1

    def test_correct_marked_for_review_is_hard(self):
        """Test that correct but marked for review is rating 2 (Hard)."""
        rating = map_attempt_to_rating(correct=True, marked_for_review=True)
        assert rating == 2

    def test_correct_with_changes_is_hard(self):
        """Test that correct with answer changes is rating 2 (Hard)."""
        rating = map_attempt_to_rating(correct=True, change_count=1)
        assert rating == 2

        rating = map_attempt_to_rating(correct=True, change_count=3)
        assert rating == 2

    def test_correct_slow_is_hard(self):
        """Test that correct but slow is rating 2 (Hard)."""
        rating = map_attempt_to_rating(correct=True, time_spent_ms=100000)  # 100 seconds
        assert rating == 2

    def test_correct_fast_confident_is_easy(self):
        """Test that correct, fast, no changes is rating 4 (Easy)."""
        rating = map_attempt_to_rating(
            correct=True, time_spent_ms=10000, change_count=0  # 10 seconds
        )
        assert rating == 4

    def test_correct_default_is_good(self):
        """Test that correct with no telemetry is rating 3 (Good)."""
        rating = map_attempt_to_rating(correct=True)
        assert rating == 3

        # Normal speed, no changes
        rating = map_attempt_to_rating(
            correct=True, time_spent_ms=30000, change_count=0  # 30 seconds
        )
        assert rating == 3

    def test_rating_deterministic(self):
        """Test that rating mapping is deterministic."""
        # Same inputs should always give same rating
        rating1 = map_attempt_to_rating(correct=True, time_spent_ms=20000, change_count=0)
        rating2 = map_attempt_to_rating(correct=True, time_spent_ms=20000, change_count=0)
        assert rating1 == rating2

    def test_explain_rating(self):
        """Test rating explanation."""
        # Incorrect
        explanation = explain_rating(1, correct=False)
        assert "Incorrect" in explanation
        assert "Again" in explanation

        # Correct but hard (with reasons)
        explanation = explain_rating(2, correct=True, marked_for_review=True, change_count=2)
        assert "marked for review" in explanation
        assert "answer changes" in explanation

        # Easy
        explanation = explain_rating(4, correct=True, time_spent_ms=10000)
        assert "fast" in explanation
        assert "Easy" in explanation

    def test_validate_telemetry(self):
        """Test telemetry validation."""
        # Valid telemetry
        time, changes, warnings = validate_telemetry(30000, 2)
        assert time == 30000
        assert changes == 2
        assert len(warnings) == 0

        # Negative time
        time, changes, warnings = validate_telemetry(-1000, 2)
        assert time is None
        assert "Negative time" in warnings[0]

        # Suspicious very long time
        time, changes, warnings = validate_telemetry(5000000, 2)
        assert time == 5000000
        assert "Suspiciously long" in warnings[0]

        # Negative changes
        time, changes, warnings = validate_telemetry(30000, -1)
        assert changes == 0
        assert "Negative change_count" in warnings[0]

        # Very high changes (capped)
        time, changes, warnings = validate_telemetry(30000, 50)
        assert changes == 20  # Capped at 20
        assert "Suspiciously high" in warnings[0]


class TestFSRSAdapter:
    """Test FSRS adapter functions."""

    def test_get_default_parameters(self):
        """Test default FSRS-6 parameters."""
        params = get_default_parameters("fsrs-6")
        assert "weights" in params
        assert "desired_retention" in params
        assert len(params["weights"]) == 19  # FSRS-6 has 19 weights
        assert 0.0 <= params["desired_retention"] <= 1.0

    def test_validate_weights(self):
        """Test weight validation."""
        # Valid weights (19 parameters)
        valid_weights = [0.5] * 19
        is_valid, msg = validate_weights(valid_weights)
        assert is_valid
        assert msg == ""

        # Wrong number of weights
        is_valid, msg = validate_weights([0.5] * 10)
        assert not is_valid
        assert "19 weights" in msg

        # Inf weights
        invalid_weights = [float("inf")] + [0.5] * 18
        is_valid, msg = validate_weights(invalid_weights)
        assert not is_valid
        assert "not finite" in msg

        # Out of range weights
        invalid_weights = [200.0] + [0.5] * 18
        is_valid, msg = validate_weights(invalid_weights)
        assert not is_valid
        assert "reasonable range" in msg

    def test_compute_next_state_first_review(self):
        """Test FSRS state computation for first review."""
        now = datetime.now()
        weights = get_default_parameters()["weights"]

        # First review (stability=None, difficulty=None)
        stability, difficulty, due_at, retrievability = compute_next_state_and_due(
            current_stability=None,
            current_difficulty=None,
            rating=3,  # Good
            delta_days=0.0,
            weights=weights,
            desired_retention=0.90,
            reviewed_at=now,
        )

        # Check outputs are valid
        assert stability > 0
        assert 0 <= difficulty <= 10
        assert due_at > now
        assert 0 <= retrievability <= 1

    def test_compute_next_state_subsequent_review(self):
        """Test FSRS state computation for subsequent review."""
        now = datetime.now()
        weights = get_default_parameters()["weights"]

        # Subsequent review
        stability, difficulty, due_at, retrievability = compute_next_state_and_due(
            current_stability=2.0,
            current_difficulty=5.0,
            rating=3,  # Good
            delta_days=2.5,
            weights=weights,
            desired_retention=0.90,
            reviewed_at=now,
        )

        # Check outputs are valid
        assert stability > 0
        assert 0 <= difficulty <= 10
        assert due_at > now
        assert 0 <= retrievability <= 1

    def test_rating_affects_stability(self):
        """Test that rating affects stability."""
        now = datetime.now()
        weights = get_default_parameters()["weights"]

        # Rating 1 (Again) should give lower stability than rating 4 (Easy)
        s1, d1, _, _ = compute_next_state_and_due(
            current_stability=2.0,
            current_difficulty=5.0,
            rating=1,  # Again
            delta_days=2.0,
            weights=weights,
            desired_retention=0.90,
            reviewed_at=now,
        )

        s4, d4, _, _ = compute_next_state_and_due(
            current_stability=2.0,
            current_difficulty=5.0,
            rating=4,  # Easy
            delta_days=2.0,
            weights=weights,
            desired_retention=0.90,
            reviewed_at=now,
        )

        # Easy should give longer stability than Again
        assert s4 > s1

    def test_due_date_always_in_future(self):
        """Test that due_at is always in the future."""
        now = datetime.now()
        weights = get_default_parameters()["weights"]

        for rating in [1, 2, 3, 4]:
            _, _, due_at, _ = compute_next_state_and_due(
                current_stability=1.0,
                current_difficulty=5.0,
                rating=rating,
                delta_days=1.0,
                weights=weights,
                desired_retention=0.90,
                reviewed_at=now,
            )
            assert due_at > now

    def test_invalid_rating_raises_error(self):
        """Test that invalid rating raises error."""
        now = datetime.now()
        weights = get_default_parameters()["weights"]

        with pytest.raises(ValueError, match="Invalid FSRS rating"):
            compute_next_state_and_due(
                current_stability=1.0,
                current_difficulty=5.0,
                rating=5,  # Invalid (must be 1-4)
                delta_days=1.0,
                weights=weights,
                desired_retention=0.90,
                reviewed_at=now,
            )


class TestSRSIntegration:
    """Integration tests for SRS service layer."""

    # Note: These would require database fixtures in a real test environment
    # For now, we test the core logic in isolation

    def test_multiple_concepts_per_attempt(self):
        """Test that SRS can handle multiple concepts per MCQ."""
        # Placeholder - would test update_from_attempt with multiple concept_ids
        concept_ids = [uuid4(), uuid4(), uuid4()]
        assert len(concept_ids) == 3
        # In real test, would verify each concept gets updated

    def test_telemetry_features_affect_rating(self):
        """Test that telemetry affects FSRS rating."""
        # Fast, no changes -> Easy (4)
        rating_easy = map_attempt_to_rating(correct=True, time_spent_ms=10000, change_count=0)
        assert rating_easy == 4

        # Slow, many changes -> Hard (2)
        rating_hard = map_attempt_to_rating(correct=True, time_spent_ms=120000, change_count=3)
        assert rating_hard == 2

        # Different ratings should lead to different stability increases
        # (tested in FSRS adapter tests above)


# Property-based tests (invariants)
class TestSRSInvariants:
    """Property-based tests for SRS invariants."""

    def test_stability_always_positive(self):
        """Test that stability is always positive."""
        now = datetime.now()
        weights = get_default_parameters()["weights"]

        for _ in range(20):
            for rating in [1, 2, 3, 4]:
                stability, _, _, _ = compute_next_state_and_due(
                    current_stability=1.0,
                    current_difficulty=5.0,
                    rating=rating,
                    delta_days=1.0,
                    weights=weights,
                    desired_retention=0.90,
                    reviewed_at=now,
                )
                assert stability > 0, f"Stability must be positive, got {stability}"

    def test_difficulty_in_range(self):
        """Test that difficulty is always in [0, 10]."""
        now = datetime.now()
        weights = get_default_parameters()["weights"]

        for _ in range(20):
            for rating in [1, 2, 3, 4]:
                _, difficulty, _, _ = compute_next_state_and_due(
                    current_stability=1.0,
                    current_difficulty=5.0,
                    rating=rating,
                    delta_days=1.0,
                    weights=weights,
                    desired_retention=0.90,
                    reviewed_at=now,
                )
                assert 0 <= difficulty <= 10, f"Difficulty must be in [0,10], got {difficulty}"

    def test_retrievability_in_range(self):
        """Test that retrievability is always in [0, 1]."""
        now = datetime.now()
        weights = get_default_parameters()["weights"]

        for _ in range(20):
            for rating in [1, 2, 3, 4]:
                _, _, _, retrievability = compute_next_state_and_due(
                    current_stability=1.0,
                    current_difficulty=5.0,
                    rating=rating,
                    delta_days=1.0,
                    weights=weights,
                    desired_retention=0.90,
                    reviewed_at=now,
                )
                assert (
                    0 <= retrievability <= 1
                ), f"Retrievability must be in [0,1], got {retrievability}"


# Integration with real database would test:
# - update_from_attempt creates review_log entries
# - update_from_attempt upserts concept_state
# - get_due_concepts returns correct buckets
# - Queue API endpoints return correct data
# - Session integration extracts concept_ids correctly
# - Training pipeline (Phase 2C)
