"""Tests for evaluation harness."""

import pytest
import numpy as np

from app.learning_engine.eval.metrics.calibration import (
    brier_score,
    expected_calibration_error,
    log_loss,
)


def test_log_loss():
    """Test log loss computation."""
    y_true = [True, False, True, False]
    y_pred = [0.9, 0.1, 0.8, 0.2]

    loss = log_loss(y_true, y_pred)
    assert loss > 0
    assert loss < 1.0  # Should be reasonable for good predictions


def test_brier_score():
    """Test Brier score computation."""
    y_true = [True, False, True, False]
    y_pred = [0.9, 0.1, 0.8, 0.2]

    brier = brier_score(y_true, y_pred)
    assert 0 <= brier <= 1
    assert brier < 0.1  # Should be low for good predictions


def test_expected_calibration_error():
    """Test ECE computation."""
    # Perfectly calibrated predictions
    y_true = [True] * 50 + [False] * 50
    y_pred = [0.9] * 50 + [0.1] * 50

    ece, bin_details = expected_calibration_error(y_true, y_pred, n_bins=10)
    assert ece >= 0
    assert len(bin_details["bins"]) == 10


def test_calibration_metrics_on_known_inputs():
    """Test calibration metrics on small known inputs."""
    # Perfect predictions
    y_true = [True, True, False, False]
    y_pred = [1.0, 1.0, 0.0, 0.0]

    loss = log_loss(y_true, y_pred)
    brier = brier_score(y_true, y_pred)

    # Should be very low (near perfect)
    assert loss < 0.1
    assert brier < 0.1


def test_dataset_split_time():
    """Test time-based split strategy."""
    from app.learning_engine.eval.dataset import EvalEvent, apply_split
    from datetime import datetime
    from uuid import uuid4

    # Create events with timestamps
    events = [
        EvalEvent(
            event_id=uuid4(),
            user_id=uuid4(),
            session_id=uuid4(),
            question_id=uuid4(),
            timestamp=datetime(2024, 1, i),
            is_correct=True,
        )
        for i in range(1, 11)
    ]

    train, eval_events = apply_split(events, "time", {"train_ratio": 0.8})

    assert len(train) == 8
    assert len(eval_events) == 2
    assert train[-1].timestamp < eval_events[0].timestamp


def test_dataset_split_user_holdout():
    """Test user holdout split strategy."""
    from app.learning_engine.eval.dataset import EvalEvent, apply_split
    from datetime import datetime
    from uuid import uuid4

    user1 = uuid4()
    user2 = uuid4()

    # Create events for two users
    events = []
    for user_id in [user1, user2]:
        for i in range(1, 11):
            events.append(
                EvalEvent(
                    event_id=uuid4(),
                    user_id=user_id,
                    session_id=uuid4(),
                    question_id=uuid4(),
                    timestamp=datetime(2024, 1, i),
                    is_correct=True,
                )
            )

    train, eval_events = apply_split(events, "user_holdout", {"holdout_ratio": 0.2})

    # Should have holdout from each user
    assert len(eval_events) > 0
    assert len(train) > len(eval_events)


def test_determinism():
    """Test that same inputs produce same outputs."""
    y_true = [True, False, True, False, True]
    y_pred = [0.9, 0.1, 0.8, 0.2, 0.7]

    # Run twice
    loss1 = log_loss(y_true, y_pred)
    loss2 = log_loss(y_true, y_pred)

    assert loss1 == loss2

    brier1 = brier_score(y_true, y_pred)
    brier2 = brier_score(y_true, y_pred)

    assert brier1 == brier2
