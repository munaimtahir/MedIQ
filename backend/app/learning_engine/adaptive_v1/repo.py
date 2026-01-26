"""
Repository layer for Adaptive Selection v1.

Provides optimized database queries for:
- Candidate themes with supply counts
- FSRS due concepts
- BKT mastery by concept/theme
- Elo predicted probability
- Recent question exclusions
- Bandit state management
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.difficulty.core import p_correct
from app.models.adaptive import BanditUserThemeState
from app.models.bkt import BKTUserSkillState
from app.models.difficulty import DifficultyQuestionRating, DifficultyUserRating, RatingScope
from app.models.question_cms import Question, QuestionStatus
from app.models.session import SessionAnswer, SessionQuestion, TestSession
from app.models.srs import SRSConceptState
from app.models.syllabus import Block, Theme

logger = logging.getLogger(__name__)


async def get_candidate_themes(
    db: AsyncSession,
    user_id: UUID,
    year: int,
    block_ids: list[int],
    theme_ids_filter: list[int] | None = None,
    max_candidates: int = 30,
) -> list[dict]:
    """
    Get candidate themes for selection.

    Returns themes in the specified year/blocks with basic metadata.
    Ordered by block order then theme order for determinism.

    Args:
        db: Database session
        user_id: User ID
        year: Academic year
        block_ids: List of block IDs to include
        theme_ids_filter: Optional explicit theme filter
        max_candidates: Maximum themes to return

    Returns:
        List of theme dicts with id, title, block_id
    """
    query = (
        select(Theme.id, Theme.title, Theme.block_id, Block.order_no.label("block_order"))
        .join(Block, Theme.block_id == Block.id)
        .where(
            and_(
                Theme.block_id.in_(block_ids),
                Theme.is_active == True,  # noqa: E712
                Block.year_id == year,
            )
        )
        .order_by(Block.order_no, Theme.order_no)
        .limit(max_candidates)
    )

    if theme_ids_filter:
        query = query.where(Theme.id.in_(theme_ids_filter))

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "theme_id": row.id,
            "title": row.title,
            "block_id": row.block_id,
        }
        for row in rows
    ]


async def get_theme_supply(
    db: AsyncSession,
    theme_id: int,
    exclude_question_ids: set[UUID] | None = None,
) -> int:
    """
    Count eligible questions for a theme.

    Args:
        db: Database session
        theme_id: Theme ID
        exclude_question_ids: Question IDs to exclude

    Returns:
        Count of eligible published questions
    """
    query = select(func.count(Question.id)).where(
        and_(
            Question.theme_id == theme_id,
            Question.status == QuestionStatus.PUBLISHED,
        )
    )

    if exclude_question_ids:
        query = query.where(Question.id.notin_(exclude_question_ids))

    result = await db.execute(query)
    return result.scalar() or 0


async def get_theme_supply_batch(
    db: AsyncSession,
    theme_ids: list[int],
    exclude_question_ids: set[UUID] | None = None,
) -> dict[int, int]:
    """
    Batch get supply counts for multiple themes.

    Args:
        db: Database session
        theme_ids: List of theme IDs
        exclude_question_ids: Question IDs to exclude

    Returns:
        Dict mapping theme_id -> eligible question count
    """
    query = (
        select(Question.theme_id, func.count(Question.id).label("count"))
        .where(
            and_(
                Question.theme_id.in_(theme_ids),
                Question.status == QuestionStatus.PUBLISHED,
            )
        )
        .group_by(Question.theme_id)
    )

    if exclude_question_ids:
        query = query.where(Question.id.notin_(exclude_question_ids))

    result = await db.execute(query)
    rows = result.all()

    # Initialize all themes with 0, then fill from query
    supply = {tid: 0 for tid in theme_ids}
    for row in rows:
        supply[row.theme_id] = row.count

    return supply


async def get_due_concepts_by_theme(
    db: AsyncSession,
    user_id: UUID,
    theme_ids: list[int],
    now: datetime | None = None,
) -> dict[int, list[UUID]]:
    """
    Get FSRS due concepts grouped by theme.

    Note: This requires concept-to-theme mapping. Currently using a simplified
    approach where concept_id may not directly map to theme_id.
    In production, you'd need a concept->theme mapping table.

    Args:
        db: Database session
        user_id: User ID
        theme_ids: Theme IDs to check
        now: Current time (defaults to now)

    Returns:
        Dict mapping theme_id -> list of due concept_ids
    """
    if now is None:
        now = datetime.now(UTC)

    # Query due concepts
    query = select(SRSConceptState).where(
        and_(
            SRSConceptState.user_id == user_id,
            SRSConceptState.due_at.isnot(None),
            SRSConceptState.due_at <= now,
        )
    )

    result = await db.execute(query)
    due_states = result.scalars().all()

    # For now, we return all due concepts without theme grouping
    # In production, you'd join with a concept->theme mapping table
    # This is a simplified placeholder that returns empty per-theme
    due_by_theme: dict[int, list[UUID]] = {tid: [] for tid in theme_ids}

    # TODO: Implement proper concept->theme mapping when available
    # For now, distribute due concepts across themes proportionally
    # This is a placeholder until proper data model exists

    logger.debug(f"Found {len(due_states)} due concepts for user {user_id}")

    return due_by_theme


async def get_bkt_mastery_by_theme(
    db: AsyncSession,
    user_id: UUID,
    theme_ids: list[int],
) -> dict[int, float]:
    """
    Get average BKT mastery per theme.

    Aggregates concept-level mastery to theme level.
    Returns 0.5 (uncertain) for themes with no data.

    Args:
        db: Database session
        user_id: User ID
        theme_ids: Theme IDs to query

    Returns:
        Dict mapping theme_id -> average mastery [0,1]
    """
    # Get all user skill states
    query = select(BKTUserSkillState).where(BKTUserSkillState.user_id == user_id)
    result = await db.execute(query)
    states = result.scalars().all()

    # For now, we don't have concept->theme mapping, so return default
    # In production, you'd join BKT states with concept->theme mapping
    mastery_by_theme: dict[int, float] = {tid: 0.5 for tid in theme_ids}

    # TODO: Implement proper concept->theme aggregation when mapping exists

    logger.debug(f"Returning default mastery for {len(theme_ids)} themes")

    return mastery_by_theme


async def get_user_theme_uncertainty(
    db: AsyncSession,
    user_id: UUID,
    theme_id: int,
) -> float | None:
    """
    Get Elo uncertainty for user in a specific theme.

    Args:
        db: Database session
        user_id: User ID
        theme_id: Theme ID

    Returns:
        Uncertainty value or None if no rating exists
    """
    query = select(DifficultyUserRating).where(
        and_(
            DifficultyUserRating.user_id == user_id,
            DifficultyUserRating.scope_type == RatingScope.THEME.value,
            DifficultyUserRating.scope_id == str(theme_id),
        )
    )
    result = await db.execute(query)
    rating = result.scalar_one_or_none()

    return rating.uncertainty if rating else None


async def get_recently_seen_question_ids(
    db: AsyncSession,
    user_id: UUID,
    within_days: int,
    within_sessions: int,
) -> set[UUID]:
    """
    Get question IDs seen recently (for anti-repeat filtering).

    Combines time-based and session-based exclusion.

    Args:
        db: Database session
        user_id: User ID
        within_days: Exclude questions seen within N days
        within_sessions: Exclude questions from last N sessions

    Returns:
        Set of question IDs to exclude
    """
    cutoff_date = datetime.now(UTC) - timedelta(days=within_days)

    # Time-based exclusion
    time_query = (
        select(SessionAnswer.question_id.distinct())
        .join(TestSession, SessionAnswer.session_id == TestSession.id)
        .where(
            and_(
                SessionAnswer.user_id == user_id,
                TestSession.started_at >= cutoff_date,
            )
        )
    )

    time_result = await db.execute(time_query)
    time_excluded = {row[0] for row in time_result.all()}

    # Session-based exclusion (last N sessions)
    recent_sessions_query = (
        select(TestSession.id)
        .where(TestSession.user_id == user_id)
        .order_by(TestSession.started_at.desc())
        .limit(within_sessions)
    )

    sessions_result = await db.execute(recent_sessions_query)
    recent_session_ids = [row[0] for row in sessions_result.all()]

    if recent_session_ids:
        session_query = select(SessionAnswer.question_id.distinct()).where(
            SessionAnswer.session_id.in_(recent_session_ids)
        )
        session_result = await db.execute(session_query)
        session_excluded = {row[0] for row in session_result.all()}
    else:
        session_excluded = set()

    # Combine both exclusion sets
    all_excluded = time_excluded | session_excluded

    logger.debug(
        f"Excluding {len(all_excluded)} questions "
        f"(time: {len(time_excluded)}, session: {len(session_excluded)})"
    )

    return all_excluded


async def get_questions_for_theme(
    db: AsyncSession,
    theme_id: int,
    exclude_question_ids: set[UUID] | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Get candidate questions for a theme with Elo ratings.

    Args:
        db: Database session
        theme_id: Theme ID
        exclude_question_ids: Questions to exclude
        limit: Maximum questions to return

    Returns:
        List of question dicts with id, concept_id, difficulty rating
    """
    query = (
        select(
            Question.id,
            Question.concept_id,
            DifficultyQuestionRating.rating.label("difficulty_rating"),
            DifficultyQuestionRating.uncertainty.label("difficulty_uncertainty"),
            DifficultyQuestionRating.n_attempts.label("difficulty_attempts"),
        )
        .outerjoin(
            DifficultyQuestionRating,
            and_(
                DifficultyQuestionRating.question_id == Question.id,
                DifficultyQuestionRating.scope_type == RatingScope.GLOBAL.value,
            ),
        )
        .where(
            and_(
                Question.theme_id == theme_id,
                Question.status == QuestionStatus.PUBLISHED,
            )
        )
        .limit(limit)
    )

    if exclude_question_ids:
        query = query.where(Question.id.notin_(exclude_question_ids))

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "question_id": row.id,
            "concept_id": row.concept_id,
            "difficulty_rating": row.difficulty_rating or 0.0,
            "difficulty_uncertainty": row.difficulty_uncertainty,
            "difficulty_attempts": row.difficulty_attempts or 0,
        }
        for row in rows
    ]


async def get_user_global_rating(
    db: AsyncSession,
    user_id: UUID,
) -> tuple[float, float]:
    """
    Get user's global Elo rating and uncertainty.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Tuple of (rating, uncertainty), defaults to (0.0, 350.0) if not found
    """
    query = select(DifficultyUserRating).where(
        and_(
            DifficultyUserRating.user_id == user_id,
            DifficultyUserRating.scope_type == RatingScope.GLOBAL.value,
            DifficultyUserRating.scope_id.is_(None),
        )
    )
    result = await db.execute(query)
    rating = result.scalar_one_or_none()

    if rating:
        return rating.rating, rating.uncertainty

    # Default values for new users
    return 0.0, 350.0


def predict_p_correct(
    user_rating: float,
    question_rating: float,
    guess_floor: float = 0.20,
    scale: float = 400.0,
) -> float:
    """
    Predict probability of correct answer using Elo model.

    Args:
        user_rating: User ability (θ)
        question_rating: Question difficulty (b)
        guess_floor: Minimum probability (MCQ guess floor)
        scale: Logistic scale parameter

    Returns:
        Probability of correct answer [guess_floor, 1.0]
    """
    return p_correct(user_rating, question_rating, guess_floor, scale)


# =============================================================================
# Bandit State Management
# =============================================================================


async def get_bandit_state(
    db: AsyncSession,
    user_id: UUID,
    theme_id: int,
) -> BanditUserThemeState | None:
    """
    Get bandit state for a (user, theme) pair.

    Args:
        db: Database session
        user_id: User ID
        theme_id: Theme ID

    Returns:
        BanditUserThemeState or None if not exists
    """
    query = select(BanditUserThemeState).where(
        and_(
            BanditUserThemeState.user_id == user_id,
            BanditUserThemeState.theme_id == theme_id,
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_bandit_states_batch(
    db: AsyncSession,
    user_id: UUID,
    theme_ids: list[int],
) -> dict[int, BanditUserThemeState]:
    """
    Batch get bandit states for multiple themes.

    Args:
        db: Database session
        user_id: User ID
        theme_ids: Theme IDs

    Returns:
        Dict mapping theme_id -> BanditUserThemeState (only for existing states)
    """
    query = select(BanditUserThemeState).where(
        and_(
            BanditUserThemeState.user_id == user_id,
            BanditUserThemeState.theme_id.in_(theme_ids),
        )
    )
    result = await db.execute(query)
    states = result.scalars().all()

    return {state.theme_id: state for state in states}


async def upsert_bandit_state(
    db: AsyncSession,
    user_id: UUID,
    theme_id: int,
    a: float,
    b: float,
    n_sessions: int,
    last_selected_at: datetime,
    last_reward: float | None = None,
) -> BanditUserThemeState:
    """
    Create or update bandit state for a (user, theme) pair.

    Args:
        db: Database session
        user_id: User ID
        theme_id: Theme ID
        a: Beta alpha
        b: Beta beta
        n_sessions: Session count
        last_selected_at: When last selected
        last_reward: Reward from last session

    Returns:
        Updated BanditUserThemeState
    """
    state = await get_bandit_state(db, user_id, theme_id)

    if state:
        state.a = a
        state.b = b
        state.n_sessions = n_sessions
        state.last_selected_at = last_selected_at
        state.last_reward = last_reward
        state.updated_at = datetime.now(UTC)
    else:
        state = BanditUserThemeState(
            user_id=user_id,
            theme_id=theme_id,
            a=a,
            b=b,
            n_sessions=n_sessions,
            last_selected_at=last_selected_at,
            last_reward=last_reward,
            updated_at=datetime.now(UTC),
        )
        db.add(state)

    await db.flush()
    return state
