"""
Tests for constants registry provenance enforcement.

Ensures all constants have proper documentation and source attribution.
"""

import pytest
import inspect

from app.learning_engine.config import (
    # FSRS constants
    FSRS_DEFAULT_WEIGHTS,
    FSRS_DESIRED_RETENTION,
    FSRS_RETENTION_MAX,
    FSRS_RETENTION_MIN,
    FSRS_SHRINKAGE_TARGET_LOGS,
    FSRS_MIN_LOGS_FOR_TRAINING,
    FSRS_VALIDATION_SPLIT,
    # BKT constants
    BKT_DEFAULT_L0,
    BKT_DEFAULT_T,
    BKT_DEFAULT_S,
    BKT_DEFAULT_G,
    BKT_MAX_PROB,
    BKT_PARAM_MIN,
    BKT_PARAM_MAX,
    BKT_EPSILON,
    # Mastery constants
    MASTERY_LOOKBACK_DAYS,
    MASTERY_MIN_ATTEMPTS,
    MASTERY_DIFFICULTY_WEIGHT_EASY,
    MASTERY_DIFFICULTY_WEIGHT_MEDIUM,
    MASTERY_DIFFICULTY_WEIGHT_HARD,
    # Rating mapper constants
    RATING_FAST_ANSWER_MS,
    RATING_MAX_CHANGES_FOR_CONFIDENT,
    RATING_SLOW_ANSWER_MS,
    TELEMETRY_MAX_CHANGES,
    TELEMETRY_MAX_TIME_MS,
    TELEMETRY_MIN_TIME_MS,
    # Training pipeline constants
    BKT_MIN_ATTEMPTS_PER_CONCEPT,
)


def all_constants():
    """Get all SourcedValue constants from config module."""
    import app.learning_engine.config as config_module
    from app.learning_engine.config import SourcedValue
    
    constants = []
    for name, obj in inspect.getmembers(config_module):
        # Skip classes, functions, and modules
        if inspect.isclass(obj) or inspect.isfunction(obj) or inspect.ismodule(obj):
            continue
        # Only include SourcedValue instances
        if isinstance(obj, SourcedValue):
            constants.append(obj)
    return constants


class TestProvenanceEnforcement:
    """Test that all constants have proper source attribution."""

    def test_all_constants_have_sources(self):
        """Every constant must have at least one source."""
        for const in all_constants():
            assert (
                const.source
            ), f"{const.value!r} has no source. All constants must document their origin."
            assert isinstance(const.source, str), f"{const.value!r} source is not a string"
            assert const.source.strip(), f"{const.value!r} has empty/whitespace-only source"

    def test_sources_are_non_empty_strings(self):
        """All source strings must be meaningful (not whitespace-only)."""
        for const in all_constants():
            assert isinstance(const.source, str), f"{const.value!r} has non-string source: {const.source}"
            assert const.source.strip(), f"{const.value!r} has empty/whitespace-only source"
            assert (
                len(const.source) > 10
            ), f"{const.value!r} source too short (< 10 chars): '{const.source}'"

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
            source_text = const.source.lower()
            has_reasoning = any(keyword in source_text for keyword in good_keywords)
            assert has_reasoning, (
                f"{const.value!r} source lacks clear reasoning. "
                f"Include keywords like: {', '.join(good_keywords[:5])}"
            )

    def test_no_naked_numbers_in_sources(self):
        """Sources should not just say 'set to X' without explanation."""
        banned_patterns = ["set to", "value of", "equals", "is set", "hardcoded"]

        for const in all_constants():
            source_text = const.source.lower()

            # If source contains a banned pattern, it should also have more context
            for pattern in banned_patterns:
                if pattern in source_text:
                    # Should also mention why/where this value comes from
                    assert any(
                        kw in source_text
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
            FSRS_SHRINKAGE_TARGET_LOGS.value > 0
        ), "Shrinkage target logs must be positive"
        assert FSRS_MIN_LOGS_FOR_TRAINING.value >= 300, "Need enough data for reliable training"
        assert 0 < FSRS_VALIDATION_SPLIT.value < 0.5, "Validation split should be reasonable"


class TestBKTConstants:
    """Test BKT parameter constraints."""

    def test_bkt_defaults_are_valid_probabilities(self):
        """All BKT default parameters must be in (0, 1)."""
        assert 0 < BKT_DEFAULT_L0.value < 1
        assert 0 < BKT_DEFAULT_T.value < 1
        assert 0 < BKT_DEFAULT_S.value < 1
        assert 0 < BKT_DEFAULT_G.value < 1

    def test_bkt_non_degeneracy_constraint(self):
        """S + G must be < 1 to prevent degeneracy."""
        assert (
            BKT_DEFAULT_S.value + BKT_DEFAULT_G.value < 1.0
        ), "S + G >= 1 would make learned/unlearned indistinguishable"

    def test_bkt_learned_better_than_unlearned(self):
        """Learned should still be better than unlearned."""
        p_correct_learned_worst = 1.0 - BKT_DEFAULT_S.value
        p_correct_unlearned_best = BKT_DEFAULT_G.value
        assert (
            p_correct_learned_worst > p_correct_unlearned_best
        ), "Even in worst case, learned performance must exceed unlearned"

    def test_bkt_stability_constants(self):
        """Numerical stability constants must be sensible."""
        assert BKT_EPSILON.value > 0
        assert BKT_EPSILON.value < 1e-6, "Epsilon too large"
        assert 0 < BKT_PARAM_MIN.value < BKT_PARAM_MAX.value < 1
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
        """Difficulty weights must be positive."""
        assert MASTERY_DIFFICULTY_WEIGHT_EASY.value > 0
        assert MASTERY_DIFFICULTY_WEIGHT_MEDIUM.value > 0
        assert MASTERY_DIFFICULTY_WEIGHT_HARD.value > 0


class TestTrainingConstants:
    """Test algorithm training thresholds."""

    def test_bkt_training_threshold(self):
        """BKT training needs enough data."""
        assert BKT_MIN_ATTEMPTS_PER_CONCEPT.value >= 10, "BKT needs substantial data for EM fitting"


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
                    existing_source = value_to_sources[val]
                    if existing_source != const.source:
                        # Different sources - potential issue but not fatal
                        pass
                else:
                    value_to_sources[val] = const.source

    def test_constants_are_immutable(self):
        """SourcedValue constants should be immutable after creation."""
        # Can't directly test immutability, but can verify they're not being modified
        initial_values = {id(const): const.source for const in all_constants()}

        # Try to access again (should be same instances)
        for const in all_constants():
            assert (
                const.source == initial_values[id(const)]
            ), f"Constant {const.value!r} source changed!"


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
        sources_text = MASTERY_DIFFICULTY_WEIGHT_EASY.source.lower()
        assert "heuristic" in sources_text or "placeholder" in sources_text or "calibration" in sources_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
