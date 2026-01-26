"""Algorithm runtime configuration - single source of truth for v0/v1 routing.

This module provides the authoritative helpers for determining which algorithm
version to use (v0 or v1) based on the runtime configuration.
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.algo_runtime import AlgoRuntimeConfig, AlgoRuntimeProfile

logger = logging.getLogger(__name__)

# Module names
MODULE_MASTERY = "mastery"
MODULE_REVISION = "revision"
MODULE_DIFFICULTY = "difficulty"
MODULE_ADAPTIVE = "adaptive"
MODULE_MISTAKES = "mistakes"
MODULE_IRT = "irt"
MODULE_RANK = "rank"
MODULE_GRAPH_REVISION = "graph_revision"

ALL_MODULES = [
    MODULE_MASTERY,
    MODULE_REVISION,
    MODULE_DIFFICULTY,
    MODULE_ADAPTIVE,
    MODULE_MISTAKES,
    MODULE_IRT,
    MODULE_RANK,
    MODULE_GRAPH_REVISION,
]


@dataclass
class AlgoRuntimeConfigData:
    """Runtime configuration data."""

    active_profile: AlgoRuntimeProfile
    active_since: str
    config_json: dict[str, Any]
    overrides: dict[str, str]  # module_name -> "v0" | "v1"
    safe_mode: dict[str, bool]  # freeze_updates, prefer_cache


async def get_algo_runtime_config(db: AsyncSession) -> AlgoRuntimeConfigData:
    """
    Get current algorithm runtime configuration (singleton).

    Returns:
        AlgoRuntimeConfigData with current profile and overrides
    """
    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        # Create default if missing
        logger.warning("No algo_runtime_config found, creating default")
        config = AlgoRuntimeConfig(
            active_profile=AlgoRuntimeProfile.V1_PRIMARY,
            config_json={
                "profile": "V1_PRIMARY",
                "overrides": {},
                "safe_mode": {"freeze_updates": False, "prefer_cache": True},
                "search_engine_mode": "postgres",  # Default to postgres
            },
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    config_json = config.config_json or {}
    overrides = config_json.get("overrides", {})
    safe_mode = config_json.get("safe_mode", {"freeze_updates": False, "prefer_cache": True})
    
    # Ensure search_engine_mode has a default
    if "search_engine_mode" not in config_json:
        config_json["search_engine_mode"] = "postgres"
        config.config_json = config_json
        await db.commit()
        await db.refresh(config)

    return AlgoRuntimeConfigData(
        active_profile=config.active_profile,
        active_since=config.active_since.isoformat() if config.active_since else "",
        config_json=config_json,
        overrides=overrides,
        safe_mode=safe_mode,
    )


async def get_algo_version(db: AsyncSession, module_name: str) -> str:
    """
    Get algorithm version for a specific module.

    Respects:
    1. Module-specific override (if set)
    2. Profile default (V1_PRIMARY -> v1, V0_FALLBACK -> v0)

    Args:
        db: Database session
        module_name: One of MODULE_MASTERY, MODULE_REVISION, etc.

    Returns:
        "v0" or "v1"
    """
    config = await get_algo_runtime_config(db)

    # Check for module-specific override
    if module_name in config.overrides:
        override = config.overrides[module_name]
        if override in ("v0", "v1"):
            return override
        logger.warning(f"Invalid override for {module_name}: {override}, using profile default")

    # Use profile default
    if config.active_profile == AlgoRuntimeProfile.V1_PRIMARY:
        return "v1"
    elif config.active_profile == AlgoRuntimeProfile.V0_FALLBACK:
        return "v0"
    else:
        logger.warning(f"Unknown profile: {config.active_profile}, defaulting to v1")
        return "v1"


async def is_safe_mode_freeze_updates(db: AsyncSession) -> bool:
    """
    Check if safe mode freeze_updates is enabled.

    When enabled, no state mutations should occur (read-only decisions).

    Returns:
        True if freeze_updates is enabled
    """
    config = await get_algo_runtime_config(db)
    return config.safe_mode.get("freeze_updates", False)


async def get_bridge_config(
    db: AsyncSession, policy_version: str = "ALGO_BRIDGE_SPEC_v1"
) -> dict[str, Any] | None:
    """
    Get bridge configuration for a policy version.

    Args:
        db: Database session
        policy_version: Policy version string (default: "ALGO_BRIDGE_SPEC_v1")

    Returns:
        Bridge config dict or None if not found
    """
    from app.models.algo_runtime import AlgoBridgeConfig
    from sqlalchemy import select

    stmt = select(AlgoBridgeConfig).where(AlgoBridgeConfig.policy_version == policy_version)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        return {
            "policy_version": config.policy_version,
            "config_json": config.config_json or {},
        }
    return None


async def is_irt_shadow_enabled(db: AsyncSession) -> bool:
    """
    Check if IRT shadow mode is enabled.

    Shadow mode allows calibration runs but no student-facing decisions.

    Returns:
        True if shadow mode is enabled
    """
    from app.models.platform_settings import PlatformSettings
    from sqlalchemy import select

    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings and settings.data and "irt" in settings.data:
        return settings.data["irt"].get("shadow", True)  # Default True
    return True  # Default enabled


async def is_irt_active_allowed(db: AsyncSession, runtime_cfg: AlgoRuntimeConfigData | None = None) -> bool:
    """
    Check if IRT is allowed to be used for student-facing decisions.

    Requires:
    1. IRT module override allows it (not "v0")
    2. FEATURE_IRT_ACTIVE flag is True (in platform_settings)
    3. Not in freeze_updates mode

    Args:
        db: Database session
        runtime_cfg: Optional runtime config (to avoid double fetch)

    Returns:
        True if IRT can be used for decisions
    """
    # Get runtime config if not provided
    if runtime_cfg is None:
        runtime_cfg = await get_algo_runtime_config(db)

    # Check module override
    irt_override = runtime_cfg.overrides.get(MODULE_IRT, None)
    if irt_override == "v0":
        return False  # Explicitly disabled

    # Check freeze mode
    if runtime_cfg.safe_mode.get("freeze_updates", False):
        return False  # Freeze mode blocks all state writes

    # Check FEATURE_IRT_ACTIVE flag
    from app.models.platform_settings import PlatformSettings
    from sqlalchemy import select

    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings and settings.data and "irt" in settings.data:
        return settings.data["irt"].get("active", False)  # Default False

    return False  # Default disabled


async def get_effective_irt_state(db: AsyncSession) -> dict[str, Any]:
    """
    Get effective IRT state (shadow, active, frozen).

    Returns:
        Dictionary with:
        - shadow_enabled: bool
        - active_allowed: bool
        - frozen: bool
        - override: str | None ("v0" | "v1" | None)
    """
    runtime_cfg = await get_algo_runtime_config(db)
    irt_override = runtime_cfg.overrides.get(MODULE_IRT, None)

    return {
        "shadow_enabled": await is_irt_shadow_enabled(db),
        "active_allowed": await is_irt_active_allowed(db, runtime_cfg),
        "frozen": runtime_cfg.safe_mode.get("freeze_updates", False),
        "override": irt_override,
    }


async def get_rank_mode(
    db: AsyncSession,
    runtime_cfg: AlgoRuntimeConfigData | None = None,
    snapshot_cfg: dict[str, Any] | None = None,
) -> str:
    """
    Get rank mode for a request (respects session snapshot).

    Args:
        db: Database session
        runtime_cfg: Optional runtime config (to avoid double fetch)
        snapshot_cfg: Optional session snapshot config

    Returns:
        "v0" | "shadow" | "v1"
    """
    if snapshot_cfg and MODULE_RANK in snapshot_cfg:
        return snapshot_cfg[MODULE_RANK]

    if runtime_cfg is None:
        runtime_cfg = await get_algo_runtime_config(db)

    rank_override = runtime_cfg.overrides.get(MODULE_RANK, None)
    if rank_override in ("v0", "shadow", "v1"):
        return rank_override

    # Default: shadow (allows computation but not student-facing usage)
    return "shadow"


async def is_rank_enabled_for_admin(db: AsyncSession, runtime_cfg: AlgoRuntimeConfigData | None = None) -> bool:
    """
    Check if rank is enabled for admin operations (shadow or v1).

    Args:
        db: Database session
        runtime_cfg: Optional runtime config

    Returns:
        True if rank mode is shadow or v1
    """
    mode = await get_rank_mode(db, runtime_cfg)
    return mode in ("shadow", "v1")


async def is_rank_enabled_for_student(
    db: AsyncSession,
    runtime_cfg: AlgoRuntimeConfigData | None = None,
    snapshot_cfg: dict[str, Any] | None = None,
) -> bool:
    """
    Check if rank is enabled for student-facing operations (v1 only + feature flag).

    Args:
        db: Database session
        runtime_cfg: Optional runtime config
        snapshot_cfg: Optional session snapshot config

    Returns:
        True if rank mode is v1 AND student feature flag is enabled
    """
    mode = await get_rank_mode(db, runtime_cfg, snapshot_cfg)
    if mode != "v1":
        return False

    # Check student feature flag (default False)
    from app.models.platform_settings import PlatformSettings
    from sqlalchemy import select

    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings and settings.data and "rank" in settings.data:
        return settings.data["rank"].get("student_enabled", False)

    return False  # Default disabled for students


async def get_graph_revision_mode(
    db: AsyncSession,
    runtime_cfg: AlgoRuntimeConfigData | None = None,
    snapshot_cfg: dict[str, Any] | None = None,
) -> str:
    """
    Get graph_revision mode for a request (respects session snapshot).

    Args:
        db: Database session
        runtime_cfg: Optional runtime config (to avoid double fetch)
        snapshot_cfg: Optional session snapshot config

    Returns:
        "v0" | "shadow" | "v1"
    """
    if snapshot_cfg and MODULE_GRAPH_REVISION in snapshot_cfg:
        return snapshot_cfg[MODULE_GRAPH_REVISION]

    if runtime_cfg is None:
        runtime_cfg = await get_algo_runtime_config(db)

    graph_revision_override = runtime_cfg.overrides.get(MODULE_GRAPH_REVISION, None)
    if graph_revision_override in ("v0", "shadow", "v1"):
        return graph_revision_override

    # Default: shadow (allows computation but not student-facing usage)
    return "shadow"


async def is_graph_revision_active_allowed(
    db: AsyncSession,
    runtime_cfg: AlgoRuntimeConfigData | None = None,
    snapshot_cfg: dict[str, Any] | None = None,
) -> bool:
    """
    Check if graph_revision is allowed to influence student-facing revision plans.

    Requires:
    1. Mode is "v1" (not "v0" or "shadow")
    2. Feature flag enabled (platform_settings.graph_revision.active)
    3. Not in freeze_updates mode

    Args:
        db: Database session
        runtime_cfg: Optional runtime config
        snapshot_cfg: Optional session snapshot config

    Returns:
        True if graph_revision can influence student plans
    """
    mode = await get_graph_revision_mode(db, runtime_cfg, snapshot_cfg)
    if mode != "v1":
        return False

    # Check freeze mode
    if runtime_cfg is None:
        runtime_cfg = await get_algo_runtime_config(db)
    if runtime_cfg.safe_mode.get("freeze_updates", False):
        return False

    # Check feature flag (default False)
    from app.models.platform_settings import PlatformSettings
    from sqlalchemy import select

    stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings and settings.data and "graph_revision" in settings.data:
        return settings.data["graph_revision"].get("active", False)

    return False  # Default disabled


async def get_session_algo_config(
    db: AsyncSession, session_profile: str | None, session_overrides: dict[str, Any] | None
) -> dict[str, str]:
    """
    Get algorithm version config for a session.

    Uses session snapshot if available, otherwise current runtime config.

    Args:
        db: Database session
        session_profile: Profile captured at session start (if any)
        session_overrides: Overrides captured at session start (if any)

    Returns:
        Dictionary mapping module_name -> "v0" | "v1"
    """
    # If session has snapshot, use it (ensures continuity)
    if session_profile:
        profile_map = {
            "V1_PRIMARY": "v1",
            "V0_FALLBACK": "v0",
        }
        base_version = profile_map.get(session_profile, "v1")

        result = {}
        for module in ALL_MODULES:
            # Check session override first
            if session_overrides and module in session_overrides:
                override = session_overrides[module]
                if override in ("v0", "v1"):
                    result[module] = override
                else:
                    result[module] = base_version
            else:
                result[module] = base_version

        return result

    # No session snapshot, use current runtime config
    result = {}
    for module in ALL_MODULES:
        result[module] = await get_algo_version(db, module)
    return result
