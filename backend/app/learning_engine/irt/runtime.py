"""IRT runtime helpers - check activation status and scope.

These helpers provide the authoritative source for IRT activation state.
They read from platform_settings (for runtime changes) with fallback to config.py.
"""

import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.platform_settings import PlatformSettings

logger = logging.getLogger(__name__)

# Type aliases
IrtScope = Literal["none", "shadow_only", "selection_only", "scoring_only", "selection_and_scoring"]
IrtModel = Literal["IRT_2PL", "IRT_3PL"]


async def is_irt_active(db: AsyncSession) -> bool:
    """
    Check if IRT is active for student-facing decisions.

    Returns:
        True if FEATURE_IRT_ACTIVE is enabled, False otherwise.
    """
    # Check platform_settings first (runtime override)
    platform_settings = await _get_platform_settings(db)
    if platform_settings and "irt" in platform_settings.get("data", {}):
        irt_config = platform_settings["data"]["irt"]
        if "active" in irt_config:
            return bool(irt_config["active"])

    # Fallback to config.py
    return getattr(settings, "FEATURE_IRT_ACTIVE", False)


async def get_irt_scope(db: AsyncSession) -> IrtScope:
    """
    Get IRT activation scope.

    Returns:
        One of: "none", "shadow_only", "selection_only", "scoring_only", "selection_and_scoring"
    """
    # If not active, scope is always "none"
    if not await is_irt_active(db):
        return "none"

    # Check platform_settings first
    platform_settings = await _get_platform_settings(db)
    if platform_settings and "irt" in platform_settings.get("data", {}):
        irt_config = platform_settings["data"]["irt"]
        if "scope" in irt_config:
            scope = irt_config["scope"]
            if scope in ("none", "shadow_only", "selection_only", "scoring_only", "selection_and_scoring"):
                return scope

    # Fallback to config.py
    scope = getattr(settings, "FEATURE_IRT_SCOPE", "none")
    if scope not in ("none", "shadow_only", "selection_only", "scoring_only", "selection_and_scoring"):
        logger.warning(f"Invalid IRT scope in config: {scope}, defaulting to 'none'")
        return "none"
    return scope


async def get_irt_model(db: AsyncSession) -> IrtModel:
    """
    Get IRT model type to use.

    Returns:
        "IRT_2PL" or "IRT_3PL"
    """
    # Check platform_settings first
    platform_settings = await _get_platform_settings(db)
    if platform_settings and "irt" in platform_settings.get("data", {}):
        irt_config = platform_settings["data"]["irt"]
        if "model" in irt_config:
            model = irt_config["model"]
            if model in ("IRT_2PL", "IRT_3PL"):
                return model

    # Fallback to config.py
    model = getattr(settings, "FEATURE_IRT_MODEL", "IRT_2PL")
    if model not in ("IRT_2PL", "IRT_3PL"):
        logger.warning(f"Invalid IRT model in config: {model}, defaulting to 'IRT_2PL'")
        return "IRT_2PL"
    return model


async def is_irt_shadow_enabled(db: AsyncSession) -> bool:
    """
    Check if IRT shadow mode is enabled (allows calibration + admin view).

    Returns:
        True if FEATURE_IRT_SHADOW is enabled, False otherwise.
    """
    # Check platform_settings first
    platform_settings = await _get_platform_settings(db)
    if platform_settings and "irt" in platform_settings.get("data", {}):
        irt_config = platform_settings["data"]["irt"]
        if "shadow" in irt_config:
            return bool(irt_config["shadow"])

    # Fallback to config.py
    return getattr(settings, "FEATURE_IRT_SHADOW", True)


async def _get_platform_settings(db: AsyncSession) -> dict | None:
    """Get platform settings from database."""
    try:
        stmt = select(PlatformSettings).where(PlatformSettings.id == 1)
        result = await db.execute(stmt)
        settings_obj = result.scalar_one_or_none()
        if settings_obj:
            return {"data": settings_obj.data or {}}
    except Exception as e:
        logger.warning(f"Failed to read platform_settings: {e}")
    return None
