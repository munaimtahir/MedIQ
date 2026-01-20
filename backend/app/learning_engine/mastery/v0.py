"""Mastery tracking algorithm v0."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.contracts import MasteryInput, MasteryOutput
from app.learning_engine.mastery.service import recompute_mastery_v0_for_user


async def compute_mastery_v0(
    db: AsyncSession,
    input_data: MasteryInput,
    params: dict,
) -> MasteryOutput:
    """
    Compute mastery scores for a user using recency-weighted accuracy.

    This implementation:
    - Uses only submitted/expired sessions
    - Weights recent attempts more heavily (recency buckets)
    - Optionally adjusts for question difficulty
    - Requires minimum attempts for confidence

    Args:
        db: Database session
        input_data: Mastery computation input
        params: Algorithm parameters

    Returns:
        Mastery scores output with theme-level mastery
    """
    theme_ids = None
    if input_data.block_id or input_data.theme_id:
        # If specific theme requested, filter
        theme_ids = [input_data.theme_id] if input_data.theme_id else None

    result = await recompute_mastery_v0_for_user(
        db,
        user_id=input_data.user_id,
        theme_ids=theme_ids,
    )

    # Return in contract format
    return MasteryOutput(
        user_id=input_data.user_id,
        mastery_scores=result,
        computed_at=datetime.utcnow(),
    )
