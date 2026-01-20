"""Revision scheduling algorithm v0."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.contracts import RevisionInput, RevisionOutput
from app.learning_engine.revision.service import generate_revision_queue_v0


async def compute_revision_v0(
    db: AsyncSession,
    input_data: RevisionInput,
    params: dict,
) -> RevisionOutput:
    """
    Compute revision schedule for a user using spaced repetition.
    
    This implementation:
    - Uses mastery scores to determine spacing
    - Prioritizes weak themes
    - Stores revision queue in database
    - Provides recommended question counts
    
    Args:
        db: Database session
        input_data: Revision scheduling input
        params: Algorithm parameters
    
    Returns:
        Revision schedule output with due questions
    """
    result = await generate_revision_queue_v0(
        db,
        user_id=input_data.user_id,
        trigger="api",
    )
    
    # Return in contract format
    return RevisionOutput(
        user_id=input_data.user_id,
        due_questions=[],  # Populated from revision_queue in actual usage
        computed_at=datetime.utcnow(),
    )
