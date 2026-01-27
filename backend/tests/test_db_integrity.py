"""Tests for DB-level integrity constraints and idempotent handling."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.main import app
from app.models.question_cms import Question, QuestionStatus
from app.models.session import (
    AttemptEvent,
    SessionAnswer,
    SessionMode,
    SessionQuestion,
    SessionStatus,
    TestSession,
)
from app.models.syllabus import Block, Theme, Year
from app.models.user import User, UserRole
from app.services.session_engine import process_answer, submit_session


@pytest.fixture
def admin_user(db: Session) -> User:
    u = User(
        id=uuid.uuid4(),
        email="admin-db@test.local",
        role=UserRole.ADMIN.value,
        password_hash="dummy",
        is_active=True,
        email_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def student_user(db: Session) -> User:
    u = User(
        id=uuid.uuid4(),
        email="student-db@test.local",
        role=UserRole.STUDENT.value,
        password_hash="dummy",
        is_active=True,
        email_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def client(db: Session, student_user: User):
    from app.core.dependencies import get_current_user
    from app.db.session import get_db

    def override_get_db():
        yield db

    def override_get_current_user(_: Request) -> User:
        return student_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        # Use TestClient without context manager to avoid lifespan issues
        c = TestClient(app)
        yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def session_with_questions(db: Session, student_user: User):
    """Create a test session with questions."""
    year = db.query(Year).filter(Year.id == 1).first()
    block = db.query(Block).filter(Block.id == 1).first()
    theme = db.query(Theme).filter(Theme.id == 1).first()
    if not all([year, block, theme]):
        pytest.skip("conftest year/block/theme missing")

    qs = []
    for i in range(5):
        q = Question(
            id=uuid.uuid4(),
            status=QuestionStatus.PUBLISHED,
            year_id=1,
            block_id=1,
            theme_id=1,
            stem=f"Q{i+1}",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            option_e="E",
            correct_index=0,
            explanation_md="X",
            difficulty="MEDIUM",
            cognitive_level="UNDERSTAND",
            created_by=student_user.id,
            updated_by=student_user.id,
        )
        db.add(q)
        qs.append(q)
    db.flush()

    sess = TestSession(
        id=uuid.uuid4(),
        user_id=student_user.id,
        mode=SessionMode.TUTOR,
        status=SessionStatus.ACTIVE,
        year=1,
        blocks_json=["A"],
        themes_json=None,
        total_questions=5,
        started_at=datetime.utcnow(),
    )
    db.add(sess)
    db.flush()

    for i, q in enumerate(qs):
        sq = SessionQuestion(
            session_id=sess.id,
            position=i + 1,
            question_id=q.id,
            snapshot_json={
                "stem": q.stem,
                "option_a": "A",
                "option_b": "B",
                "option_c": "C",
                "option_d": "D",
                "option_e": "E",
                "correct_index": 0,
                "explanation_md": "X",
            },
        )
        db.add(sq)
    db.commit()
    db.refresh(sess)
    return sess, qs


class TestSubmitIdempotent:
    """Second submit returns 200 with existing result, no duplicates."""

    def test_double_submit_idempotent(self, client: TestClient, session_with_questions):
        """Submit twice: both 200, single submit (idempotent)."""
        sess, _ = session_with_questions
        r1 = client.post(f"/v1/sessions/{sess.id}/submit")
        assert r1.status_code == 200
        r2 = client.post(f"/v1/sessions/{sess.id}/submit")
        assert r2.status_code == 200
        data1 = r1.json()
        data2 = r2.json()
        assert data1.get("submitted_at") == data2.get("submitted_at")


class TestDuplicateAnswerIdempotent:
    """Duplicate answer insert → IntegrityError handled, return 200 with existing."""

    @pytest.mark.asyncio
    async def test_process_answer_integrity_error_returns_existing(self, db_session: AsyncSession):
        """When commit raises IntegrityError (duplicate), we rollback, refetch, return existing (idempotent)."""
        # Create session and questions in async session
        from app.models.user import User, UserRole
        from app.core.security import hash_password
        from uuid import uuid4
        
        # Use unique email to avoid conflicts with other fixtures
        unique_id = uuid4()
        student_user = User(
            id=unique_id,
            email=f"student_{unique_id}@test.com",
            password_hash=hash_password("Test123!"),
            full_name="Test Student",
            role=UserRole.STUDENT.value,
            is_active=True,
            email_verified=True,
        )
        db_session.add(student_user)
        await db_session.flush()
        
        # Create session and questions
        sess = TestSession(
            id=uuid4(),
            user_id=student_user.id,
            mode=SessionMode.TUTOR,
            status=SessionStatus.ACTIVE,
            year=1,
            blocks_json=["A"],
            total_questions=5,
            started_at=datetime.now(UTC),
        )
        db_session.add(sess)
        
        qs = []
        for i in range(5):
            q = Question(
                id=uuid4(),
                status=QuestionStatus.PUBLISHED,
                year_id=1,
                block_id=1,
                theme_id=1,
                stem=f"Q{i+1}",
                option_a="A",
                option_b="B",
                option_c="C",
                option_d="D",
                option_e="E",
                correct_index=0,
                explanation_md="X",
                difficulty="MEDIUM",
                cognitive_level="UNDERSTAND",
                created_by=student_user.id,
                updated_by=student_user.id,
            )
            db_session.add(q)
            qs.append(q)
            
            sq = SessionQuestion(
                session_id=sess.id,
                question_id=q.id,
                position=i+1,
            )
            db_session.add(sq)
        
        await db_session.commit()
        await db_session.refresh(sess)
        
        q = qs[0]

        # Pre-insert in same session so refetch can see it. We mock commit to raise;
        # we mock rollback to no-op so we don't undo the pre-insert, then refetch sees it.
        existing = SessionAnswer(
            session_id=sess.id,
            question_id=q.id,
            selected_index=1,
            is_correct=False,
            answered_at=datetime.utcnow(),
            changed_count=0,
        )
        db_session.add(existing)
        await db_session.commit()
        await db_session.refresh(existing)

        async def _run():
            with patch.object(db_session, "commit", side_effect=IntegrityError("stmt", "params", None)):
                with patch.object(db_session, "rollback"):  # no-op so pre-insert stays
                    return await process_answer(db_session, sess, q.id, 0, False)

        out = await _run()
        assert out is not None
        assert out.session_id == sess.id and out.question_id == q.id
        assert out.selected_index == 1  # existing; our update was rolled back


class TestTelemetryAppendOnly:
    """attempt_events: UPDATE/DELETE forbidden by trigger."""

    def test_attempt_events_update_raises(self, db: Session, session_with_questions):
        """UPDATE on attempt_events raises (append-only)."""
        sess, _ = session_with_questions
        ev = AttemptEvent(
            session_id=sess.id,
            user_id=sess.user_id,
            event_type="QUESTION_VIEWED",
            event_ts=datetime.utcnow(),
            payload_json={},
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)

        with pytest.raises(Exception):
            with db.get_bind().connect() as conn:
                conn.execute(text("UPDATE attempt_events SET event_type = 'X' WHERE id = :id"), {"id": str(ev.id)})
                conn.commit()

    def test_attempt_events_delete_raises(self, db: Session, session_with_questions):
        """DELETE on attempt_events raises (append-only)."""
        sess, _ = session_with_questions
        ev = AttemptEvent(
            session_id=sess.id,
            user_id=sess.user_id,
            event_type="QUESTION_VIEWED",
            event_ts=datetime.utcnow(),
            payload_json={},
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)

        with pytest.raises(Exception):
            with db.get_bind().connect() as conn:
                conn.execute(text("DELETE FROM attempt_events WHERE id = :id"), {"id": str(ev.id)})
                conn.commit()
