"""Difficulty assessment algorithm v0 (stub)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.contracts import DifficultyInput, DifficultyOutput


async def compute_difficulty_v0(
    db: AsyncSession,
    input_data: DifficultyInput,
    params: dict,
) -> DifficultyOutput:
    """
    Compute difficulty score for a question (v0 stub).
    
    Args:
        db: Database session
        input_data: Difficulty assessment input
        params: Algorithm parameters
    
    Returns:
        Difficulty score output
    
    Raises:
        NotImplementedError: Algorithm not yet implemented
    """
    raise NotImplementedError("Difficulty v0 algorithm not yet implemented (Task 103+)")
