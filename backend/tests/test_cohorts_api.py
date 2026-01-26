"""Tests for cohort analytics API endpoints."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.models.algo_runtime import AlgoRuntimeConfig, AlgoRuntimeProfile
from app.models.user import User, UserRole
from app.models.warehouse import (
    WarehouseExportDataset,
    WarehouseExportRun,
    WarehouseExportRunStatus,
    WarehouseExportRunType,
    WarehouseExportState,
)

client = TestClient(app)


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing."""
    user = User(
        email="admin@test.com",
        role=UserRole.ADMIN,
        password_hash="dummy",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def student_user(db):
    """Create a student user for testing."""
    user = User(
        email="student@test.com",
        role=UserRole.STUDENT,
        password_hash="dummy",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers_admin(admin_user):
    """Get auth headers for admin user."""
    # Note: In real tests, you'd generate a proper JWT token
    # For now, we'll mock the authentication
    return {"Authorization": f"Bearer mock_token_{admin_user.id}"}


@pytest.fixture
def auth_headers_student(student_user):
    """Get auth headers for student user."""
    return {"Authorization": f"Bearer mock_token_{student_user.id}"}


class TestCohortActivationGating:
    """Test cohort API activation gating."""

    def test_percentiles_disabled_when_warehouse_mode_not_active(self, db, admin_user):
        """Test that percentiles endpoint returns 403 when warehouse_mode != active."""
        # Set warehouse_mode to shadow (not active)
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "shadow", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        # Mock authentication (simplified - in real tests use proper JWT)
        # For now, we'll test the service directly
        from app.cohorts.service import get_percentiles

        result = get_percentiles(db, "mastery_prob", "theme", 1, "30d")

        assert "error" in result
        assert result["error"] == "feature_disabled"
        assert result["data_source"] == "disabled"
        assert len(result["blocking_reasons"]) > 0
        assert any("warehouse_mode" in reason for reason in result["blocking_reasons"])

    def test_percentiles_disabled_when_snowflake_not_enabled(self, db, admin_user):
        """Test that percentiles endpoint returns 403 when SNOWFLAKE_ENABLED=false."""
        # Set warehouse_mode to active
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "active", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        # Mock SNOWFLAKE_ENABLED=False (default)
        from app.cohorts.service import get_percentiles
        from app.core.config import settings

        original_value = settings.SNOWFLAKE_ENABLED
        try:
            settings.SNOWFLAKE_ENABLED = False
            result = get_percentiles(db, "mastery_prob", "theme", 1, "30d")

            assert "error" in result
            assert result["error"] == "feature_disabled"
            assert result["data_source"] == "disabled"
            assert any("SNOWFLAKE_ENABLED" in reason for reason in result["blocking_reasons"])
        finally:
            settings.SNOWFLAKE_ENABLED = original_value

    def test_percentiles_disabled_when_no_recent_exports(self, db, admin_user):
        """Test that percentiles endpoint returns 403 when no recent successful exports."""
        # Set warehouse_mode to active
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "active", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        # Mock SNOWFLAKE_ENABLED=True and readiness=True
        from app.cohorts.service import get_percentiles
        from app.core.config import settings
        from unittest.mock import patch
        from app.warehouse.snowflake_readiness import SnowflakeReadinessStatus

        original_value = settings.SNOWFLAKE_ENABLED
        try:
            settings.SNOWFLAKE_ENABLED = True
            # Mock snowflake readiness to be ready so we can test the export check
            with patch("app.cohorts.service.check_snowflake_readiness") as mock_readiness:
                mock_readiness.return_value = SnowflakeReadinessStatus(ready=True, reason="")
                # No export runs in database
                result = get_percentiles(db, "mastery_prob", "theme", 1, "30d")

                assert "error" in result
                assert result["error"] == "feature_disabled"
                assert result["data_source"] == "disabled"
                # Check for blocking reason about missing exports (message format: "no successful export for {dataset} in last 24h")
                blocking_reasons_str = " ".join(result["blocking_reasons"]).lower()
                assert "no successful export" in blocking_reasons_str or ("export" in blocking_reasons_str and "24h" in blocking_reasons_str)
        finally:
            settings.SNOWFLAKE_ENABLED = original_value

    def test_percentiles_enabled_when_all_checks_pass(self, db, admin_user):
        """Test that percentiles endpoint returns not_implemented when all checks pass."""
        # Set warehouse_mode to active
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "active", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        # Create recent successful export runs (within last 24h, check requires >= 24h cutoff)
        # Use 12 hours ago to ensure it's within the 24h window
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=12)
        # Each dataset needs its own run_id since run_id is the primary key
        for dataset in [WarehouseExportDataset.ATTEMPTS, WarehouseExportDataset.EVENTS, WarehouseExportDataset.MASTERY]:
            run = WarehouseExportRun(
                run_id=uuid4(),  # Unique run_id for each dataset
                run_type=WarehouseExportRunType.INCREMENTAL.value,  # Must use .value to get "incremental" (lowercase)
                dataset=dataset,
                range_start=cutoff_time - timedelta(hours=1),
                range_end=cutoff_time,
                status=WarehouseExportRunStatus.SHADOW_DONE_FILES_ONLY.value,  # Must use .value to get lowercase string
                finished_at=cutoff_time,  # 12 hours ago, well within 24h window
                rows_exported=100,
                files_written=1,
            )
            db.add(run)
        db.commit()

        # Mock SNOWFLAKE_ENABLED=True and readiness=True
        from app.cohorts.service import get_percentiles
        from app.core.config import settings
        from unittest.mock import patch

        original_value = settings.SNOWFLAKE_ENABLED
        try:
            settings.SNOWFLAKE_ENABLED = True
            # Mock snowflake readiness to return ready=True
            with patch("app.cohorts.service.check_snowflake_readiness") as mock_readiness:
                from app.warehouse.snowflake_readiness import SnowflakeReadinessStatus

                mock_readiness.return_value = SnowflakeReadinessStatus(
                    ready=True,
                    reason=None,
                    checks={"snowflake_enabled": True},
                )

                result = get_percentiles(db, "mastery_prob", "theme", 1, "30d")

                # Should return not_implemented (not disabled)
                assert "error" in result
                assert result["error"] == "not_implemented"
                assert result["data_source"] == "snowflake"
        finally:
            settings.SNOWFLAKE_ENABLED = original_value

    def test_comparisons_disabled_when_warehouse_mode_not_active(self, db, admin_user):
        """Test that comparisons endpoint returns 403 when warehouse_mode != active."""
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "shadow", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        from app.cohorts.service import get_comparisons

        result = get_comparisons(
            db,
            {"scope": "year", "id": 1},
            {"scope": "year", "id": 2},
            "mastery_prob",
            "30d",
        )

        assert "error" in result
        assert result["error"] == "feature_disabled"
        assert result["data_source"] == "disabled"

    def test_rank_sim_disabled_when_warehouse_mode_not_active(self, db, admin_user):
        """Test that rank-sim endpoint returns 403 when warehouse_mode != active."""
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "shadow", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        from app.cohorts.service import get_rank_sim

        result = get_rank_sim(db, "user-123", "year", 1, "30d")

        assert "error" in result
        assert result["error"] == "feature_disabled"
        assert result["data_source"] == "disabled"


class TestCohortResponseContracts:
    """Test that response contracts are stable."""

    def test_disabled_response_always_has_data_source_and_blocking_reasons(self, db):
        """Test that disabled responses always include data_source and blocking_reasons."""
        from app.cohorts.service import get_percentiles

        result = get_percentiles(db, "mastery_prob", "theme", 1, "30d")

        assert "error" in result
        assert result["error"] == "feature_disabled"
        assert "data_source" in result
        assert result["data_source"] == "disabled"
        assert "blocking_reasons" in result
        assert isinstance(result["blocking_reasons"], list)
        assert len(result["blocking_reasons"]) > 0
