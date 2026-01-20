"""Assemble learning engine information for API responses."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.constants import AlgoKey
from app.learning_engine.contracts import AlgorithmInfo, LearningEngineInfo
from app.learning_engine.registry import resolve_active


async def get_learning_engine_info(db: AsyncSession) -> LearningEngineInfo:
    """
    Assemble comprehensive learning engine information.
    
    Args:
        db: Database session
    
    Returns:
        LearningEngineInfo with all algorithm states
    """
    algorithms = []
    
    for algo_key in AlgoKey:
        version, params = await resolve_active(db, algo_key.value)
        
        if version and params:
            algorithms.append(
                AlgorithmInfo(
                    algo_key=version.algo_key,
                    active_version=version.version,
                    status=version.status,
                    active_params=params.params_json,
                    updated_at=version.updated_at,
                )
            )
    
    return LearningEngineInfo(algorithms=algorithms)
