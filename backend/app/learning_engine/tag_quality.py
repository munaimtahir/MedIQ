"""Tag quality debt logging for BKT Q-matrix hygiene."""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question_cms import Question
from app.models.tag_quality import TagQualityDebtLog

logger = logging.getLogger(__name__)


async def log_tag_debt(
    db: AsyncSession,
    question_id: UUID | None,
    theme_id: int | None,
    reason: str,
    count: int = 1,
) -> None:
    """
    Log tag quality debt.

    Args:
        db: Database session
        question_id: Question ID (if applicable)
        theme_id: Theme ID (if applicable)
        reason: Reason code (MISSING_CONCEPT, MULTIPLE_CONCEPTS, INCONSISTENT_TAGS)
        count: Count (for aggregation)
    """
    debt_log = TagQualityDebtLog(
        question_id=question_id,
        theme_id=theme_id,
        reason=reason,
        count=count,
    )

    db.add(debt_log)
    await db.commit()


async def get_concept_id_with_fallback(
    db: AsyncSession,
    question_id: UUID,
    theme_id: int | None = None,
) -> tuple[UUID, bool]:
    """
    Get concept_id for a question with fallback.

    If question has no concept_id:
    - Use theme_id as pseudo-concept: "THEME::<theme_id>"
    - Mark as tag_debt=true
    - Log to tag_quality_debt_log

    Args:
        db: Database session
        question_id: Question ID
        theme_id: Theme ID (for fallback)

    Returns:
        Tuple of (concept_id, tag_debt_flag)
    """
    question = await db.get(Question, question_id)
    if not question:
        logger.warning(f"Question not found: {question_id}")
        # Return a default concept_id
        return UUID(int=0), True

    # Check if question has concept_id
    if question.concept_id:
        return UUID(int=question.concept_id), False

    # Fallback: use theme_id as pseudo-concept
    if theme_id:
        # Create pseudo-concept ID from theme_id
        # Format: use a hash of "THEME::<theme_id>" to generate UUID
        import hashlib

        pseudo_concept_str = f"THEME::{theme_id}"
        hash_bytes = hashlib.md5(pseudo_concept_str.encode()).digest()[:16]
        pseudo_concept_id = UUID(bytes=hash_bytes)

        # Log debt
        await log_tag_debt(db, question_id, theme_id, "MISSING_CONCEPT", count=1)

        return pseudo_concept_id, True

    # Last resort: use question_id itself
    logger.warning(f"No concept_id or theme_id for question {question_id}, using question_id as concept")
    await log_tag_debt(db, question_id, None, "MISSING_CONCEPT", count=1)

    return question_id, True
