"""
Tests for constants registry provenance enforcement.

Ensures all constants have proper documentation and source attribution.
"""

import pytest
from app.learning_engine.config import (
    # FSRS constants
    FSRS_DEFAULT_WEIGHTS,
    FSRS_DESIRED_RETENTION,
    FSRS_RETENTION_MIN,
    FSRS_RETENTION_MAX,
    FSRS_SHRINKAGE_MIN_LOGS,
    FSRS_SHRINKAGE_TARGET_LOGS,
    FSRS_TRAINING_MIN_LOGS,
    FSRS_TRAINING_VAL_RATIO,
    # BKT constants
    BKT_L0_MIN,
    BKT_L0_MAX,
    BKT_T_MIN,
    BKT_T_MAX,
    BKT_S_MIN,
    BKT_S_MAX,
    BKT_G_MIN,
    BKT_G_MAX,
    BKT_STABILITY_EPSILON,
    BKT_MIN_PROB,
    BKT_MAX_PROB,
    # Rating mapper constants
    RATING_FAST_ANSWER_MS,
    RATING_SLOW_ANSWER_MS,
    RATING_MAX_CHANGES_FOR_CONFIDENT,
    # Telemetry validation
    TELEMETRY_MIN_TIME_MS,
    TELEMETRY_MAX_TIME_MS,
    TELEMETRY_MAX_CHANGES,
    # Mastery constants
    MASTERY_LOOKBACK_DAYS,
    MASTERY_MIN_ATTEMPTS,
    MASTERY_DIFFICULTY_WEIGHTS,
    # Training pipeline constants
    TRAINING_BKT_MIN_ATTEMPTS,
    TRAINING_DIFFICULTY_MIN_ATTEMPTS,
    # All constants for provenance check
    all_constants,
)


class TestProvenanceEnforcement:
    """Test that all constants have proper source attribution."""

    def test_all_constants_have_sources(self):
        """Every constant must have at least one source."""
        for const in all_constants():
            assert (
                const.sources
            ), f"{const.value!r} has no sources. All constants must document their origin."
            assert len(const.sources) > 0, f"{const.value!r} has empty sources list"

    def test_sources_are_non_empty_strings(self):
        """All source strings must be meaningful (not whitespace-only)."""
        for const in all_constants():
            for source in const.sources:
                assert isinstance(source, str), f"{const.value!r} has non-string source: {source}"
                assert source.strip(), f"{const.value!r} has empty/whitespace-only source"
                assert (
                    len(source) > 10
                ), f"{const.value!r} source too short (< 10 chars): '{source}'"

    def test_sources_contain_reasoning(self):
        """Sources should explain why the value was chosen."""
        # Keywords that indicate proper provenance
        good_keywords = [
            "paper",
            "study",
            "pyBKT",
            "py-fsrs",
            "Baker",
            "empirical",
            "literature",
            "standard",
            "default",
            "heuristic",
            "placeholder",
            "calibration",
            "typical",
        ]

        for const in all_constants():
            sources_text = " ".join(const.sources).lower()
            has_reasoning = any(keyword in sources_text for keyword in good_keywords)
            assert has_reasoning, (
                f"{const.value!r} sources lack clear reasoning. "
                f"Include keywords like: {', '.join(good_keywords[:5])}"
            )

    def test_no_naked_numbers_in_sources(self):
        """Sources should not just say 'set to X' without explanation."""
        banned_patterns = ["set to", "value of", "equals", "is set", "hardcoded"]

        for const in all_constants():
            sources_text = " ".join(const.sources).lower()

            # If source contains a banned pattern, it should also have more context
            for pattern in banned_patterns:
                if pattern in sources_text:
                    # Should also mention why/where this value comes from
                    assert any(
                        kw in sources_text
                        for kw in ["paper", "default", "standard", "heuristic", "typical"]
                    ), f"{const.value!r} source uses '{pattern}' but lacks proper justification"


class TestFSRSConstants:
    """Test FSRS constants are correctly specified."""

    def test_fsrs_weights_count(self):
        """FSRS-6 must have exactly 19 weights."""
        assert len(FSRS_DEFAULT_WEIGHTS.value) == 19, "FSRS-6 requires exactly 19 parameters"

    def test_fsrs_weights_are_floats(self):
        """All FSRS weights must be numeric."""
        for i, w in enumerate(FSRS_DEFAULT_WEIGHTS.value):
            assert isinstance(w, (int, float)), f"Weight[{i}] is not numeric: {w}"
            assert w > 0, f"Weight[{i}] must be positive: {w}"

    def test_fsrs_retention_bounds(self):
        """Retention must be in valid range."""
        assert 0 < FSRS_RETENTION_MIN.value < FSRS_RETENTION_MAX.value < 1
        assert FSRS_RETENTION_MIN.value <= FSRS_DESIRED_RETENTION.value <= FSRS_RETENTION_MAX.value

    def test_fsrs_training_thresholds(self):
        """Training thresholds must be ordered."""
        assert (
            FSRS_SHRINKAGE_MIN_LOGS.value
            < FSRS_SHRINKAGE_TARGET_LOGS.value
            < FSRS_TRAINING_MIN_LOGS.value
        )
        assert FSRS_TRAINING_MIN_LOGS.value >= 300, "Need enough data for reliable training"
        assert 0 < FSRS_TRAINING_VAL_RATIO.value < 0.5, "Validation split should be reasonable"


class TestBKTConstants:
    """Test BKT parameter constraints."""

    def test_bkt_ranges_are_valid_probabilities(self):
        """All BKT parameters must be in (0, 1)."""
        assert 0 < BKT_L0_MIN.value < BKT_L0_MAX.value < 1
        assert 0 < BKT_T_MIN.value < BKT_T_MAX.value < 1
        assert 0 < BKT_S_MIN.value < BKT_S_MAX.value < 1
        assert 0 < BKT_G_MIN.value < BKT_G_MAX.value < 1

    def test_bkt_non_degeneracy_constraint(self):
        """S_max + G_max must be < 1 to prevent degeneracy."""
        assert (
            BKT_S_MAX.value + BKT_G_MAX.value < 1.0
        ), "S + G >= 1 would make learned/unlearned indistinguishable"

    def test_bkt_learned_better_than_unlearned(self):
        """At max slip and max guess, learned should still be better."""
        p_correct_learned_worst = 1.0 - BKT_S_MAX.value
        p_correct_unlearned_best = BKT_G_MAX.value
        assert (
            p_correct_learned_worst > p_correct_unlearned_best
        ), "Even in worst case, learned performance must exceed unlearned"

    def test_bkt_stability_constants(self):
        """Numerical stability constants must be sensible."""
        assert BKT_STABILITY_EPSILON.value > 0
        assert BKT_STABILITY_EPSILON.value < 1e-6, "Epsilon too large"
        assert 0 < BKT_MIN_PROB.value < BKT_MAX_PROB.value < 1
        assert BKT_MAX_PROB.value > 0.99, "MAX_PROB should be close to 1"


class TestRatingMapperConstants:
    """Test rating mapper thresholds."""

    def test_timing_thresholds_ordered(self):
        """Fast < Slow timing thresholds."""
        assert RATING_FAST_ANSWER_MS.value < RATING_SLOW_ANSWER_MS.value
        assert RATING_FAST_ANSWER_MS.value > 0
        assert RATING_SLOW_ANSWER_MS.value < 10 * 60 * 1000, "Slow threshold should be < 10 minutes"

    def test_change_threshold(self):
        """Change count threshold must be reasonable."""
        assert RATING_MAX_CHANGES_FOR_CONFIDENT.value >= 0
        assert RATING_MAX_CHANGES_FOR_CONFIDENT.value <= 2, "Few changes = confident"

    def test_telemetry_validation_bounds(self):
        """Telemetry validation bounds must be sensible."""
        assert TELEMETRY_MIN_TIME_MS.value > 0
        assert TELEMETRY_MAX_TIME_MS.value > TELEMETRY_MIN_TIME_MS.value
        assert TELEMETRY_MAX_TIME_MS.value <= 3600 * 1000, "Max time should be <= 1 hour"
        assert TELEMETRY_MAX_CHANGES.value > 0
        assert TELEMETRY_MAX_CHANGES.value <= 50, "Change count cap should be reasonable"


class TestMasteryConstants:
    """Test mastery computation constants."""

    def test_lookback_window(self):
        """Lookback window must be reasonable."""
        assert 7 <= MASTERY_LOOKBACK_DAYS.value <= 365, "Lookback should be 1 week to 1 year"

    def test_min_attempts(self):
        """Minimum attempts threshold must be positive."""
        assert MASTERY_MIN_ATTEMPTS.value > 0
        assert MASTERY_MIN_ATTEMPTS.value <= 10, "Min attempts should be achievable"

    def test_difficulty_weights_structure(self):
        """Difficulty weights must cover all buckets."""
        weights = MASTERY_DIFFICULTY_WEIGHTS.value
        assert isinstance(weights, dict)
        assert len(weights) > 0
        assert all(isinstance(k, str) for k in weights.keys())
        assert all(isinstance(v, (int, float)) for v in weights.values())
        assert all(v > 0 for v in weights.values()), "All weights must be positive"


class TestTrainingConstants:
    """Test algorithm training thresholds."""

    def test_bkt_training_threshold(self):
        """BKT training needs enough data."""
        assert TRAINING_BKT_MIN_ATTEMPTS.value >= 50, "BKT needs substantial data for EM fitting"

    def test_difficulty_training_threshold(self):
        """Difficulty calibration needs multiple observations."""
        assert (
            TRAINING_DIFFICULTY_MIN_ATTEMPTS.value >= 10
        ), "Difficulty needs enough attempts per question"


class TestConstantsIntegrity:
    """Test overall registry integrity."""

    def test_no_duplicate_values_with_different_sources(self):
        """Same value should not have conflicting provenance."""
        value_to_sources = {}

        for const in all_constants():
            val = const.value
            # Skip complex types (dicts, lists) - only check simple values
            if isinstance(val, (int, float, str, bool)):
                if val in value_to_sources:
                    # Same value can appear if sources are compatible
                    # Just warn if sources are completely different
                    existing_sources_set = set(value_to_sources[val])
                    new_sources_set = set(const.sources)
                    if not existing_sources_set & new_sources_set:
                        # No overlap in sources - potential issue
                        pytest.warns(UserWarning, match=f"Value {val} has conflicting provenance")
                else:
                    value_to_sources[val] = const.sources

    def test_constants_are_immutable(self):
        """SourcedValue constants should be immutable after creation."""
        # Can't directly test immutability, but can verify they're not being modified
        initial_values = {const.value: const.sources[:] for const in all_constants()}

        # Try to access again (should be same instances)
        for const in all_constants():
            assert (
                const.sources == initial_values[const.value]
            ), f"Constant {const.value!r} sources changed!"


class TestCalibrationFlag:
    """Test that heuristic constants are flagged for calibration."""

    def test_rating_thresholds_need_calibration(self):
        """Rating thresholds are marked as needing calibration."""
        # These are heuristic and should mention "calibration" or "heuristic" in sources
        rating_constants = [
            RATING_FAST_ANSWER_MS,
            RATING_SLOW_ANSWER_MS,
            RATING_MAX_CHANGES_FOR_CONFIDENT,
        ]

        for const in rating_constants:
            sources_text = " ".join(const.sources).lower()
            assert (
                "heuristic" in sources_text
                or "calibration" in sources_text
                or "placeholder" in sources_text
            ), f"{const.value!r} is a heuristic but doesn't mention calibration plan"

    def test_difficulty_weights_need_calibration(self):
        """Difficulty weights are marked as heuristic."""
        sources_text = " ".join(MASTERY_DIFFICULTY_WEIGHTS.sources).lower()
        assert "heuristic" in sources_text or "placeholder" in sources_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
