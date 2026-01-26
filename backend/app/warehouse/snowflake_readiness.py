"""Snowflake readiness checks (hard-disabled by default).

This module checks if Snowflake is ready for use, but is hard-disabled
by default to prevent accidental connections.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)


class SnowflakeReadinessStatus:
    """Snowflake readiness status."""

    def __init__(
        self,
        ready: bool,
        reason: str | None = None,
        checks: dict[str, Any] | None = None,
    ):
        self.ready = ready
        self.reason = reason
        self.checks = checks or {}


def check_snowflake_readiness(db: Session) -> SnowflakeReadinessStatus:
    """
    Check if Snowflake is ready for use.

    Rules:
    - If SNOWFLAKE_ENABLED=false: ready=false, reason="snowflake_disabled"
    - If warehouse_mode != "active": ready=false, reason="warehouse_not_active"
    - If FEATURE_ALLOW_SNOWFLAKE_CONNECT=false: ready=false, reason="snowflake_connect_disabled"
    - Only if all above pass: attempt minimal connectivity check (future)

    Returns:
        SnowflakeReadinessStatus
    """
    checks: dict[str, Any] = {}

    # Check 1: SNOWFLAKE_ENABLED
    if not settings.SNOWFLAKE_ENABLED:
        return SnowflakeReadinessStatus(
            ready=False,
            reason="snowflake_disabled",
            checks={"snowflake_enabled": False},
        )
    checks["snowflake_enabled"] = True

    # Check 2: Warehouse mode must be active
    from app.warehouse.exporter import _get_warehouse_mode

    warehouse_mode, warehouse_freeze = _get_warehouse_mode(db)
    if warehouse_mode != "active":
        return SnowflakeReadinessStatus(
            ready=False,
            reason="warehouse_not_active",
            checks={
                "snowflake_enabled": True,
                "warehouse_mode": warehouse_mode,
            },
        )
    checks["warehouse_mode"] = warehouse_mode
    checks["warehouse_freeze"] = warehouse_freeze

    # Check 3: Feature flag for allowing connections
    if not settings.FEATURE_ALLOW_SNOWFLAKE_CONNECT:
        return SnowflakeReadinessStatus(
            ready=False,
            reason="snowflake_connect_disabled",
            checks={
                "snowflake_enabled": True,
                "warehouse_mode": warehouse_mode,
                "feature_allow_snowflake_connect": False,
            },
        )
    checks["feature_allow_snowflake_connect"] = True

    # Check 4: Required environment variables
    required_vars = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
    ]
    missing_vars = []
    for var in required_vars:
        value = getattr(settings, var, None)
        if not value:
            missing_vars.append(var)
        else:
            checks[var.lower()] = "***"  # Masked for security

    if missing_vars:
        return SnowflakeReadinessStatus(
            ready=False,
            reason="missing_snowflake_config",
            checks={
                **checks,
                "missing_vars": missing_vars,
            },
        )

    # All checks passed - but we don't actually connect yet
    # Future: Add actual connectivity check here when ready
    # For now, return ready=True but note that connection is not attempted
    checks["connectivity_check"] = "not_attempted"
    checks["note"] = "Connection check deferred - not implemented yet"

    return SnowflakeReadinessStatus(
        ready=True,
        reason=None,
        checks=checks,
    )
