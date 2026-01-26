"""Tests for IRT activation policy."""

import pytest
from uuid import uuid4

from app.learning_engine.irt.activation_policy import evaluate_irt_activation
from app.models.irt import IrtCalibrationRun


@pytest.mark.asyncio
async def test_activation_policy_requires_succeeded_run(db_session):
    """Test that activation evaluation requires SUCCEEDED run."""
    # Create a run with status != SUCCEEDED
    run = IrtCalibrationRun(
        id=uuid4(),
        model_type="IRT_2PL",
        dataset_spec={},
        status="RUNNING",
        seed=42,
    )
    db_session.add(run)
    await db_session.commit()

    with pytest.raises(ValueError, match="Run must be SUCCEEDED"):
        await evaluate_irt_activation(db_session, run.id, "IRT_2PL")


@pytest.mark.asyncio
async def test_activation_policy_gate_a_data_sufficiency(db_session):
    """Test Gate A: Minimum Data Sufficiency."""
    # Create a succeeded run with insufficient data
    run = IrtCalibrationRun(
        id=uuid4(),
        model_type="IRT_2PL",
        dataset_spec={},
        status="SUCCEEDED",
        seed=42,
        metrics={
            "n_users_train": 100,  # Below threshold (500)
            "n_items_train": 500,  # Below threshold (1000)
            "n_attempts_train": 50000,  # Below threshold (100000)
            "median_attempts_per_item": 20.0,  # Below threshold (50)
            "median_attempts_per_user": 50.0,  # Below threshold (100)
        },
    )
    db_session.add(run)
    await db_session.commit()

    decision = await evaluate_irt_activation(db_session, run.id, "IRT_2PL")

    assert not decision.eligible
    gate_a = next(g for g in decision.gates if "Gate A" in g.name)
    assert not gate_a.passed


@pytest.mark.asyncio
async def test_activation_requires_human_ack(db_session):
    """Test that activation always requires human acknowledgement."""
    # Create a succeeded run with sufficient data
    run = IrtCalibrationRun(
        id=uuid4(),
        model_type="IRT_2PL",
        dataset_spec={},
        status="SUCCEEDED",
        seed=42,
        metrics={
            "n_users_train": 1000,
            "n_items_train": 2000,
            "n_attempts_train": 200000,
            "median_attempts_per_item": 100.0,
            "median_attempts_per_user": 200.0,
        },
    )
    db_session.add(run)
    await db_session.commit()

    decision = await evaluate_irt_activation(db_session, run.id, "IRT_2PL")

    # Even if eligible, requires human ack
    assert decision.requires_human_ack is True


# Note: Full integration tests would require:
# - Mock eval_run with metrics
# - Mock baseline comparison
# - Mock item parameters for stability check
# - Mock user abilities for precision check
# These are placeholders showing the test structure.
