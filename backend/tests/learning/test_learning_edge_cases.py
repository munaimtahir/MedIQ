"""Tests for learning engine edge cases (zero attempts, all correct, all incorrect)."""

import math
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning_engine.difficulty.service import update_difficulty_from_attempt
from app.learning_engine.mastery.service import compute_mastery_for_theme
from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
async def test_mastery_zero_attempts(
    db_session: AsyncSession,
    test_user,
) -> None:
    """Test mastery computation with zero attempts."""
    # Compute mastery for a theme with no attempts
    result = await compute_mastery_for_theme(
        db_session,
        user_id=test_user.id,
        year=1,
        block_id=1,
        theme_id=999,  # Non-existent theme (no attempts)
        params={"lookback_days": 90, "min_attempts": 5},
        current_time=datetime.now(UTC),
    )
    
    # Should return zero or neutral mastery
    assert result["attempts_total"] == 0
    assert result["correct_total"] == 0
    assert result["accuracy_pct"] == 0.0
    assert result["mastery_score"] == 0.0  # Or neutral value
    assert "insufficient_attempts" in str(result.get("breakdown_json", {})).lower()


@pytest.mark.asyncio
async def test_mastery_all_correct(
    db_session: AsyncSession,
    test_user,
    published_questions,
) -> None:
    """Test mastery computation with all correct attempts."""
    from app.models.attempt import AttemptEvent
    from datetime import timedelta
    
    # Create multiple correct attempts for same theme
    theme_id = published_questions[0].theme_id
    now = datetime.now(UTC)
    
    for i in range(5):
        attempt_event = AttemptEvent(
            id=uuid4(),
            user_id=test_user.id,
            session_id=uuid4(),
            question_id=published_questions[0].id,
            event_type="ANSWER_SUBMITTED",
            event_ts=now - timedelta(days=i),
            payload_json={"is_correct": True, "selected_index": 0},
        )
        db_session.add(attempt_event)
    
    await db_session.commit()
    
    # Compute mastery
    result = await compute_mastery_for_theme(
        db_session,
        user_id=test_user.id,
        year=1,
        block_id=1,
        theme_id=theme_id,
        params={"lookback_days": 90, "min_attempts": 5},
        current_time=now,
    )
    
    # Should have high mastery
    assert result["attempts_total"] >= 5
    assert result["correct_total"] == result["attempts_total"]  # All correct
    assert result["accuracy_pct"] == 100.0
    assert result["mastery_score"] > 0.5  # Should be high
    assert math.isfinite(result["mastery_score"])
    assert 0.0 <= result["mastery_score"] <= 1.0


@pytest.mark.asyncio
async def test_mastery_all_incorrect(
    db_session: AsyncSession,
    test_user,
    published_questions,
) -> None:
    """Test mastery computation with all incorrect attempts."""
    from app.models.attempt import AttemptEvent
    from datetime import timedelta
    
    # Create multiple incorrect attempts for same theme
    theme_id = published_questions[0].theme_id
    now = datetime.now(UTC)
    
    for i in range(5):
        attempt_event = AttemptEvent(
            id=uuid4(),
            user_id=test_user.id,
            session_id=uuid4(),
            question_id=published_questions[0].id,
            event_type="ANSWER_SUBMITTED",
            event_ts=now - timedelta(days=i),
            payload_json={"is_correct": False, "selected_index": 1},  # Wrong answer
        )
        db_session.add(attempt_event)
    
    await db_session.commit()
    
    # Compute mastery
    result = await compute_mastery_for_theme(
        db_session,
        user_id=test_user.id,
        year=1,
        block_id=1,
        theme_id=theme_id,
        params={"lookback_days": 90, "min_attempts": 5},
        current_time=now,
    )
    
    # Should have low mastery
    assert result["attempts_total"] >= 5
    assert result["correct_total"] == 0  # All incorrect
    assert result["accuracy_pct"] == 0.0
    assert result["mastery_score"] < 0.5  # Should be low
    assert math.isfinite(result["mastery_score"])
    assert 0.0 <= result["mastery_score"] <= 1.0


@pytest.mark.asyncio
async def test_difficulty_zero_attempts(
    db_session: AsyncSession,
    test_user,
    published_questions,
) -> None:
    """Test difficulty update with no previous attempts."""
    question = published_questions[0]
    
    # First attempt (no previous data)
    result = await update_difficulty_from_attempt(
        db_session,
        user_id=test_user.id,
        question_id=question.id,
        theme_id=None,
        score=True,
        attempt_id=uuid4(),
        occurred_at=datetime.now(UTC),
    )
    
    # Should handle gracefully
    assert "p_pred" in result
    assert math.isfinite(result["p_pred"])
    assert 0.0 <= result["p_pred"] <= 1.0
    
    # Ratings should be finite
    if "user_rating_post" in result:
        assert math.isfinite(result["user_rating_post"])
    if "question_rating_post" in result:
        assert math.isfinite(result["question_rating_post"])


@pytest.mark.asyncio
async def test_difficulty_all_correct_attempts(
    db_session: AsyncSession,
    test_user,
    published_questions,
) -> None:
    """Test difficulty update with all correct attempts."""
    question = published_questions[0]
    
    # Make multiple correct attempts
    for i in range(5):
        result = await update_difficulty_from_attempt(
            db_session,
            user_id=test_user.id,
            question_id=question.id,
            theme_id=None,
            score=True,  # All correct
            attempt_id=uuid4(),
            occurred_at=datetime.now(UTC),
        )
        
        # Should handle correctly
        assert math.isfinite(result.get("p_pred", 0.5))
        
        # Ratings should remain finite and reasonable
        if "user_rating_post" in result:
            rating = result["user_rating_post"]
            assert math.isfinite(rating)
            assert rating >= 0  # ELO should be non-negative
        if "question_rating_post" in result:
            rating = result["question_rating_post"]
            assert math.isfinite(rating)
            assert rating >= 0


@pytest.mark.asyncio
async def test_difficulty_all_incorrect_attempts(
    db_session: AsyncSession,
    test_user,
    published_questions,
) -> None:
    """Test difficulty update with all incorrect attempts."""
    question = published_questions[0]
    
    # Make multiple incorrect attempts
    for i in range(5):
        result = await update_difficulty_from_attempt(
            db_session,
            user_id=test_user.id,
            question_id=question.id,
            theme_id=None,
            score=False,  # All incorrect
            attempt_id=uuid4(),
            occurred_at=datetime.now(UTC),
        )
        
        # Should handle correctly
        assert math.isfinite(result.get("p_pred", 0.5))
        
        # Ratings should remain finite and reasonable
        if "user_rating_post" in result:
            rating = result["user_rating_post"]
            assert math.isfinite(rating)
            assert rating >= 0
        if "question_rating_post" in result:
            rating = result["question_rating_post"]
            assert math.isfinite(rating)
            assert rating >= 0
