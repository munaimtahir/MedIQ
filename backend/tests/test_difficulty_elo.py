"""
Comprehensive tests for Difficulty Calibration (Elo v1).

Tests:
- Core math functions
- Property tests (no NaN/Inf, bounded outputs)
- Service layer (rating creation, updates, idempotency)
- Recenter (preserves θ-b differences)
- Uncertainty dynamics
"""

import math
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.learning_engine.difficulty.core import (
    apply_update,
    compute_delta,
    compute_dynamic_k,
    p_correct,
    sigmoid,
    update_uncertainty,
    validate_rating_finite,
)
from app.learning_engine.difficulty.recenter import recenter_question_ratings
from app.learning_engine.difficulty.service import (
    get_or_create_question_rating,
    get_or_create_user_rating,
    update_difficulty_from_attempt,
)
from app.models.difficulty import (
    DifficultyQuestionRating,
    DifficultyUpdateLog,
    RatingScope,
)
from app.models.question_cms import Question, QuestionStatus
from app.models.user import User, UserRole

# === Core Math Tests ===


def test_sigmoid_bounded():
    """Sigmoid output always in [0, 1]."""
    test_values = [-1000, -100, -10, -1, 0, 1, 10, 100, 1000]
    for x in test_values:
        s = sigmoid(x)
        assert 0.0 <= s <= 1.0, f"sigmoid({x}) = {s} out of bounds"
        assert math.isfinite(s), f"sigmoid({x}) = {s} not finite"


def test_sigmoid_monotonic():
    """Sigmoid is monotonically increasing."""
    x_values = [-10, -5, -1, 0, 1, 5, 10]
    sig_values = [sigmoid(x) for x in x_values]

    for i in range(len(sig_values) - 1):
        assert sig_values[i] < sig_values[i + 1], "Sigmoid not monotonic"


def test_p_correct_respects_guess_floor():
    """P(correct) always >= guess_floor."""
    guess_floor = 0.20
    scale = 400.0

    # Even with worst ability and hardest question
    theta = -1000.0
    b = 1000.0
    p = p_correct(theta, b, guess_floor, scale)

    assert p >= guess_floor, f"P(correct) = {p} < guess_floor = {guess_floor}"
    assert p <= 1.0, f"P(correct) = {p} > 1.0"


def test_p_correct_at_parity():
    """When theta = b, p should be near 0.6 (guess_floor + 0.5 * (1 - guess_floor))."""
    theta = 0.0
    b = 0.0
    guess_floor = 0.20
    scale = 400.0

    p = p_correct(theta, b, guess_floor, scale)

    # At parity, sigmoid(0) = 0.5, so p = 0.2 + 0.8 * 0.5 = 0.6
    expected = guess_floor + (1 - guess_floor) * 0.5
    assert abs(p - expected) < 0.01, f"P(correct) at parity: {p}, expected ~{expected}"


def test_p_correct_increases_with_ability():
    """Higher theta -> higher p(correct)."""
    b = 0.0
    guess_floor = 0.20
    scale = 400.0

    theta_values = [-400, -200, 0, 200, 400]
    p_values = [p_correct(theta, b, guess_floor, scale) for theta in theta_values]

    for i in range(len(p_values) - 1):
        assert p_values[i] < p_values[i + 1], "P(correct) not increasing with theta"


def test_compute_delta():
    """Delta computation is correct."""
    # Correct answer, predicted 0.7
    delta = compute_delta(True, 0.7)
    assert abs(delta - 0.3) < 0.001, f"Delta for correct: {delta}, expected 0.3"

    # Incorrect answer, predicted 0.7
    delta = compute_delta(False, 0.7)
    assert abs(delta - (-0.7)) < 0.001, f"Delta for incorrect: {delta}, expected -0.7"


def test_compute_dynamic_k_bounded():
    """Dynamic K always in [k_min, k_max]."""
    k_base = 32.0
    k_min = 8.0
    k_max = 64.0

    unc_values = [0, 10, 32, 100, 500, 1000]
    for unc in unc_values:
        k = compute_dynamic_k(k_base, unc, k_min, k_max)
        assert k_min <= k <= k_max, f"K = {k} out of bounds for unc={unc}"
        assert math.isfinite(k), f"K = {k} not finite"


def test_compute_dynamic_k_monotonic():
    """K increases monotonically with uncertainty."""
    k_base = 32.0
    k_min = 8.0
    k_max = 64.0

    unc_values = [0, 10, 32, 100, 500]
    k_values = [compute_dynamic_k(k_base, unc, k_min, k_max) for unc in unc_values]

    for i in range(len(k_values) - 1):
        assert k_values[i] <= k_values[i + 1], "K not monotonic with uncertainty"


def test_update_uncertainty_decays():
    """Uncertainty decreases with attempts."""
    unc = 350.0
    n_attempts = 5
    last_seen_at = datetime.now(UTC) - timedelta(hours=1)
    now = datetime.now(UTC)
    unc_floor = 50.0
    unc_decay = 0.9
    unc_age_rate = 1.0

    unc_new = update_uncertainty(
        unc, n_attempts, last_seen_at, now, unc_floor, unc_decay, unc_age_rate
    )

    # Should be less than original (decay dominates over 1 hour of age)
    assert unc_new < unc, "Uncertainty did not decay"
    assert unc_new >= unc_floor, f"Uncertainty {unc_new} below floor {unc_floor}"


def test_update_uncertainty_ages():
    """Uncertainty increases with inactivity."""
    unc = 50.0  # At floor
    n_attempts = 10
    last_seen_at = datetime.now(UTC) - timedelta(days=30)
    now = datetime.now(UTC)
    unc_floor = 50.0
    unc_decay = 0.9
    unc_age_rate = 1.0

    unc_new = update_uncertainty(
        unc, n_attempts, last_seen_at, now, unc_floor, unc_decay, unc_age_rate
    )

    # After 30 days, should increase by ~30 points
    assert unc_new > unc, "Uncertainty did not increase with age"


def test_apply_update_correct_answer():
    """Correct answer increases user rating and decreases question difficulty."""
    theta = 0.0
    b = 0.0
    k_u = 32.0
    k_q = 24.0
    delta = 0.3  # Correct answer with p_pred = 0.7

    theta_new, b_new = apply_update(theta, b, k_u, k_q, delta)

    assert theta_new > theta, "User rating did not increase after correct"
    assert b_new < b, "Question difficulty did not decrease after correct"


def test_apply_update_incorrect_answer():
    """Incorrect answer decreases user rating and increases question difficulty."""
    theta = 0.0
    b = 0.0
    k_u = 32.0
    k_q = 24.0
    delta = -0.7  # Incorrect answer with p_pred = 0.7

    theta_new, b_new = apply_update(theta, b, k_u, k_q, delta)

    assert theta_new < theta, "User rating did not decrease after incorrect"
    assert b_new > b, "Question difficulty did not increase after incorrect"


def test_validate_rating_finite():
    """Validation catches non-finite ratings."""
    validate_rating_finite(0.0)
    validate_rating_finite(100.0)
    validate_rating_finite(-100.0)

    with pytest.raises(ValueError):
        validate_rating_finite(float("nan"))

    with pytest.raises(ValueError):
        validate_rating_finite(float("inf"))


# === Property Tests ===


def test_no_nan_in_p_correct():
    """P(correct) never produces NaN for any finite inputs."""
    import random

    random.seed(42)

    for _ in range(100):
        theta = random.uniform(-1000, 1000)
        b = random.uniform(-1000, 1000)
        guess_floor = random.uniform(0.1, 0.3)
        scale = random.uniform(100, 500)

        p = p_correct(theta, b, guess_floor, scale)
        assert math.isfinite(p), f"NaN/Inf for theta={theta}, b={b}"
        assert guess_floor <= p <= 1.0


def test_no_nan_in_dynamic_k():
    """Dynamic K never produces NaN."""
    import random

    random.seed(42)

    for _ in range(100):
        k_base = random.uniform(10, 50)
        unc = random.uniform(0, 500)
        k_min = random.uniform(5, 10)
        k_max = random.uniform(50, 100)

        k = compute_dynamic_k(k_base, unc, k_min, k_max)
        assert math.isfinite(k)
        assert k_min <= k <= k_max


# === Service Layer Tests ===


@pytest.fixture
async def test_user_async(db_session):
    """Create a test user in async session."""
    from app.core.security import hash_password
    
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"test_user_{user_id}@example.com",
        full_name="Test User",
        password_hash=hash_password("Test123!"),
        role=UserRole.STUDENT.value,
        is_active=True,
        email_verified=True,
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.flush()
    # Refresh to ensure user is accessible
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_question_async(db_session, test_user_async):
    """Create a test question in async session."""
    question_id = uuid4()
    question = Question(
        id=question_id,
        status=QuestionStatus.PUBLISHED,
        year_id=1,
        block_id=1,
        theme_id=1,
        stem="Test Question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        option_e="E",
        correct_index=0,
        explanation_md="Test explanation",
        difficulty="MEDIUM",
        cognitive_level="UNDERSTAND",
        created_by=test_user_async.id,
        updated_by=test_user_async.id,
    )
    db_session.add(question)
    await db_session.flush()
    # Refresh to ensure question is accessible
    await db_session.refresh(question)
    return question


@pytest.mark.asyncio
async def test_get_or_create_user_rating(db_session, test_user_async):
    """Get or create user rating initializes correctly."""
    user_id = test_user_async.id
    params = {"rating_init": 0.0, "unc_init_user": 350.0}

    # First call creates
    rating1 = await get_or_create_user_rating(db_session, user_id, RatingScope.GLOBAL, None, params)
    await db_session.commit()

    assert rating1.user_id == user_id
    assert rating1.scope_type == RatingScope.GLOBAL.value
    assert rating1.rating == 0.0
    assert rating1.uncertainty == 350.0
    assert rating1.n_attempts == 0

    # Second call retrieves same
    rating2 = await get_or_create_user_rating(db_session, user_id, RatingScope.GLOBAL, None, params)
    assert rating2.id == rating1.id


@pytest.mark.asyncio
async def test_get_or_create_question_rating(db_session, test_question_async):
    """Get or create question rating initializes correctly."""
    question_id = test_question_async.id
    params = {"rating_init": 0.0, "unc_init_question": 250.0}

    # First call creates
    rating1 = await get_or_create_question_rating(
        db_session, question_id, RatingScope.GLOBAL, None, params
    )
    await db_session.commit()

    assert rating1.question_id == question_id
    assert rating1.scope_type == RatingScope.GLOBAL.value
    assert rating1.rating == 0.0
    assert rating1.uncertainty == 250.0
    assert rating1.n_attempts == 0

    # Second call retrieves same
    rating2 = await get_or_create_question_rating(
        db_session, question_id, RatingScope.GLOBAL, None, params
    )
    assert rating2.id == rating1.id


@pytest.mark.asyncio
async def test_update_difficulty_from_attempt_creates_ratings(
    db_session, test_user_async, test_question_async, active_difficulty_algo
):
    """First attempt creates user and question ratings."""
    result = await update_difficulty_from_attempt(
        db_session,
        user_id=test_user_async.id,
        question_id=test_question_async.id,
        theme_id=None,
        score=True,
        attempt_id=uuid4(),
        occurred_at=datetime.now(UTC),
    )

    assert result["p_pred"] > 0
    assert result["scope_updated"] == "GLOBAL"
    assert "user_rating_global" in result
    assert "question_rating_global" in result


@pytest.mark.asyncio
async def test_update_difficulty_idempotent(
    db_session, test_user_async, test_question_async, active_difficulty_algo
):
    """Same attempt_id is idempotent."""
    attempt_id = uuid4()

    # First update
    result1 = await update_difficulty_from_attempt(
        db_session,
        user_id=test_user_async.id,
        question_id=test_question_async.id,
        theme_id=None,
        score=True,
        attempt_id=attempt_id,
        occurred_at=datetime.now(UTC),
    )

    # Second update with same attempt_id
    result2 = await update_difficulty_from_attempt(
        db_session,
        user_id=test_user_async.id,
        question_id=test_question_async.id,
        theme_id=None,
        score=True,
        attempt_id=attempt_id,
        occurred_at=datetime.now(UTC),
    )

    assert result2.get("duplicate")
    assert result2["p_pred"] == result1["p_pred"]


@pytest.mark.asyncio
async def test_update_difficulty_logs_update(
    db_session, test_user_async, test_question_async, active_difficulty_algo
):
    """Update creates log entry with pre/post values."""
    await update_difficulty_from_attempt(
        db_session,
        user_id=test_user_async.id,
        question_id=test_question_async.id,
        theme_id=None,
        score=True,
        attempt_id=uuid4(),
        occurred_at=datetime.now(UTC),
    )

    # Check log exists
    stmt = select(DifficultyUpdateLog).where(DifficultyUpdateLog.user_id == test_user_async.id)
    result = await db_session.execute(stmt)
    log = result.scalar_one()

    assert log.score
    assert log.p_pred > 0
    assert math.isfinite(log.user_rating_pre)
    assert math.isfinite(log.user_rating_post)
    assert math.isfinite(log.q_rating_pre)
    assert math.isfinite(log.q_rating_post)
    assert log.k_u_used > 0
    assert log.k_q_used > 0


# === Recenter Tests ===


@pytest.mark.asyncio
async def test_recenter_preserves_differences(
    db_session, test_user_async, test_question_async, active_difficulty_algo
):
    """Recentering preserves θ - b differences."""
    # Create some ratings
    user_rating = await get_or_create_user_rating(
        db_session, test_user_async.id, RatingScope.GLOBAL, None, {}
    )
    user_rating.rating = 100.0

    question_rating = await get_or_create_question_rating(
        db_session, test_question_async.id, RatingScope.GLOBAL, None, {}
    )
    question_rating.rating = 50.0

    await db_session.commit()

    # Record difference before
    diff_before = user_rating.rating - question_rating.rating

    # Recenter
    await recenter_question_ratings(db_session, RatingScope.GLOBAL, None)

    # Reload ratings
    await db_session.refresh(user_rating)
    await db_session.refresh(question_rating)

    # Check difference preserved
    diff_after = user_rating.rating - question_rating.rating
    assert abs(diff_before - diff_after) < 0.01, "Difference not preserved by recenter"


@pytest.mark.asyncio
async def test_recenter_zeros_mean(db_session, test_question_async, active_difficulty_algo):
    """Recentering brings mean question rating to ~0."""
    from sqlalchemy import func

    from app.models.syllabus import Theme

    # Create multiple questions with various ratings
    theme_stmt = select(Theme).limit(1)
    result = await db_session.execute(theme_stmt)
    theme = result.scalar_one()

    question_ids = []
    for i in range(5):
        from app.models.question_cms import Question as CMSQuestion
        from app.models.question_cms import QuestionStatus

        q = CMSQuestion(
            year=2024,
            block_id=theme.block_id,
            theme_id=theme.id,
            status=QuestionStatus.PUBLISHED,
            stem=f"Test question {i}",
            options_json=["A", "B", "C", "D", "E"],
            correct_answer="A",
            explanation="Test",
            cognitive_level="RECALL",
        )
        db_session.add(q)
        await db_session.flush()
        question_ids.append(q.id)

        # Create rating with varying values
        rating = await get_or_create_question_rating(db_session, q.id, RatingScope.GLOBAL, None, {})
        rating.rating = float(i * 50 - 100)  # -100, -50, 0, 50, 100

    await db_session.commit()

    # Recenter
    await recenter_question_ratings(db_session, RatingScope.GLOBAL, None)

    # Check mean is near zero
    stmt = select(func.avg(DifficultyQuestionRating.rating)).where(
        DifficultyQuestionRating.scope_type == RatingScope.GLOBAL.value,
        DifficultyQuestionRating.scope_id.is_(None),
    )
    result = await db_session.execute(stmt)
    mean = result.scalar()

    assert abs(mean) < 1.0, f"Mean question rating after recenter: {mean}, expected ~0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
