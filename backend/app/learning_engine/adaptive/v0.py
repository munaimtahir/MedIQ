"""Adaptive Selection v0 - Rule-based question selection."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_difficulty import QuestionDifficulty
from app.models.learning_mastery import UserThemeMastery
from app.models.learning_revision import RevisionQueue
from app.models.question_cms import Question
from app.models.session import SessionAnswer, SessionQuestion
from app.models.syllabus import Block, Theme

logger = logging.getLogger(__name__)


def deterministic_hash(user_id: UUID, question_id: UUID, seed: str) -> int:
    """Create a deterministic hash for tie-breaking."""
    combined = f"{user_id}{question_id}{seed}"
    return int(hashlib.sha256(combined.encode()).hexdigest()[:8], 16)


async def select_questions_v0(
    db: AsyncSession,
    user_id: UUID,
    *,
    year: int,
    block_ids: list[UUID],
    theme_ids: list[UUID] | None,
    count: int,
    mode: str,
    params: dict[str, Any],
) -> list[UUID]:
    """
    Select optimal questions for a user using rule-based adaptive logic.

    Selection prioritizes:
    1. Themes due for revision (from revision_queue)
    2. Weakest themes by mastery
    3. Appropriate difficulty matching mastery
    4. Anti-repeat (exclude recently seen questions)
    5. Diversity across themes

    Args:
        db: Database session
        user_id: User ID
        year: Academic year
        block_ids: Block IDs to select from
        theme_ids: Optional theme filter (if None, use all themes in blocks)
        count: Number of questions to select
        mode: "tutor" or "exam"
        params: Algorithm parameters

    Returns:
        List of question IDs (deterministically ordered)
    """
    # Extract params
    anti_repeat_days = params.get("anti_repeat_days", 14)
    theme_mix = params.get("theme_mix", {"weak": 0.5, "medium": 0.3, "mixed": 0.2})
    difficulty_targets = params.get(
        "difficulty_targets",
        {
            "weak": [900, 1050],
            "medium": [1000, 1150],
            "strong": [1050, 1250],
        },
    )
    difficulty_bucket_limits = params.get(
        "difficulty_bucket_limits",
        {
            "easy": [0, 950],
            "medium": [950, 1100],
            "hard": [1100, 9999],
        },
    )
    difficulty_mix = params.get(
        "difficulty_mix",
        {
            "easy": 0.2,
            "medium": 0.6,
            "hard": 0.2,
        },
    )
    fit_weights = params.get(
        "fit_weights",
        {
            "mastery_inverse": 0.6,
            "difficulty_distance": 0.3,
            "freshness": 0.1,
        },
    )

    # Step 1: Determine target themes
    target_themes = []

    # Priority 1: Themes due for revision
    revision_stmt = select(RevisionQueue).where(
        and_(
            RevisionQueue.user_id == user_id,
            RevisionQueue.due_date <= datetime.utcnow().date(),
        )
    )
    revision_result = await db.execute(revision_stmt)
    revision_items = revision_result.scalars().all()

    if revision_items:
        target_themes.extend([item.theme_id for item in revision_items])
        logger.info(f"Found {len(revision_items)} themes due for revision")

    # Priority 2: Weakest themes by mastery
    mastery_stmt = (
        select(UserThemeMastery)
        .where(
            and_(
                UserThemeMastery.user_id == user_id,
                UserThemeMastery.year == year,
                UserThemeMastery.block_id.in_(block_ids),
            )
        )
        .order_by(UserThemeMastery.mastery_score.asc())
        .limit(10)
    )
    if theme_ids:
        mastery_stmt = mastery_stmt.where(UserThemeMastery.theme_id.in_(theme_ids))

    mastery_result = await db.execute(mastery_stmt)
    mastery_records = mastery_result.scalars().all()

    mastery_map = {m.theme_id: float(m.mastery_score) for m in mastery_records}

    # Add weak themes not already in target
    for mastery in mastery_records:
        if mastery.theme_id not in target_themes:
            target_themes.append(mastery.theme_id)

    # If still no themes, get all themes from blocks
    if not target_themes:
        themes_stmt = select(Theme).where(
            and_(
                Theme.block_id.in_(block_ids),
                Theme.year == year,
            )
        )
        if theme_ids:
            themes_stmt = themes_stmt.where(Theme.id.in_(theme_ids))

        themes_result = await db.execute(themes_stmt)
        target_themes = [t.id for t in themes_result.scalars().all()]

    # Ensure at least 2 themes for diversity (if available)
    target_themes = target_themes[: max(2, len(target_themes))]

    if not target_themes:
        logger.warning("No themes available for selection")
        return []

    logger.info(f"Target themes: {len(target_themes)}")

    # Step 2: Build candidate question pool
    # Get recently attempted questions
    cutoff_date = datetime.utcnow() - timedelta(days=anti_repeat_days)
    recent_stmt = (
        select(SessionAnswer.question_id.distinct())
        .join(SessionQuestion, SessionAnswer.session_id == SessionQuestion.session_id)
        .where(
            and_(
                SessionAnswer.user_id == user_id,
                SessionQuestion.created_at >= cutoff_date,
            )
        )
    )
    recent_result = await db.execute(recent_stmt)
    recent_question_ids = set(r[0] for r in recent_result.all())

    logger.info(f"Excluding {len(recent_question_ids)} recent questions")

    # Query candidate questions
    questions_stmt = (
        select(Question, QuestionDifficulty)
        .outerjoin(QuestionDifficulty, Question.id == QuestionDifficulty.question_id)
        .where(
            and_(
                Question.status == "PUBLISHED",
                Question.year == year,
                Question.block_id.in_(block_ids),
                Question.theme_id.in_(target_themes),
            )
        )
    )

    # Exclude recent questions
    if recent_question_ids:
        questions_stmt = questions_stmt.where(Question.id.notin_(recent_question_ids))

    questions_result = await db.execute(questions_stmt)
    candidates = questions_result.all()

    if not candidates:
        logger.warning("No candidate questions found, relaxing anti-repeat filter")
        # Fallback: relax anti-repeat filter
        questions_stmt = (
            select(Question, QuestionDifficulty)
            .outerjoin(QuestionDifficulty, Question.id == QuestionDifficulty.question_id)
            .where(
                and_(
                    Question.status == "PUBLISHED",
                    Question.year == year,
                    Question.block_id.in_(block_ids),
                    Question.theme_id.in_(target_themes),
                )
            )
        )
        questions_result = await db.execute(questions_stmt)
        candidates = questions_result.all()

    if not candidates:
        logger.warning("No questions available for selection")
        return []

    logger.info(f"Found {len(candidates)} candidate questions")

    # Step 3: Compute fit scores
    scored_candidates = []
    today_seed = datetime.utcnow().date().isoformat()

    for question, difficulty in candidates:
        theme_id = question.theme_id
        mastery_score = mastery_map.get(theme_id, 0.5)  # Default to medium if no mastery

        # Determine mastery band
        if mastery_score < 0.4:
            mastery_band = "weak"
        elif mastery_score < 0.7:
            mastery_band = "medium"
        else:
            mastery_band = "strong"

        # Get target difficulty range
        target_range = difficulty_targets.get(mastery_band, [1000, 1150])
        target_mid = (target_range[0] + target_range[1]) / 2

        # Get question rating
        question_rating = float(difficulty.rating) if difficulty else 1000.0

        # Compute difficulty distance (normalized)
        difficulty_distance = abs(question_rating - target_mid)
        max_distance = 500.0  # Normalizing factor
        normalized_distance = min(difficulty_distance / max_distance, 1.0)

        # Compute fit score
        fit_score = (
            fit_weights["mastery_inverse"] * (1.0 - mastery_score)
            + fit_weights["difficulty_distance"] * (1.0 - normalized_distance)
            + fit_weights["freshness"] * 1.0  # All candidates are "fresh" after anti-repeat filter
        )

        # Deterministic tie-breaker
        tie_breaker = deterministic_hash(user_id, question.id, today_seed)

        scored_candidates.append(
            {
                "question_id": question.id,
                "theme_id": theme_id,
                "rating": question_rating,
                "mastery_score": mastery_score,
                "mastery_band": mastery_band,
                "fit_score": fit_score,
                "tie_breaker": tie_breaker,
            }
        )

    # Step 4 & 5: Apply coverage constraints and sort
    # Sort by fit score (desc), then tie-breaker (asc)
    scored_candidates.sort(key=lambda x: (-x["fit_score"], x["tie_breaker"]))

    # Step 5: Apply theme and difficulty mix constraints
    selected = []
    theme_counts = {tid: 0 for tid in target_themes}
    difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}

    # Calculate target counts
    target_theme_weak = int(count * theme_mix.get("weak", 0.5))
    target_theme_medium = int(count * theme_mix.get("medium", 0.3))

    target_easy = int(count * difficulty_mix.get("easy", 0.2))
    target_medium = int(count * difficulty_mix.get("medium", 0.6))
    target_hard = count - target_easy - target_medium

    # Determine difficulty bucket
    def get_difficulty_bucket(rating: float) -> str:
        for bucket, (low, high) in difficulty_bucket_limits.items():
            if low <= rating < high:
                return bucket
        return "medium"

    # Multi-pass selection to respect constraints
    for candidate in scored_candidates:
        if len(selected) >= count:
            break

        theme_id = candidate["theme_id"]
        rating = candidate["rating"]
        bucket = get_difficulty_bucket(rating)

        # Check constraints
        # Prefer even distribution across themes
        max_per_theme = (count // len(target_themes)) + 1
        if theme_counts[theme_id] >= max_per_theme:
            continue

        # Check difficulty mix (soft constraint - can exceed if needed)
        if bucket == "easy" and difficulty_counts["easy"] >= target_easy + 2:
            continue
        if bucket == "hard" and difficulty_counts["hard"] >= target_hard + 2:
            continue

        # Add to selection
        selected.append(candidate["question_id"])
        theme_counts[theme_id] += 1
        difficulty_counts[bucket] += 1

    # If we didn't get enough, relax constraints
    if len(selected) < count:
        for candidate in scored_candidates:
            if len(selected) >= count:
                break
            if candidate["question_id"] not in selected:
                selected.append(candidate["question_id"])

    logger.info(
        f"Selected {len(selected)} questions: "
        f"themes={list(theme_counts.values())}, "
        f"difficulty={list(difficulty_counts.values())}"
    )

    return selected[:count]
