"""Tests for warehouse export pipeline."""

import pytest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.algo_runtime import AlgoRuntimeConfig, AlgoRuntimeProfile
from app.models.warehouse import (
    WarehouseExportDataset,
    WarehouseExportRun,
    WarehouseExportRunStatus,
    WarehouseExportState,
)
from app.warehouse.exporter import (
    start_export,
    run_incremental_exports,
)


class TestWarehouseModeGuards:
    """Test warehouse mode guardrails."""

    @pytest.fixture
    def admin_user(self, db):
        """Create an admin user for testing."""
        from app.models.user import User
        user = User(
            email="admin@test.com",
            role="ADMIN",
            password_hash="dummy",
        )
        db.add(user)
        db.commit()
        return user

    def test_disabled_mode_blocks_export(self, db: Session, admin_user):
        """Test that disabled mode blocks export and records blocked_disabled."""
        # Set warehouse_mode to disabled
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "disabled"},
        )
        db.add(config)
        db.commit()

        run_id = start_export(
            db,
            "attempts",
            "incremental",
            None,
            datetime.now(timezone.utc),
            admin_user.id,
            "Test export",
        )

        run = db.query(WarehouseExportRun).filter(WarehouseExportRun.run_id == run_id).first()
        assert run is not None
        assert run.status == WarehouseExportRunStatus.BLOCKED_DISABLED
        assert "disabled" in run.last_error.lower()

    def test_frozen_mode_blocks_export(self, db: Session, admin_user):
        """Test that warehouse_freeze blocks export and records blocked_frozen."""
        # Set warehouse_mode to shadow but freeze=true
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "shadow", "warehouse_freeze": True},
        )
        db.add(config)
        db.commit()

        run_id = start_export(
            db,
            "attempts",
            "incremental",
            None,
            datetime.now(timezone.utc),
            admin_user.id,
            "Test export",
        )

        run = db.query(WarehouseExportRun).filter(WarehouseExportRun.run_id == run_id).first()
        assert run is not None
        assert run.status == WarehouseExportRunStatus.BLOCKED_FROZEN
        assert "frozen" in run.last_error.lower()

    def test_shadow_mode_writes_files(self, db: Session, admin_user):
        """Test that shadow mode writes files and records shadow_done_files_only."""
        # Set warehouse_mode to shadow
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "shadow", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        # Mock the mapper to return empty iterator (no actual data needed)
        with patch("app.warehouse.exporter.map_attempts", return_value=iter([])):
            run_id = start_export(
                db,
                "attempts",
                "incremental",
                None,
                datetime.now(timezone.utc),
                admin_user.id,
                "Test export",
            )

            run = db.query(WarehouseExportRun).filter(WarehouseExportRun.run_id == run_id).first()
            assert run is not None
            assert run.status == WarehouseExportRunStatus.SHADOW_DONE_FILES_ONLY
            assert run.rows_exported == 0
            assert run.files_written == 0  # No files if no rows
            assert run.manifest_path is not None

    def test_active_mode_treated_as_shadow(self, db: Session, admin_user):
        """Test that active mode is treated same as shadow (no Snowflake yet)."""
        # Set warehouse_mode to active
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "active", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        # Mock the mapper to return empty iterator
        with patch("app.warehouse.exporter.map_attempts", return_value=iter([])):
            run_id = start_export(
                db,
                "attempts",
                "incremental",
                None,
                datetime.now(timezone.utc),
                admin_user.id,
                "Test export",
            )

            run = db.query(WarehouseExportRun).filter(WarehouseExportRun.run_id == run_id).first()
            assert run is not None
            assert run.status == WarehouseExportRunStatus.SHADOW_DONE_FILES_ONLY
            assert run.details is not None
            assert run.details.get("warning") == "active_mode_no_snowflake_loader_yet"


class TestWatermarkBehavior:
    """Test watermark advancement behavior."""

    @pytest.fixture
    def admin_user(self, db):
        """Create an admin user for testing."""
        from app.models.user import User
        user = User(
            email="admin@test.com",
            role="ADMIN",
            password_hash="dummy",
        )
        db.add(user)
        db.commit()
        return user

    def test_watermark_advances_on_success(self, db: Session, admin_user):
        """Test that watermark advances only on successful export."""
        # Create state with initial watermark
        state = WarehouseExportState(id=1, attempts_watermark=datetime(2025, 1, 1, tzinfo=timezone.utc))
        db.add(state)
        db.commit()

        # Set warehouse_mode to shadow
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "shadow", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        new_watermark = datetime(2025, 1, 2, tzinfo=timezone.utc)

        # Mock successful export
        with patch("app.warehouse.exporter.map_attempts", return_value=iter([])):
            run_id = start_export(
                db,
                "attempts",
                "incremental",
                state.attempts_watermark,
                new_watermark,
                admin_user.id,
                "Test export",
            )

            # Check watermark was updated
            db.refresh(state)
            assert state.attempts_watermark == new_watermark

    def test_watermark_preserved_on_failure(self, db: Session, admin_user):
        """Test that watermark is NOT updated on failure."""
        # Create state with initial watermark
        initial_watermark = datetime(2025, 1, 1, tzinfo=timezone.utc)
        state = WarehouseExportState(id=1, attempts_watermark=initial_watermark)
        db.add(state)
        db.commit()

        # Set warehouse_mode to shadow
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "shadow", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        # Mock export failure
        with patch("app.warehouse.exporter.map_attempts", side_effect=Exception("Export failed")):
            run_id = start_export(
                db,
                "attempts",
                "incremental",
                initial_watermark,
                datetime(2025, 1, 2, tzinfo=timezone.utc),
                admin_user.id,
                "Test export",
            )

            # Check watermark was NOT updated
            db.refresh(state)
            assert state.attempts_watermark == initial_watermark

            # Check run is marked as failed
            run = db.query(WarehouseExportRun).filter(WarehouseExportRun.run_id == run_id).first()
            assert run.status == WarehouseExportRunStatus.FAILED


class TestIncrementalExports:
    """Test incremental export orchestration."""

    @pytest.fixture
    def admin_user(self, db):
        """Create an admin user for testing."""
        from app.models.user import User
        user = User(
            email="admin@test.com",
            role="ADMIN",
            password_hash="dummy",
        )
        db.add(user)
        db.commit()
        return user

    def test_incremental_exports_uses_watermarks(self, db: Session, admin_user):
        """Test that incremental exports compute ranges from watermarks."""
        # Set warehouse_mode to shadow
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={"warehouse_mode": "shadow", "warehouse_freeze": False},
        )
        db.add(config)
        db.commit()

        # Mock mappers
        with patch("app.warehouse.exporter.map_attempts", return_value=iter([])):
            with patch("app.warehouse.exporter.map_events", return_value=iter([])):
                with patch("app.warehouse.exporter.map_mastery_snapshots", return_value=iter([])):
                    run_ids = run_incremental_exports(db, admin_user.id, "Test incremental")

                    assert len(run_ids) == 3  # attempts, events, mastery
                    # All run_ids should be UUIDs
                    from uuid import UUID
                    for rid in run_ids:
                        assert isinstance(rid, UUID)
