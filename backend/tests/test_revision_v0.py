"""
Tests for Revision Scheduler v0.
"""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4

from app.learning_engine.revision.service import (
    compute_priority_score,
    compute_spacing_days,
    generate_revision_queue_v0,
    get_mastery_band,
    get_recommended_count,
)
from app.models.learning import AlgoVersion
from app.models.learning_mastery import UserThemeMastery
from app.models.learning_revision import RevisionQueue
from app.models.syllabus import Block, Theme
from app.models.user import User, UserRole
from sqlalchemy import select


@pytest.fixture
async def student_user(db):
    """Create a test student user."""
    user = User(
        id=uuid4(),
        email="student@test.com",
        hashed_password="hashed",
        full_name="Test Student",
        role=UserRole.STUDENT,
        year=1,
        is_email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def block_and_themes(db):
    """Create test block and themes."""
    block = Block(
        id=1,
        name="Test Block",
        order_index=1,
        year=1,
    )
    db.add(block)
    await db.commit()

    themes = []
    for i in range(3):
        theme = Theme(
            id=i + 1,
            block_id=1,
            title=f"Theme {i + 1}",
            order_index=i + 1,
        )
        themes.append(theme)

    db.add_all(themes)
    await db.commit()

    return block, themes


@pytest.fixture
async def revision_algo_version(db):
    """Get revision algo version."""
    stmt = select(AlgoVersion).where(
        AlgoVersion.algo_key == "revision", AlgoVersion.version == "v0"
    )
    result = await db.execute(stmt)
    return result.scalar_one()


class TestMasteryBands:
    """Test mastery band classification."""

    def test_weak_band(self):
        """Test weak mastery band."""
        bands = [
            {"name": "weak", "max": 0.39},
            {"name": "medium", "max": 0.69},
            {"name": "strong", "max": 0.84},
            {"name": "mastered", "max": 1.00},
        ]

        assert get_mastery_band(0.2, bands) == "weak"
        assert get_mastery_band(0.39, bands) == "weak"

    def test_medium_band(self):
        """Test medium mastery band."""
        bands = [
            {"name": "weak", "max": 0.39},
            {"name": "medium", "max": 0.69},
            {"name": "strong", "max": 0.84},
            {"name": "mastered", "max": 1.00},
        ]

        assert get_mastery_band(0.5, bands) == "medium"
        assert get_mastery_band(0.69, bands) == "medium"

    def test_strong_band(self):
        """Test strong mastery band."""
        bands = [
            {"name": "weak", "max": 0.39},
            {"name": "medium", "max": 0.69},
            {"name": "strong", "max": 0.84},
            {"name": "mastered", "max": 1.00},
        ]

        assert get_mastery_band(0.75, bands) == "strong"
        assert get_mastery_band(0.84, bands) == "strong"

    def test_mastered_band(self):
        """Test mastered band."""
        bands = [
            {"name": "weak", "max": 0.39},
            {"name": "medium", "max": 0.69},
            {"name": "strong", "max": 0.84},
            {"name": "mastered", "max": 1.00},
        ]

        assert get_mastery_band(0.9, bands) == "mastered"
        assert get_mastery_band(1.0, bands) == "mastered"


class TestSpacing:
    """Test spacing computation."""

    def test_never_attempted_due_now(self):
        """Test that never-attempted themes are due now."""
        spacing_days = {"weak": 1, "medium": 2, "strong": 5, "mastered": 12}
        current_date = date(2026, 1, 21)

        due_date, is_due_now = compute_spacing_days("weak", None, spacing_days, current_date)

        assert due_date == current_date
        assert is_due_now is True

    def test_weak_spacing_one_day(self):
        """Test weak theme spacing (1 day)."""
        spacing_days = {"weak": 1, "medium": 2, "strong": 5, "mastered": 12}
        current_date = date(2026, 1, 21)
        last_attempt = datetime(2026, 1, 20, 10, 0, 0)

        due_date, is_due_now = compute_spacing_days(
            "weak", last_attempt, spacing_days, current_date
        )

        assert due_date == date(2026, 1, 21)
        assert is_due_now is True

    def test_strong_spacing_not_due_yet(self):
        """Test strong theme not due yet (5 days)."""
        spacing_days = {"weak": 1, "medium": 2, "strong": 5, "mastered": 12}
        current_date = date(2026, 1, 21)
        last_attempt = datetime(2026, 1, 20, 10, 0, 0)  # 1 day ago

        due_date, is_due_now = compute_spacing_days(
            "strong", last_attempt, spacing_days, current_date
        )

        assert due_date == date(2026, 1, 25)  # 5 days after last
        assert is_due_now is False

    def test_mastered_long_spacing(self):
        """Test mastered theme spacing (12 days)."""
        spacing_days = {"weak": 1, "medium": 2, "strong": 5, "mastered": 12}
        current_date = date(2026, 1, 21)
        last_attempt = datetime(2026, 1, 5, 10, 0, 0)  # 16 days ago

        due_date, is_due_now = compute_spacing_days(
            "mastered", last_attempt, spacing_days, current_date
        )

        assert due_date == date(2026, 1, 17)  # 12 days after last
        assert is_due_now is True  # Past due


class TestPriority:
    """Test priority score computation."""

    def test_weak_theme_high_priority(self):
        """Test weak theme gets high priority."""
        priority_weights = {
            "mastery_inverse": 70,
            "recency": 2,
            "low_data_bonus": 10,
        }
        current_date = date(2026, 1, 21)

        # Weak theme (0.3), recent (2 days ago), enough data
        priority = compute_priority_score(
            mastery_score=0.3,
            attempts_total=10,
            last_attempt_at=datetime(2026, 1, 19, 10, 0, 0),
            current_date=current_date,
            priority_weights=priority_weights,
            min_attempts=5,
        )

        # mastery_inverse = 0.7 * 70 = 49.0
        # recency = 2 * 2 = 4.0
        # low_data_bonus = 0
        # Total = 53.0
        assert priority == 53.0

    def test_strong_theme_low_priority(self):
        """Test strong theme gets lower priority."""
        priority_weights = {
            "mastery_inverse": 70,
            "recency": 2,
            "low_data_bonus": 10,
        }
        current_date = date(2026, 1, 21)

        # Strong theme (0.85), recent (1 day ago), enough data
        priority = compute_priority_score(
            mastery_score=0.85,
            attempts_total=10,
            last_attempt_at=datetime(2026, 1, 20, 10, 0, 0),
            current_date=current_date,
            priority_weights=priority_weights,
            min_attempts=5,
        )

        # mastery_inverse = 0.15 * 70 = 10.5
        # recency = 1 * 2 = 2.0
        # low_data_bonus = 0
        # Total = 12.5
        assert priority == 12.5

    def test_low_data_bonus_applied(self):
        """Test low data bonus is applied."""
        priority_weights = {
            "mastery_inverse": 70,
            "recency": 2,
            "low_data_bonus": 10,
        }
        current_date = date(2026, 1, 21)

        # Medium theme (0.6), recent, LOW DATA (3 attempts < 5 min)
        priority = compute_priority_score(
            mastery_score=0.6,
            attempts_total=3,
            last_attempt_at=datetime(2026, 1, 20, 10, 0, 0),
            current_date=current_date,
            priority_weights=priority_weights,
            min_attempts=5,
        )

        # mastery_inverse = 0.4 * 70 = 28.0
        # recency = 1 * 2 = 2.0
        # low_data_bonus = 10
        # Total = 40.0
        assert priority == 40.0


class TestRecommendedCount:
    """Test recommended question count."""

    def test_weak_theme_more_questions(self):
        """Test weak theme gets more questions."""
        question_counts = {
            "weak": [15, 20],
            "medium": [10, 15],
            "strong": [5, 10],
            "mastered": [5, 5],
        }

        # Low attempts -> lower bound
        count = get_recommended_count("weak", 3, question_counts, 5)
        assert count == 15

        # High attempts -> upper bound
        count = get_recommended_count("weak", 10, question_counts, 5)
        assert count == 20

    def test_mastered_theme_few_questions(self):
        """Test mastered theme gets fewer questions."""
        question_counts = {
            "weak": [15, 20],
            "medium": [10, 15],
            "strong": [5, 10],
            "mastered": [5, 5],
        }

        count = get_recommended_count("mastered", 10, question_counts, 5)
        assert count == 5


class TestRevisionQueueGeneration:
    """Test full revision queue generation."""

    async def test_generate_for_user_with_mastery(
        self, db, student_user, block_and_themes, revision_algo_version
    ):
        """Test generating revision queue for user with mastery records."""
        block, themes = block_and_themes

        # Create mastery records with different levels
        # Theme 1: Weak (0.3), recent
        # Theme 2: Strong (0.8), old
        # Theme 3: Medium (0.5), medium age
        mastery_data = [
            (themes[0].id, 0.3, 8, datetime.utcnow() - timedelta(days=1)),
            (themes[1].id, 0.8, 15, datetime.utcnow() - timedelta(days=10)),
            (themes[2].id, 0.5, 5, datetime.utcnow() - timedelta(days=3)),
        ]

        for theme_id, score, attempts, last_attempt in mastery_data:
            mastery = UserThemeMastery(
                id=uuid4(),
                user_id=student_user.id,
                year=1,
                block_id=block.id,
                theme_id=theme_id,
                attempts_total=attempts,
                correct_total=int(attempts * score),
                accuracy_pct=score * 100,
                mastery_score=score,
                last_attempt_at=last_attempt,
                computed_at=datetime.utcnow(),
                algo_version_id=revision_algo_version.id,
                params_id=uuid4(),
                run_id=uuid4(),
                breakdown_json={},
            )
            db.add(mastery)

        await db.commit()

        # Generate revision queue
        result = await generate_revision_queue_v0(
            db,
            user_id=student_user.id,
            trigger="test",
        )

        assert result["generated"] > 0
        assert result["due_today"] > 0

        # Verify records in database
        stmt = select(RevisionQueue).where(RevisionQueue.user_id == student_user.id)
        queue_result = await db.execute(stmt)
        queue_items = queue_result.scalars().all()

        assert len(queue_items) > 0

        # Verify all have correct fields
        for item in queue_items:
            assert item.user_id == student_user.id
            assert item.due_date is not None
            assert item.priority_score >= 0
            assert item.recommended_count > 0
            assert item.status == "DUE"
            assert "band" in item.reason_json
            assert item.algo_version_id is not None
            assert item.run_id is not None

    async def test_weak_theme_due_today(
        self, db, student_user, block_and_themes, revision_algo_version
    ):
        """Test weak theme is due today (1 day spacing)."""
        block, themes = block_and_themes

        # Weak theme attempted yesterday
        mastery = UserThemeMastery(
            id=uuid4(),
            user_id=student_user.id,
            year=1,
            block_id=block.id,
            theme_id=themes[0].id,
            attempts_total=8,
            correct_total=2,
            accuracy_pct=25.0,
            mastery_score=0.25,  # Weak
            last_attempt_at=datetime.utcnow() - timedelta(days=1),
            computed_at=datetime.utcnow(),
            algo_version_id=revision_algo_version.id,
            params_id=uuid4(),
            run_id=uuid4(),
            breakdown_json={},
        )
        db.add(mastery)
        await db.commit()

        result = await generate_revision_queue_v0(db, user_id=student_user.id, trigger="test")

        assert result["generated"] >= 1
        assert result["due_today"] >= 1

    async def test_strong_theme_not_due_yet(
        self, db, student_user, block_and_themes, revision_algo_version
    ):
        """Test strong theme not due yet (5 day spacing)."""
        block, themes = block_and_themes

        # Strong theme attempted 2 days ago (needs 5 days)
        mastery = UserThemeMastery(
            id=uuid4(),
            user_id=student_user.id,
            year=1,
            block_id=block.id,
            theme_id=themes[0].id,
            attempts_total=12,
            correct_total=10,
            accuracy_pct=83.0,
            mastery_score=0.83,  # Strong
            last_attempt_at=datetime.utcnow() - timedelta(days=2),
            computed_at=datetime.utcnow(),
            algo_version_id=revision_algo_version.id,
            params_id=uuid4(),
            run_id=uuid4(),
            breakdown_json={},
        )
        db.add(mastery)
        await db.commit()

        result = await generate_revision_queue_v0(db, user_id=student_user.id, trigger="test")

        # Should generate future item, but not due today
        assert result["generated"] >= 1
        assert result["due_today"] == 0

    async def test_idempotent_generation(
        self, db, student_user, block_and_themes, revision_algo_version
    ):
        """Test that regenerating doesn't create duplicates."""
        block, themes = block_and_themes

        mastery = UserThemeMastery(
            id=uuid4(),
            user_id=student_user.id,
            year=1,
            block_id=block.id,
            theme_id=themes[0].id,
            attempts_total=8,
            correct_total=5,
            accuracy_pct=62.5,
            mastery_score=0.625,
            last_attempt_at=datetime.utcnow() - timedelta(days=1),
            computed_at=datetime.utcnow(),
            algo_version_id=revision_algo_version.id,
            params_id=uuid4(),
            run_id=uuid4(),
            breakdown_json={},
        )
        db.add(mastery)
        await db.commit()

        # Generate first time
        result1 = await generate_revision_queue_v0(db, user_id=student_user.id, trigger="test")

        # Count records
        stmt = select(RevisionQueue).where(RevisionQueue.user_id == student_user.id)
        queue_result = await db.execute(stmt)
        count1 = len(queue_result.scalars().all())

        # Generate again
        result2 = await generate_revision_queue_v0(db, user_id=student_user.id, trigger="test")

        # Count again
        queue_result = await db.execute(stmt)
        count2 = len(queue_result.scalars().all())

        # Should be same count (upsert, not insert)
        assert count1 == count2
        assert result2["generated"] == result1["generated"]

    async def test_status_protection(
        self, db, student_user, block_and_themes, revision_algo_version
    ):
        """Test that DONE status is not overwritten."""
        block, themes = block_and_themes

        mastery = UserThemeMastery(
            id=uuid4(),
            user_id=student_user.id,
            year=1,
            block_id=block.id,
            theme_id=themes[0].id,
            attempts_total=8,
            correct_total=5,
            accuracy_pct=62.5,
            mastery_score=0.625,
            last_attempt_at=datetime.utcnow() - timedelta(days=1),
            computed_at=datetime.utcnow(),
            algo_version_id=revision_algo_version.id,
            params_id=uuid4(),
            run_id=uuid4(),
            breakdown_json={},
        )
        db.add(mastery)
        await db.commit()

        # Generate queue
        await generate_revision_queue_v0(db, user_id=student_user.id, trigger="test")

        # Mark as DONE
        stmt = select(RevisionQueue).where(
            RevisionQueue.user_id == student_user.id,
            RevisionQueue.theme_id == themes[0].id,
        )
        queue_result = await db.execute(stmt)
        item = queue_result.scalar_one()
        item.status = "DONE"
        await db.commit()

        # Regenerate
        await generate_revision_queue_v0(db, user_id=student_user.id, trigger="test")

        # Verify status still DONE
        queue_result = await db.execute(stmt)
        item = queue_result.scalar_one()
        assert item.status == "DONE"


class TestAlgoRunLogging:
    """Test algo run logging for revision."""

    async def test_run_logging_on_success(
        self, db, student_user, block_and_themes, revision_algo_version
    ):
        """Test that successful generation logs a run."""
        from app.models.learning import AlgoRun

        block, themes = block_and_themes

        mastery = UserThemeMastery(
            id=uuid4(),
            user_id=student_user.id,
            year=1,
            block_id=block.id,
            theme_id=themes[0].id,
            attempts_total=8,
            correct_total=5,
            accuracy_pct=62.5,
            mastery_score=0.625,
            last_attempt_at=datetime.utcnow() - timedelta(days=1),
            computed_at=datetime.utcnow(),
            algo_version_id=revision_algo_version.id,
            params_id=uuid4(),
            run_id=uuid4(),
            breakdown_json={},
        )
        db.add(mastery)
        await db.commit()

        # Generate
        result = await generate_revision_queue_v0(db, user_id=student_user.id, trigger="test")
        run_id = result["run_id"]

        # Verify run exists
        run = await db.get(AlgoRun, run_id)
        assert run is not None
        assert run.user_id == student_user.id
        assert run.status == "SUCCESS"
        assert run.completed_at is not None
        assert run.output_summary_json["generated"] >= 1
