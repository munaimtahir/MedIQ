"""Property-based tests for session invariants."""

import math
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings, strategies as st
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.session import SessionAnswer, SessionQuestion, SessionStatus, TestSession
from app.services.session_engine import check_and_expire_session, process_answer, submit_session
from tests.helpers.seed import create_test_student


@settings(max_examples=50, deadline=None, print_blob=True)
@given(
    num_questions=st.integers(min_value=1, max_value=20),
    num_answers=st.integers(min_value=0, max_value=20),
)
@pytest.mark.asyncio
async def test_session_state_machine_validity(
    db: Session,
    db_session: AsyncSession,
    num_questions: int,
    num_answers: int,
) -> None:
    """
    Property: Session state machine transitions are valid.

    Invariants:
    - ACTIVE -> SUBMITTED/EXPIRED (cannot go backwards)
    - Cannot submit answer after session ended
    - Cannot submit session twice (idempotent)
    """
    # Create test user
    user = create_test_student(db, email="test_student@example.com")
    db.commit()

    # Create session with questions
    from app.models.question_cms import Question, QuestionStatus
    from app.models.syllabus import Block, Theme, Year

    year = db.query(Year).filter(Year.id == 1).first()
    block = db.query(Block).filter(Block.id == 1).first()
    theme = db.query(Theme).filter(Theme.id == 1).first()

    # Create questions
    questions = []
    for i in range(num_questions):
        q = Question(
            external_id=f"TEST-Q-{i}",
            stem=f"Question {i}",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            option_e="E",
            correct_index=0,
            explanation_md="Explanation",
            status=QuestionStatus.PUBLISHED,
            year_id=year.id,
            block_id=block.id,
            theme_id=theme.id,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(q)
        questions.append(q)
    db.commit()

    # Create session
    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        year=1,
        blocks_json=["A"],
        total_questions=num_questions,
        status=SessionStatus.ACTIVE,
        started_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(session)
    db.flush()

    # Add questions to session
    for i, q in enumerate(questions[:num_questions], 1):
        sq = SessionQuestion(
            session_id=session.id,
            question_id=q.id,
            position=i,
        )
        db.add(sq)
    db.commit()

    # Submit answers (up to num_answers)
    for i in range(min(num_answers, num_questions)):
        q_id = questions[i].id
        answer = await process_answer(
            db_session,
            session,
            q_id,
            selected_index=0,
            marked_for_review=False,
        )
        await db_session.commit()
        db.refresh(session)

        # Invariant: Session must remain ACTIVE after answer submission
        assert session.status == SessionStatus.ACTIVE, "Session must remain ACTIVE after answer"

    # Submit session
    submitted_session = await submit_session(db, session, auto_expired=False)
    db.refresh(submitted_session)

    # Invariant: Status must be SUBMITTED or EXPIRED (not ACTIVE)
    assert submitted_session.status in [
        SessionStatus.SUBMITTED,
        SessionStatus.EXPIRED,
    ], f"Session status must be SUBMITTED or EXPIRED, got {submitted_session.status}"

    # Invariant: Cannot submit answer after session ended
    if num_questions > 0:
        q_id = questions[0].id
        try:
            await process_answer(
                db_session,
                submitted_session,
                q_id,
                selected_index=1,
                marked_for_review=False,
            )
            await db_session.commit()
            pytest.fail("Should not allow answer submission after session ended")
        except Exception as e:
            # Expected: should raise HTTPException with status 400
            assert "not active" in str(e).lower() or "400" in str(e), f"Unexpected error: {e}"

    # Invariant: Re-submitting session is idempotent
    resubmitted = await submit_session(db, submitted_session, auto_expired=False)
    db.refresh(resubmitted)

    # Scores should be the same
    assert resubmitted.score_correct == submitted_session.score_correct
    assert resubmitted.score_total == submitted_session.score_total
    assert resubmitted.status == submitted_session.status


@settings(max_examples=30, deadline=None)
@given(
    question_id=st.uuids(),
    selected_index=st.integers(min_value=0, max_value=4) | st.none(),
)
@pytest.mark.asyncio
async def test_cannot_submit_for_question_not_in_session(
    db: Session,
    db_session: AsyncSession,
    question_id: UUID,
    selected_index: int | None,
) -> None:
    """
    Property: Cannot submit answer for a question that was never served in the session.

    Invariant: process_answer must verify question belongs to session.
    """
    # Create test user and session
    user = create_test_student(db, email="test_student@example.com")
    db.commit()

    from app.models.question_cms import Question, QuestionStatus
    from app.models.syllabus import Block, Theme, Year

    year = db.query(Year).filter(Year.id == 1).first()
    block = db.query(Block).filter(Block.id == 1).first()
    theme = db.query(Theme).filter(Theme.id == 1).first()

    # Create a question that IS in the session
    q_in_session = Question(
        external_id="IN-SESSION",
        stem="Question in session",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        option_e="E",
        correct_index=0,
        explanation_md="Explanation",
        status=QuestionStatus.PUBLISHED,
        year_id=year.id,
        block_id=block.id,
        theme_id=theme.id,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(q_in_session)
    db.commit()

    # Create session with only q_in_session
    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        year=1,
        blocks_json=["A"],
        total_questions=1,
        status=SessionStatus.ACTIVE,
        started_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(session)
    db.flush()

    sq = SessionQuestion(
        session_id=session.id,
        question_id=q_in_session.id,
        position=1,
    )
    db.add(sq)
    db.commit()

    # Try to submit answer for question NOT in session
    if question_id != q_in_session.id:
        try:
            await process_answer(
                db_session,
                session,
                question_id,  # This question is NOT in the session
                selected_index=selected_index,
                marked_for_review=False,
            )
            await db_session.commit()
            pytest.fail(f"Should not allow answer for question {question_id} not in session")
        except Exception as e:
            # Expected: should raise HTTPException
            assert "not found" in str(e).lower() or "400" in str(e) or "404" in str(e), (
                f"Expected error about question not in session, got: {e}"
            )


@settings(max_examples=20, deadline=None)
@given(
    num_submits=st.integers(min_value=1, max_value=5),
    selected_index=st.integers(min_value=0, max_value=4),
)
@pytest.mark.asyncio
async def test_duplicate_submit_idempotency(
    db: Session,
    db_session: AsyncSession,
    num_submits: int,
    selected_index: int,
) -> None:
    """
    Property: Duplicate submit for the same attempt is idempotent (no double mutation).

    Invariant: Submitting the same answer multiple times should not create duplicate answers.
    """
    # Create test user and session
    user = create_test_student(db, email="test_student@example.com")
    db.commit()

    from app.models.question_cms import Question, QuestionStatus
    from app.models.syllabus import Block, Theme, Year

    year = db.query(Year).filter(Year.id == 1).first()
    block = db.query(Block).filter(Block.id == 1).first()
    theme = db.query(Theme).filter(Theme.id == 1).first()

    q = Question(
        external_id="TEST-Q",
        stem="Question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        option_e="E",
        correct_index=0,
        explanation_md="Explanation",
        status=QuestionStatus.PUBLISHED,
        year_id=year.id,
        block_id=block.id,
        theme_id=theme.id,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(q)
    db.commit()

    session = TestSession(
        id=uuid4(),
        user_id=user.id,
        year=1,
        blocks_json=["A"],
        total_questions=1,
        status=SessionStatus.ACTIVE,
        started_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(session)
    db.flush()

    sq = SessionQuestion(
        session_id=session.id,
        question_id=q.id,
        position=1,
    )
    db.add(sq)
    db.commit()

    # Submit answer multiple times
    answers = []
    for _ in range(num_submits):
        answer = await process_answer(
            db_session,
            session,
            q.id,
            selected_index=selected_index,
            marked_for_review=False,
        )
        await db_session.commit()
        db.refresh(session)
        answers.append(answer)

    # Invariant: Should have exactly one answer record
    answer_count = db.query(SessionAnswer).filter(
        SessionAnswer.session_id == session.id,
        SessionAnswer.question_id == q.id,
    ).count()

    assert answer_count == 1, f"Expected 1 answer, got {answer_count} (idempotency violation)"

    # Invariant: All answer objects should reference the same record
    answer_ids = {a.id for a in answers}
    assert len(answer_ids) == 1, f"All submits should return same answer, got IDs: {answer_ids}"
