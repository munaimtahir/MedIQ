"""Rank configuration helpers."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rank import RankConfig


async def get_rank_config(
    db: AsyncSession, policy_version: str = "rank_v1"
) -> dict[str, Any] | None:
    """
    Get rank configuration for a policy version.

    Args:
        db: Database session
        policy_version: Policy version string (default: "rank_v1")

    Returns:
        Rank config dict or None if not found
    """
    stmt = select(RankConfig).where(RankConfig.policy_version == policy_version)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        return {
            "policy_version": config.policy_version,
            "config_json": config.config_json or {},
        }
    return None
