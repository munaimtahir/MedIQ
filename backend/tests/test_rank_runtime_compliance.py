"""Tests for rank prediction runtime compliance."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.runtime import (
    get_rank_mode,
    is_rank_enabled_for_admin,
    is_rank_enabled_for_student,
    is_safe_mode_freeze_updates,
)
from app.models.algo_runtime import AlgoRuntimeConfig
from app.models.rank import RankPredictionSnapshot, RankSnapshotStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_rank_default_mode_is_shadow(db_session: AsyncSession):
    """Test that rank defaults to shadow mode."""
    mode = await get_rank_mode(db_session)
    assert mode == "shadow"


@pytest.mark.asyncio
async def test_rank_v0_override_disables(db_session: AsyncSession):
    """Test that rank override v0 disables rank."""
    # Set override to v0
    stmt = AlgoRuntimeConfig.__table__.select().limit(1)
    result = await db_session.execute(stmt)
    config_row = result.first()

    if config_row:
        config = await db_session.get(AlgoRuntimeConfig, config_row[0])
        config.config_json = config.config_json or {}
        config.config_json["overrides"] = config.config_json.get("overrides", {})
        config.config_json["overrides"]["rank"] = "v0"
        await db_session.commit()

        mode = await get_rank_mode(db_session)
        assert mode == "v0"

        enabled_admin = await is_rank_enabled_for_admin(db_session)
        assert enabled_admin is False

        enabled_student = await is_rank_enabled_for_student(db_session)
        assert enabled_student is False


@pytest.mark.asyncio
async def test_rank_shadow_enabled_for_admin(db_session: AsyncSession):
    """Test that shadow mode enables admin operations."""
    # Set override to shadow
    stmt = AlgoRuntimeConfig.__table__.select().limit(1)
    result = await db_session.execute(stmt)
    config_row = result.first()

    if config_row:
        config = await db_session.get(AlgoRuntimeConfig, config_row[0])
        config.config_json = config.config_json or {}
        config.config_json["overrides"] = config.config_json.get("overrides", {})
        config.config_json["overrides"]["rank"] = "shadow"
        await db_session.commit()

        enabled_admin = await is_rank_enabled_for_admin(db_session)
        assert enabled_admin is True

        enabled_student = await is_rank_enabled_for_student(db_session)
        assert enabled_student is False


@pytest.mark.asyncio
async def test_rank_freeze_mode_blocks_snapshots(db_session: AsyncSession):
    """Test that freeze_updates blocks rank snapshot computation."""
    from app.learning_engine.rank.model_v1 import compute_rank_snapshot
    from app.models.user import User

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

        # Try to compute snapshot
        snapshot = await compute_rank_snapshot(db_session, test_user.id)

        assert snapshot is not None
        assert snapshot.status == RankSnapshotStatus.BLOCKED_FROZEN


@pytest.mark.asyncio
async def test_rank_v1_requires_student_flag(db_session: AsyncSession):
    """Test that v1 mode requires student feature flag for student operations."""
    # Set override to v1
    stmt = AlgoRuntimeConfig.__table__.select().limit(1)
    result = await db_session.execute(stmt)
    config_row = result.first()

    if config_row:
        config = await db_session.get(AlgoRuntimeConfig, config_row[0])
        config.config_json = config.config_json or {}
        config.config_json["overrides"] = config.config_json.get("overrides", {})
        config.config_json["overrides"]["rank"] = "v1"
        await db_session.commit()

        # Without student flag, should be disabled
        enabled_student = await is_rank_enabled_for_student(db_session)
        assert enabled_student is False

        # With student flag (via platform_settings), should be enabled
        from app.models.platform_settings import PlatformSettings
        from sqlalchemy import select

        stmt_settings = select(PlatformSettings).where(PlatformSettings.id == 1)
        result_settings = await db_session.execute(stmt_settings)
        settings = result_settings.scalar_one_or_none()

        if settings:
            settings.data = settings.data or {}
            settings.data["rank"] = {"student_enabled": True}
            await db_session.commit()

            enabled_student = await is_rank_enabled_for_student(db_session)
            assert enabled_student is True
