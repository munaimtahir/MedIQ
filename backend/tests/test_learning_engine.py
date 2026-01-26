"""
Tests for learning engine versioning and run logging.
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.learning_engine import (
    AlgoKey,
    AlgoStatus,
    RunStatus,
    RunTrigger,
    get_active_algo_version,
    get_active_params,
    log_run_failure,
    log_run_start,
    log_run_success,
    resolve_active,
)
from app.learning_engine.info import get_learning_engine_info
from app.learning_engine.registry import activate_algo_version, activate_params
from app.models.learning import AlgoParams, AlgoRun, AlgoVersion
from app.models.user import User, UserRole


class TestAlgoVersionSeeding:
    """Test that algorithm versions are properly seeded."""

    async def test_five_algorithms_seeded(self, db_session):
        """Test that all 5 algorithms are seeded with v0."""
        stmt = select(AlgoVersion).where(
            AlgoVersion.version == "v0",
            AlgoVersion.status == AlgoStatus.ACTIVE,
        )
        result = await db_session.execute(stmt)
        versions = result.scalars().all()

        # Should have 5 algorithms
        assert len(versions) == 5

        # Check all algo_keys are present
        algo_keys = {v.algo_key for v in versions}
        expected_keys = {
            AlgoKey.MASTERY.value,
            AlgoKey.REVISION.value,
            AlgoKey.DIFFICULTY.value,
            AlgoKey.ADAPTIVE.value,
            AlgoKey.MISTAKES.value,
        }
        assert algo_keys == expected_keys

    async def test_each_version_has_active_params(self, db_session):
        """Test that each algorithm version has active params."""
        for algo_key in AlgoKey:
            version = await get_active_algo_version(db_session, algo_key.value)
            assert version is not None, f"Missing active version for {algo_key.value}"

            params = await get_active_params(db_session, version.id)
            assert (
                params is not None
            ), f"Missing active params for {algo_key.value} v{version.version}"
            assert params.is_active is True

    async def test_default_params_populated(self, db_session):
        """Test that default parameters are populated correctly."""
        # Mastery should have threshold, decay_factor, min_attempts
        version, params = await resolve_active(db_session, AlgoKey.MASTERY.value)
        assert "threshold" in params.params_json
        assert "decay_factor" in params.params_json
        assert "min_attempts" in params.params_json

        # Revision should have intervals, ease_factor
        version, params = await resolve_active(db_session, AlgoKey.REVISION.value)
        assert "intervals" in params.params_json
        assert "ease_factor" in params.params_json


class TestAlgoVersionResolution:
    """Test algorithm version and parameter resolution."""

    async def test_get_active_algo_version(self, db_session):
        """Test getting active algorithm version."""
        version = await get_active_algo_version(db_session, AlgoKey.MASTERY.value)

        assert version is not None
        assert version.algo_key == AlgoKey.MASTERY.value
        assert version.status == AlgoStatus.ACTIVE
        assert version.version == "v0"

    async def test_get_active_params(self, db_session):
        """Test getting active parameters for a version."""
        version = await get_active_algo_version(db_session, AlgoKey.MASTERY.value)
        params = await get_active_params(db_session, version.id)

        assert params is not None
        assert params.algo_version_id == version.id
        assert params.is_active is True
        assert isinstance(params.params_json, dict)

    async def test_resolve_active(self, db_session):
        """Test resolving both version and params in one call."""
        version, params = await resolve_active(db_session, AlgoKey.MASTERY.value)

        assert version is not None
        assert params is not None
        assert version.algo_key == AlgoKey.MASTERY.value
        assert params.algo_version_id == version.id

    async def test_resolve_nonexistent_algorithm(self, db_session):
        """Test resolving a non-existent algorithm returns None."""
        version, params = await resolve_active(db_session, "nonexistent")

        assert version is None
        assert params is None


class TestAlgoVersionActivation:
    """Test activating different algorithm versions."""

    async def test_activate_algo_version(self, db_session):
        """Test activating a different version deactivates others."""
        # Create v1 version
        v1 = AlgoVersion(
            id=uuid4(),
            algo_key=AlgoKey.MASTERY.value,
            version="v1",
            status=AlgoStatus.EXPERIMENTAL,
            description="Test v1",
        )
        db_session.add(v1)
        await db_session.commit()

        # Activate v1
        activated = await activate_algo_version(db_session, AlgoKey.MASTERY.value, "v1")

        assert activated is not None
        assert activated.version == "v1"
        assert activated.status == AlgoStatus.ACTIVE

        # v0 should now be DEPRECATED
        v0 = await get_active_algo_version(db_session, AlgoKey.MASTERY.value)
        assert v0.version == "v1"  # Active version is now v1

        # Check v0 is deprecated
        stmt = select(AlgoVersion).where(
            AlgoVersion.algo_key == AlgoKey.MASTERY.value,
            AlgoVersion.version == "v0",
        )
        result = await db_session.execute(stmt)
        old_v0 = result.scalar_one()
        assert old_v0.status == AlgoStatus.DEPRECATED

    async def test_only_one_active_version_per_algo(self, db):
        """Test that only one version is active per algorithm."""
        stmt = select(AlgoVersion).where(
            AlgoVersion.algo_key == AlgoKey.MASTERY.value,
            AlgoVersion.status == AlgoStatus.ACTIVE,
        )
        result = await db.execute(stmt)
        active_versions = result.scalars().all()

        assert len(active_versions) == 1


class TestAlgoParamsActivation:
    """Test activating different parameter sets."""

    async def test_activate_params(self, db):
        """Test activating a new params set deactivates old one."""
        version = await get_active_algo_version(db, AlgoKey.MASTERY.value)

        # Create new params
        new_params = AlgoParams(
            id=uuid4(),
            algo_version_id=version.id,
            params_json={"threshold": 0.8, "decay_factor": 0.9, "min_attempts": 10},
            is_active=False,
        )
        db.add(new_params)
        await db.commit()

        # Activate new params
        activated = await activate_params(db, new_params.id)

        assert activated is not None
        assert activated.is_active is True
        assert activated.params_json["threshold"] == 0.8

        # Old params should be inactive
        stmt = select(AlgoParams).where(
            AlgoParams.algo_version_id == version.id,
            AlgoParams.id != new_params.id,
        )
        result = await db.execute(stmt)
        old_params = result.scalars().all()

        for params in old_params:
            assert params.is_active is False

    async def test_only_one_active_params_per_version(self, db_session):
        """Test that only one params set is active per version."""
        version = await get_active_algo_version(db_session, AlgoKey.MASTERY.value)

        stmt = select(AlgoParams).where(
            AlgoParams.algo_version_id == version.id,
            AlgoParams.is_active == True,  # noqa: E712
        )
        result = await db_session.execute(stmt)
        active_params = result.scalars().all()

        assert len(active_params) == 1


class TestAlgoRunLogging:
    """Test algorithm run logging."""

    @pytest.fixture
    async def student_user(self, db_session):
        """Create a test student user."""
        from app.core.security import hash_password
        user = User(
            id=uuid4(),
            email="student@test.com",
            password_hash=hash_password("Test123!"),
            full_name="Test Student",
            role=UserRole.STUDENT.value,
            is_active=True,
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    async def test_log_run_start(self, db_session, student_user):
        """Test logging the start of an algorithm run."""
        version, params = await resolve_active(db_session, AlgoKey.MASTERY.value)

        run = await log_run_start(
            db_session,
            algo_version_id=version.id,
            params_id=params.id,
            user_id=student_user.id,
            trigger=RunTrigger.MANUAL,
            input_summary={"block_id": 1},
        )

        assert run is not None
        assert run.algo_version_id == version.id
        assert run.params_id == params.id
        assert run.user_id == student_user.id
        assert run.trigger == RunTrigger.MANUAL
        assert run.status == RunStatus.RUNNING
        assert run.input_summary_json == {"block_id": 1}
        assert run.started_at is not None
        assert run.completed_at is None

    async def test_log_run_success(self, db_session, student_user):
        """Test marking a run as successful."""
        version, params = await resolve_active(db_session, AlgoKey.MASTERY.value)

        run = await log_run_start(
            db_session,
            algo_version_id=version.id,
            params_id=params.id,
            user_id=student_user.id,
        )

        await log_run_success(
            db_session,
            run_id=run.id,
            output_summary={"mastery_score": 0.75},
        )

        # Refresh run
        await db_session.refresh(run)

        assert run.status == RunStatus.SUCCESS
        assert run.completed_at is not None
        assert run.output_summary_json == {"mastery_score": 0.75}
        assert run.error_message is None

    async def test_log_run_failure(self, db_session, student_user):
        """Test marking a run as failed."""
        version, params = await resolve_active(db_session, AlgoKey.MASTERY.value)

        run = await log_run_start(
            db_session,
            algo_version_id=version.id,
            params_id=params.id,
            user_id=student_user.id,
        )

        error_msg = "Test error message"
        await log_run_failure(db_session, run_id=run.id, error_message=error_msg)

        # Refresh run
        await db_session.refresh(run)

        assert run.status == RunStatus.FAILED
        assert run.completed_at is not None
        assert run.error_message == error_msg

    async def test_run_logging_without_user(self, db_session):
        """Test logging a run without a specific user (global run)."""
        version, params = await resolve_active(db_session, AlgoKey.DIFFICULTY.value)

        run = await log_run_start(
            db_session,
            algo_version_id=version.id,
            params_id=params.id,
            user_id=None,
            trigger=RunTrigger.NIGHTLY,
        )

        assert run.user_id is None
        assert run.trigger == RunTrigger.NIGHTLY


class TestLearningEngineInfo:
    """Test learning engine info API."""

    async def test_get_learning_engine_info(self, db_session):
        """Test getting comprehensive learning engine info."""
        info = await get_learning_engine_info(db_session)

        assert len(info.algorithms) == 5

        # Check mastery is present
        mastery = next((a for a in info.algorithms if a.algo_key == AlgoKey.MASTERY.value), None)
        assert mastery is not None
        assert mastery.active_version == "v0"
        assert mastery.status == AlgoStatus.ACTIVE
        assert "threshold" in mastery.active_params
        assert mastery.updated_at is not None

    async def test_info_includes_all_algorithms(self, db_session):
        """Test that info includes all 5 algorithms."""
        info = await get_learning_engine_info(db_session)

        algo_keys = {a.algo_key for a in info.algorithms}
        expected_keys = {k.value for k in AlgoKey}

        assert algo_keys == expected_keys


class TestRunLoggingIndexes:
    """Test that indexes are created properly for performance."""

    @pytest.fixture
    async def student_user(self, db_session):
        """Create a test student user."""
        from app.core.security import hash_password
        user = User(
            id=uuid4(),
            email="student@test.com",
            password_hash=hash_password("Test123!"),
            full_name="Test Student",
            role=UserRole.STUDENT.value,
            is_active=True,
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    async def test_multiple_runs_for_user(self, db_session, student_user):
        """Test querying runs by user (uses index)."""
        version, params = await resolve_active(db_session, AlgoKey.MASTERY.value)

        # Create multiple runs
        for _i in range(3):
            await log_run_start(
                db_session,
                algo_version_id=version.id,
                params_id=params.id,
                user_id=student_user.id,
                trigger=RunTrigger.SUBMIT,
            )

        # Query runs by user
        stmt = select(AlgoRun).where(AlgoRun.user_id == student_user.id)
        result = await db_session.execute(stmt)
        runs = result.scalars().all()

        assert len(runs) == 3
        for run in runs:
            assert run.user_id == student_user.id
