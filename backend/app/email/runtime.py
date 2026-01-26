"""Email runtime configuration - single source of truth for email mode."""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.email import EmailMode, EmailRuntimeConfig, EmailSwitchEvent

logger = logging.getLogger(__name__)


@dataclass
class EmailRuntimeConfigData:
    """Email runtime configuration data."""

    requested_mode: EmailMode
    email_freeze: bool
    config_json: dict[str, Any]
    reason: str | None = None
    changed_by_user_id: str | None = None


def get_email_runtime_config_sync(db: Session) -> EmailRuntimeConfigData:
    """
    Get current email runtime configuration (singleton, sync version).

    Returns:
        EmailRuntimeConfigData with current mode and freeze state
    """
    config = db.query(EmailRuntimeConfig).first()

    if not config:
        # Create default if missing
        logger.warning("No email_runtime_config found, creating default")
        config = EmailRuntimeConfig(
            requested_mode=EmailMode.DISABLED.value,
            email_freeze=False,
            config_json={"requested_mode": "disabled", "email_freeze": False},
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    config_json = config.config_json or {}
    requested_mode_str = config.requested_mode or "disabled"
    try:
        requested_mode = EmailMode(requested_mode_str)
    except ValueError:
        requested_mode = EmailMode.DISABLED

    return EmailRuntimeConfigData(
        requested_mode=requested_mode,
        email_freeze=bool(config.email_freeze),
        config_json=config_json,
        reason=config.reason,
        changed_by_user_id=str(config.changed_by_user_id) if config.changed_by_user_id else None,
    )


async def get_email_runtime_config(db: AsyncSession) -> EmailRuntimeConfigData:
    """
    Get current email runtime configuration (singleton, async version).

    Returns:
        EmailRuntimeConfigData with current mode and freeze state
    """
    stmt = select(EmailRuntimeConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        # Create default if missing
        logger.warning("No email_runtime_config found, creating default")
        config = EmailRuntimeConfig(
            requested_mode=EmailMode.DISABLED.value,
            email_freeze=False,
            config_json={"requested_mode": "disabled", "email_freeze": False},
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    config_json = config.config_json or {}
    requested_mode_str = config.requested_mode or "disabled"
    try:
        requested_mode = EmailMode(requested_mode_str)
    except ValueError:
        requested_mode = EmailMode.DISABLED

    return EmailRuntimeConfigData(
        requested_mode=requested_mode,
        email_freeze=bool(config.email_freeze),
        config_json=config_json,
        reason=config.reason,
        changed_by_user_id=str(config.changed_by_user_id) if config.changed_by_user_id else None,
    )


def get_effective_email_mode(
    requested_mode: EmailMode,
    email_freeze: bool,
    provider_configured: bool,
) -> tuple[EmailMode, list[str], list[str]]:
    """
    Resolve effective email mode based on requested mode, freeze, and provider config.

    Returns:
        Tuple of (effective_mode, warnings, blocking_reasons)
    """
    warnings: list[str] = []
    blocking_reasons: list[str] = []

    if requested_mode == EmailMode.DISABLED:
        return EmailMode.DISABLED, warnings, blocking_reasons

    if requested_mode == EmailMode.SHADOW:
        return EmailMode.SHADOW, warnings, blocking_reasons

    # requested_mode == ACTIVE
    if email_freeze:
        warnings.append("Email freeze is enabled; emails will be shadow-logged")
        return EmailMode.SHADOW, warnings, blocking_reasons

    if not provider_configured:
        blocking_reasons.append("Email provider not configured")
        warnings.append("Provider not configured; emails will be shadow-logged")
        return EmailMode.SHADOW, warnings, blocking_reasons

    return EmailMode.ACTIVE, warnings, blocking_reasons
