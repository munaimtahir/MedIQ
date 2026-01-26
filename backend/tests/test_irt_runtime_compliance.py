"""Tests for IRT runtime/kill-switch/bridge framework compliance."""

import pytest
from sqlalchemy import select
from uuid import UUID, uuid4

from app.learning_engine.runtime import (
    is_irt_active_allowed,
    is_irt_shadow_enabled,
    get_effective_irt_state,
    MODULE_IRT,
)
from app.models.algo_runtime import AlgoRuntimeConfig, AlgoRuntimeProfile
from app.models.platform_settings import PlatformSettings
from app.learning_engine.irt.runner import run_irt_calibration
from app.learning_engine.irt.registry import create_irt_run


@pytest.mark.asyncio
async def test_irt_shadow_enabled_default(db_session):
    """Test that IRT shadow is enabled by default."""
    enabled = await is_irt_shadow_enabled(db_session)
    assert enabled is True, "IRT shadow should be enabled by default"


@pytest.mark.asyncio
async def test_irt_shadow_enabled_from_settings(db_session):
    """Test that IRT shadow respects platform_settings."""
    # Create/update platform settings
    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db_session.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = PlatformSettings(id=1, data={})
        db_session.add(settings)
    
    if not settings.data:
        settings.data = {}
    
    # Disable shadow
    settings.data["irt"] = {"shadow": False}
    await db_session.commit()
    await db_session.refresh(settings)
    
    enabled = await is_irt_shadow_enabled(db_session)
    assert enabled is False, "IRT shadow should be disabled when set in platform_settings"
    
    # Re-enable
    settings.data["irt"] = {"shadow": True}
    await db_session.commit()
    
    enabled = await is_irt_shadow_enabled(db_session)
    assert enabled is True, "IRT shadow should be enabled when set in platform_settings"


@pytest.mark.asyncio
async def test_irt_active_allowed_requires_flags(db_session):
    """Test that IRT active requires FEATURE_IRT_ACTIVE flag."""
    # Ensure runtime config exists
    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db_session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={
                "profile": "V1_PRIMARY",
                "overrides": {},
                "safe_mode": {"freeze_updates": False, "prefer_cache": True},
            },
        )
        db_session.add(config)
        await db_session.commit()
    
    # With IRT not active in platform_settings
    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db_session.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = PlatformSettings(id=1, data={})
        db_session.add(settings)
    
    if not settings.data:
        settings.data = {}
    
    settings.data["irt"] = {"active": False, "shadow": True}
    await db_session.commit()
    
    allowed = await is_irt_active_allowed(db_session)
    assert allowed is False, "IRT should not be active when FEATURE_IRT_ACTIVE is False"
    
    # Enable active flag
    settings.data["irt"] = {"active": True, "shadow": True}
    await db_session.commit()
    
    allowed = await is_irt_active_allowed(db_session)
    assert allowed is True, "IRT should be active when FEATURE_IRT_ACTIVE is True and not frozen"


@pytest.mark.asyncio
async def test_irt_active_blocked_by_v0_override(db_session):
    """Test that IRT v0 override blocks activation even if flag is on."""
    # Ensure runtime config exists
    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db_session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={
                "profile": "V1_PRIMARY",
                "overrides": {MODULE_IRT: "v0"},
                "safe_mode": {"freeze_updates": False, "prefer_cache": True},
            },
        )
        db_session.add(config)
        await db_session.commit()
    else:
        config.config_json = config.config_json or {}
        config.config_json["overrides"] = {MODULE_IRT: "v0"}
        await db_session.commit()
    
    # Enable active flag
    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db_session.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = PlatformSettings(id=1, data={})
        db_session.add(settings)
    
    if not settings.data:
        settings.data = {}
    
    settings.data["irt"] = {"active": True, "shadow": True}
    await db_session.commit()
    
    allowed = await is_irt_active_allowed(db_session)
    assert allowed is False, "IRT should be blocked when override is v0"


@pytest.mark.asyncio
async def test_irt_active_blocked_by_freeze_mode(db_session):
    """Test that freeze_updates blocks IRT activation."""
    # Ensure runtime config exists with freeze mode
    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db_session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={
                "profile": "V1_PRIMARY",
                "overrides": {},
                "safe_mode": {"freeze_updates": True, "prefer_cache": True},
            },
        )
        db_session.add(config)
        await db_session.commit()
    else:
        config.config_json = config.config_json or {}
        config.config_json["safe_mode"] = {"freeze_updates": True, "prefer_cache": True}
        await db_session.commit()
    
    # Enable active flag
    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db_session.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = PlatformSettings(id=1, data={})
        db_session.add(settings)
    
    if not settings.data:
        settings.data = {}
    
    settings.data["irt"] = {"active": True, "shadow": True}
    await db_session.commit()
    
    allowed = await is_irt_active_allowed(db_session)
    assert allowed is False, "IRT should be blocked when freeze_updates is True"


@pytest.mark.asyncio
async def test_irt_runner_blocks_on_freeze_mode(db_session):
    """Test that IRT runner blocks execution when freeze_updates is enabled."""
    # Set freeze mode
    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db_session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={
                "profile": "V1_PRIMARY",
                "overrides": {},
                "safe_mode": {"freeze_updates": True, "prefer_cache": True},
            },
        )
        db_session.add(config)
        await db_session.commit()
    else:
        config.config_json = config.config_json or {}
        config.config_json["safe_mode"] = {"freeze_updates": True, "prefer_cache": True}
        await db_session.commit()
    
    # Create a test run
    run = await create_irt_run(
        db_session,
        model_type="IRT_2PL",
        dataset_spec={"time_min": None, "time_max": None},
        seed=42,
        notes="Test run for freeze mode",
    )
    
    # Attempt to run calibration
    await run_irt_calibration(db_session, run.id)
    
    # Check that run was blocked
    await db_session.refresh(run)
    assert run.status == "FAILED", "Run should be FAILED when freeze mode is enabled"
    assert "freeze_updates" in (run.error or "").lower(), "Error should mention freeze_updates"


@pytest.mark.asyncio
async def test_get_effective_irt_state(db_session):
    """Test that get_effective_irt_state returns correct state."""
    # Ensure runtime config exists
    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db_session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={
                "profile": "V1_PRIMARY",
                "overrides": {MODULE_IRT: "v1"},
                "safe_mode": {"freeze_updates": False, "prefer_cache": True},
            },
        )
        db_session.add(config)
        await db_session.commit()
    
    # Set platform settings
    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db_session.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = PlatformSettings(id=1, data={})
        db_session.add(settings)
    
    if not settings.data:
        settings.data = {}
    
    settings.data["irt"] = {"active": True, "shadow": True}
    await db_session.commit()
    
    state = await get_effective_irt_state(db_session)
    
    assert "shadow_enabled" in state
    assert "active_allowed" in state
    assert "frozen" in state
    assert "override" in state
    assert state["shadow_enabled"] is True
    assert state["active_allowed"] is True
    assert state["frozen"] is False
    assert state["override"] == "v1"


@pytest.mark.asyncio
async def test_maybe_get_irt_estimates_respects_snapshot(db_session):
    """Test that maybe_get_irt_estimates_for_session respects session snapshot."""
    from app.learning_engine.router import maybe_get_irt_estimates_for_session
    
    # With IRT not active
    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db_session.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = PlatformSettings(id=1, data={})
        db_session.add(settings)
    
    if not settings.data:
        settings.data = {}
    
    settings.data["irt"] = {"active": False, "shadow": True}
    await db_session.commit()
    
    session_id = uuid4()
    user_id = uuid4()
    
    result = await maybe_get_irt_estimates_for_session(
        session_id,
        user_id,
        db_session,
        snapshot={"algo_profile_at_start": "V1_PRIMARY", "algo_overrides_at_start": {}},
    )
    
    assert result is None, "Should return None when IRT is not active"
    
    # With IRT active but v0 override in snapshot
    settings.data["irt"] = {"active": True, "shadow": True}
    await db_session.commit()
    
    result = await maybe_get_irt_estimates_for_session(
        session_id,
        user_id,
        db_session,
        snapshot={
            "algo_profile_at_start": "V1_PRIMARY",
            "algo_overrides_at_start": {MODULE_IRT: "v0"},
        },
    )
    
    assert result is None, "Should return None when snapshot has v0 override"
