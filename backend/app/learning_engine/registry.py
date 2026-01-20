"""Registry functions for resolving active algorithm versions and parameters."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.constants import AlgoStatus
from app.models.learning import AlgoParams, AlgoVersion

logger = logging.getLogger(__name__)


async def get_active_algo_version(
    db: AsyncSession, algo_key: str
) -> AlgoVersion | None:
    """
    Get the active version for an algorithm.
    
    Args:
        db: Database session
        algo_key: Algorithm key (e.g., "mastery")
    
    Returns:
        Active AlgoVersion or None if not found
    """
    stmt = select(AlgoVersion).where(
        AlgoVersion.algo_key == algo_key,
        AlgoVersion.status == AlgoStatus.ACTIVE,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_active_params(
    db: AsyncSession, algo_version_id: UUID
) -> AlgoParams | None:
    """
    Get the active parameters for an algorithm version.
    
    Args:
        db: Database session
        algo_version_id: Algorithm version ID
    
    Returns:
        Active AlgoParams or None if not found
    """
    stmt = select(AlgoParams).where(
        AlgoParams.algo_version_id == algo_version_id,
        AlgoParams.is_active == True,  # noqa: E712
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def resolve_active(
    db: AsyncSession, algo_key: str
) -> tuple[AlgoVersion | None, AlgoParams | None]:
    """
    Resolve the active version and parameters for an algorithm.
    
    Args:
        db: Database session
        algo_key: Algorithm key (e.g., "mastery")
    
    Returns:
        Tuple of (AlgoVersion, AlgoParams) or (None, None) if not found
    """
    version = await get_active_algo_version(db, algo_key)
    if not version:
        logger.warning(f"No active version found for algorithm: {algo_key}")
        return None, None
    
    params = await get_active_params(db, version.id)
    if not params:
        logger.warning(
            f"No active params found for algorithm version: {algo_key} v{version.version}"
        )
        return version, None
    
    return version, params


async def activate_algo_version(
    db: AsyncSession, algo_key: str, version: str
) -> AlgoVersion | None:
    """
    Activate a specific version of an algorithm.
    
    Deactivates all other versions of the same algorithm.
    
    Args:
        db: Database session
        algo_key: Algorithm key
        version: Version string to activate
    
    Returns:
        Activated AlgoVersion or None if not found
    """
    # Find the target version
    stmt = select(AlgoVersion).where(
        AlgoVersion.algo_key == algo_key,
        AlgoVersion.version == version,
    )
    result = await db.execute(stmt)
    target_version = result.scalar_one_or_none()
    
    if not target_version:
        return None
    
    # Deactivate all other versions of this algorithm
    stmt = select(AlgoVersion).where(
        AlgoVersion.algo_key == algo_key,
        AlgoVersion.id != target_version.id,
        AlgoVersion.status == AlgoStatus.ACTIVE,
    )
    result = await db.execute(stmt)
    other_versions = result.scalars().all()
    
    for other in other_versions:
        other.status = AlgoStatus.DEPRECATED
    
    # Activate target
    target_version.status = AlgoStatus.ACTIVE
    
    await db.commit()
    await db.refresh(target_version)
    
    return target_version


async def activate_params(
    db: AsyncSession, params_id: UUID
) -> AlgoParams | None:
    """
    Activate a specific parameter set.
    
    Deactivates all other parameter sets for the same algorithm version.
    
    Args:
        db: Database session
        params_id: Parameter set ID to activate
    
    Returns:
        Activated AlgoParams or None if not found
    """
    # Find the target params
    stmt = select(AlgoParams).where(AlgoParams.id == params_id)
    result = await db.execute(stmt)
    target_params = result.scalar_one_or_none()
    
    if not target_params:
        return None
    
    # Deactivate all other params for this version
    stmt = select(AlgoParams).where(
        AlgoParams.algo_version_id == target_params.algo_version_id,
        AlgoParams.id != params_id,
        AlgoParams.is_active == True,  # noqa: E712
    )
    result = await db.execute(stmt)
    other_params = result.scalars().all()
    
    for other in other_params:
        other.is_active = False
    
    # Activate target
    target_params.is_active = True
    
    await db.commit()
    await db.refresh(target_params)
    
    return target_params
