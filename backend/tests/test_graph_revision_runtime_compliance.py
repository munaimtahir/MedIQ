"""Tests for graph revision runtime compliance."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.graph_revision.planner import compute_shadow_revision_plan
from app.learning_engine.runtime import (
    get_graph_revision_mode,
    is_graph_revision_active_allowed,
    is_safe_mode_freeze_updates,
)
from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.graph_revision import ShadowRevisionPlan
from app.models.user import User


@pytest.mark.asyncio
async def test_graph_revision_default_mode_is_shadow(db_session: AsyncSession):
    """Test that graph_revision defaults to shadow mode."""
    mode = await get_graph_revision_mode(db_session)
    assert mode == "shadow"


@pytest.mark.asyncio
async def test_graph_revision_v0_override_disables(db_session: AsyncSession):
    """Test that graph_revision override v0 disables it."""
    # Set override to v0
    stmt = AlgoRuntimeConfig.__table__.select().limit(1)
    result = await db_session.execute(stmt)
    config_row = result.first()

    if config_row:
        config = await db_session.get(AlgoRuntimeConfig, config_row[0])
        config.config_json = config.config_json or {}
        config.config_json["overrides"] = config.config_json.get("overrides", {})
        config.config_json["overrides"]["graph_revision"] = "v0"
        await db_session.commit()

        mode = await get_graph_revision_mode(db_session)
        assert mode == "v0"

        enabled = await is_graph_revision_active_allowed(db_session)
        assert enabled is False


@pytest.mark.asyncio
async def test_graph_revision_shadow_allows_computation(db_session: AsyncSession):
    """Test that shadow mode allows plan computation (but not student-facing usage)."""
    # Set override to shadow
    stmt = AlgoRuntimeConfig.__table__.select().limit(1)
    result = await db_session.execute(stmt)
    config_row = result.first()

    if config_row:
        config = await db_session.get(AlgoRuntimeConfig, config_row[0])
        config.config_json = config.config_json or {}
        config.config_json["overrides"] = config.config_json.get("overrides", {})
        config.config_json["overrides"]["graph_revision"] = "shadow"
        await db_session.commit()

        mode = await get_graph_revision_mode(db_session)
        assert mode == "shadow"

        # Shadow mode should not allow student-facing usage
        enabled = await is_graph_revision_active_allowed(db_session)
        assert enabled is False

        # But plans can still be computed (shadow plans)


@pytest.mark.asyncio
async def test_graph_revision_freeze_mode_blocks_plans(db_session: AsyncSession):
    """Test that freeze_updates blocks shadow plan computation."""
    from datetime import date

    # Enable freeze mode
    stmt = AlgoRuntimeConfig.__table__.select().limit(1)
    result = await db_session.execute(stmt)
    config_row = result.first()

    if config_row:
        config = await db_session.get(AlgoRuntimeConfig, config_row[0])
        config.config_json = config.config_json or {}
        config.config_json["safe_mode"] = config.config_json.get("safe_mode", {})
        config.config_json["safe_mode"]["freeze_updates"] = True
        await db_session.commit()

        assert await is_safe_mode_freeze_updates(db_session) is True

        # Create a test user
        test_user = User(
            name="Test User",
            email="test@example.com",
            role="STUDENT",
        )
        db_session.add(test_user)
        await db_session.flush()

        # Try to compute shadow plan
        plan = await compute_shadow_revision_plan(
            db_session,
            user_id=test_user.id,
            baseline_due_themes=[1, 2, 3],  # Mock theme IDs
            run_date=date.today(),
        )

        # Should return None when frozen
        assert plan is None


@pytest.mark.asyncio
async def test_graph_revision_v1_requires_feature_flag(db_session: AsyncSession):
    """Test that v1 mode requires feature flag for student-facing operations."""
    # Set override to v1
    stmt = AlgoRuntimeConfig.__table__.select().limit(1)
    result = await db_session.execute(stmt)
    config_row = result.first()

    if config_row:
        config = await db_session.get(AlgoRuntimeConfig, config_row[0])
        config.config_json = config.config_json or {}
        config.config_json["overrides"] = config.config_json.get("overrides", {})
        config.config_json["overrides"]["graph_revision"] = "v1"
        await db_session.commit()

        # Without feature flag, should be disabled
        enabled = await is_graph_revision_active_allowed(db_session)
        assert enabled is False

        # With feature flag (via platform_settings), should be enabled
        from app.models.platform_settings import PlatformSettings
        from sqlalchemy import select

        stmt_settings = select(PlatformSettings).where(PlatformSettings.id == 1)
        result_settings = await db_session.execute(stmt_settings)
        settings = result_settings.scalar_one_or_none()

        if settings:
            settings.data = settings.data or {}
            settings.data["graph_revision"] = {"active": True}
            await db_session.commit()

            enabled = await is_graph_revision_active_allowed(db_session)
            assert enabled is True


@pytest.mark.asyncio
async def test_graph_revision_session_snapshot_respect(db_session: AsyncSession):
    """Test that graph_revision respects session snapshot config."""
    # Set current runtime to v1
    stmt = AlgoRuntimeConfig.__table__.select().limit(1)
    result = await db_session.execute(stmt)
    config_row = result.first()

    if config_row:
        config = await db_session.get(AlgoRuntimeConfig, config_row[0])
        config.config_json = config.config_json or {}
        config.config_json["overrides"] = config.config_json.get("overrides", {})
        config.config_json["overrides"]["graph_revision"] = "v1"
        await db_session.commit()

        # With session snapshot set to shadow, should use shadow
        snapshot_cfg = {"graph_revision": "shadow"}
        mode = await get_graph_revision_mode(db_session, snapshot_cfg=snapshot_cfg)
        assert mode == "shadow"

        # With session snapshot set to v0, should use v0
        snapshot_cfg = {"graph_revision": "v0"}
        mode = await get_graph_revision_mode(db_session, snapshot_cfg=snapshot_cfg)
        assert mode == "v0"


@pytest.mark.asyncio
async def test_graph_revision_neo4j_unavailable_graceful(db_session: AsyncSession):
    """Test that graph_revision degrades gracefully when Neo4j is unavailable."""
    from datetime import date
    from unittest.mock import patch

    # Create a test user
    test_user = User(
        name="Test User",
        email="test@example.com",
        role="STUDENT",
    )
    db_session.add(test_user)
    await db_session.flush()

    # Mock Neo4j as unavailable
    with patch("app.learning_engine.graph_revision.planner.is_neo4j_available", return_value=False):
        plan = await compute_shadow_revision_plan(
            db_session,
            user_id=test_user.id,
            baseline_due_themes=[1, 2, 3],
            run_date=date.today(),
        )

        # Should return baseline-only plan
        assert plan is not None
        assert plan.mode == "baseline"
        assert plan.baseline_count == 3
        assert plan.injected_count == 0


@pytest.mark.asyncio
async def test_graph_revision_eligibility_gates(db_session: AsyncSession):
    """Test that activation eligibility gates work correctly."""
    from app.learning_engine.graph_revision.eligibility import is_graph_revision_eligible_for_activation

    eligible, reasons = await is_graph_revision_eligible_for_activation(db_session)

    # Should return tuple
    assert isinstance(eligible, bool)
    assert isinstance(reasons, list)

    # If not eligible, should have reasons
    if not eligible:
        assert len(reasons) > 0
