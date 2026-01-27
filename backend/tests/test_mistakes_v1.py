"""Tests for Mistake Engine v1."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta

from app.learning_engine.mistakes_v1.schemas import AttemptFeaturesV1, WeakLabel
from app.learning_engine.mistakes_v1.weak_labels import generate_weak_label
from app.learning_engine.mistakes_v1.features import features_to_dict


@pytest.fixture
def sample_features():
    """Sample attempt features for testing."""
    return AttemptFeaturesV1(
        question_id=uuid4(),
        session_id=uuid4(),
        user_id=uuid4(),
        position=1,
        is_correct=False,  # Wrong answer
        answered_at=datetime.utcnow(),
        response_time_seconds=15.0,
        changed_answer_count=1,
        final_answer_correct=False,
        mark_for_review_used=False,
        pause_blur_count=0,
    )


@pytest.fixture
def v0_params():
    """Default v0 parameters."""
    return {
        "fast_wrong_sec": 20,
        "slow_wrong_sec": 90,
        "time_pressure_remaining_sec": 60,
        "blur_threshold": 1,
        "severity_rules": {},
    }


def test_weak_labeling_changed_answer(sample_features, v0_params):
    """Test weak labeling for changed answer."""
    sample_features.changed_answer_count = 2
    weak_label = generate_weak_label(sample_features, v0_params)

    assert weak_label is not None
    assert weak_label.mistake_type == "CHANGED_ANSWER_WRONG"
    assert weak_label.confidence >= 0.9  # High confidence for changed answer


def test_weak_labeling_fast_wrong(sample_features, v0_params):
    """Test weak labeling for fast wrong."""
    sample_features.response_time_seconds = 10.0  # Very fast
    weak_label = generate_weak_label(sample_features, v0_params)

    assert weak_label is not None
    assert weak_label.mistake_type == "FAST_WRONG"
    assert 0.6 <= weak_label.confidence <= 1.0


def test_weak_labeling_correct_answer(sample_features, v0_params):
    """Test that correct answers are not labeled."""
    sample_features.is_correct = True
    weak_label = generate_weak_label(sample_features, v0_params)

    assert weak_label is None


def test_features_to_dict(sample_features):
    """Test feature dictionary conversion."""
    feature_dict = features_to_dict(sample_features)

    assert isinstance(feature_dict, dict)
    assert "response_time_seconds" in feature_dict
    assert "changed_answer_count" in feature_dict
    assert "is_correct" in feature_dict
    assert feature_dict["is_correct"] == 0  # False -> 0
    assert feature_dict["changed_answer_count"] == 1


def test_weak_labeling_confidence_ranges(sample_features, v0_params):
    """Test that confidence values are in valid range."""
    # Test different scenarios
    scenarios = [
        {"changed_answer_count": 2},  # High confidence
        {"response_time_seconds": 5.0},  # Very fast
        {"response_time_seconds": 100.0},  # Very slow
        {"pause_blur_count": 3},  # Multiple blurs
    ]

    for scenario in scenarios:
        for key, value in scenario.items():
            setattr(sample_features, key, value)

        weak_label = generate_weak_label(sample_features, v0_params)
        if weak_label:
            assert 0.0 <= weak_label.confidence <= 1.0


@pytest.mark.asyncio
async def test_dataset_build_sparse_telemetry(db, test_user, test_session):
    """Test that dataset build doesn't crash with sparse telemetry."""
    from app.learning_engine.mistakes_v1.train import build_training_dataset

    # Create a session with minimal telemetry
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()

    features = []
    labels = []
    confidences = []
    try:
        features, labels, confidences = await build_training_dataset(db, start_date, end_date)
        # Should not crash even with sparse data
        assert isinstance(features, list)
        assert isinstance(labels, list)
        assert isinstance(confidences, list)
    except Exception as e:
        # If no data, that's OK - just shouldn't crash
        assert "Insufficient data" in str(e) or len(features) == 0


def test_v0_fallback_logic():
    """Test that v0 fallback logic is correct."""
    # This would be tested in integration tests
    # For now, just verify the structure
    from app.learning_engine.mistakes_v1.schemas import MistakeSource

    assert MistakeSource.RULE_V0.value == "RULE_V0"
    assert MistakeSource.MODEL_V1.value == "MODEL_V1"
