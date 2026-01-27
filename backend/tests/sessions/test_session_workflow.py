"""Tests for session workflow (create, answer, submit, idempotency, concurrency)."""

import asyncio
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.session import SessionStatus
from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
async def test_create_session(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test creating a session (student)."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 5,
            "duration_seconds": 3600,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == SessionStatus.ACTIVE.value
    assert data["total_questions"] == 5
    assert data["session_id"] is not None
    assert data["progress"]["answered_count"] == 0
    assert data["progress"]["current_position"] == 1


@pytest.mark.asyncio
async def test_get_session_state(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test fetching session state with current question."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create session
    create_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 5,
        },
    )
    session_id = create_response.json()["session_id"]
    
    # Get session state
    get_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["session"]["id"] == str(session_id)
    assert data["session"]["status"] == SessionStatus.ACTIVE.value
    assert len(data["questions"]) == 5
    assert data["current_question"] is not None
    assert data["current_question"]["stem"] is not None
    # Should not include correct answer or explanation
    assert "correct_index" not in data["current_question"]
    assert "explanation" not in data["current_question"]


@pytest.mark.asyncio
async def test_submit_answer(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test submitting an answer for a question."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create session
    create_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 5,
        },
    )
    session_id = create_response.json()["session_id"]
    
    # Get session to find question ID
    get_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    question_id = get_response.json()["current_question"]["question_id"]
    
    # Submit answer
    answer_response = await async_client.post(
        f"/v1/sessions/{session_id}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": str(question_id),
            "selected_index": 0,
            "marked_for_review": False,
        },
    )
    
    assert answer_response.status_code == 200
    data = answer_response.json()
    assert data["answer"]["selected_index"] == 0
    assert data["answer"]["is_correct"] is not None  # Should be computed
    assert data["progress"]["answered_count"] == 1


@pytest.mark.asyncio
async def test_submit_session(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test submitting a session and verify scoring."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create session
    create_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 3,
        },
    )
    session_id = create_response.json()["session_id"]
    
    # Get session and submit answers for all questions
    get_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    questions = get_response.json()["questions"]
    
    # Submit answers (all correct for simplicity)
    for q in questions[:3]:
        await async_client.post(
            f"/v1/sessions/{session_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "question_id": str(q["question_id"]),
                "selected_index": 0,  # Assume first option is correct
                "marked_for_review": False,
            },
        )
    
    # Submit session
    submit_response = await async_client.post(
        f"/v1/sessions/{session_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert submit_response.status_code == 200
    data = submit_response.json()
    assert data["session"]["status"] == SessionStatus.SUBMITTED.value
    assert data["session"]["score_total"] == 3
    assert data["session"]["score_correct"] is not None
    assert data["session"]["score_pct"] is not None
    assert 0 <= data["session"]["score_pct"] <= 100


@pytest.mark.asyncio
async def test_submit_session_idempotency(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test that re-submitting a session is idempotent (safe no-op)."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create and submit session
    create_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 3,
        },
    )
    session_id = create_response.json()["session_id"]
    
    # Submit session first time
    submit1_response = await async_client.post(
        f"/v1/sessions/{session_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submit1_response.status_code == 200
    score1 = submit1_response.json()["session"]["score_correct"]
    
    # Submit session second time (should be idempotent)
    submit2_response = await async_client.post(
        f"/v1/sessions/{session_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submit2_response.status_code == 200
    score2 = submit2_response.json()["session"]["score_correct"]
    
    # Scores should be the same (idempotent)
    assert score1 == score2
    assert submit2_response.json()["session"]["status"] == SessionStatus.SUBMITTED.value


@pytest.mark.asyncio
async def test_cannot_submit_after_session_ended(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test that cannot submit answer after session is submitted."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create session
    create_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 3,
        },
    )
    session_id = create_response.json()["session_id"]
    
    # Submit session
    await async_client.post(
        f"/v1/sessions/{session_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Try to submit answer after session is submitted (should fail)
    get_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    question_id = get_response.json()["questions"][0]["question_id"]
    
    answer_response = await async_client.post(
        f"/v1/sessions/{session_id}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": str(question_id),
            "selected_index": 0,
        },
    )
    
    # Should return 400 (session not active)
    assert answer_response.status_code == 400


@pytest.mark.asyncio
async def test_concurrent_answer_submission(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test concurrent answer submissions for same question (only one should apply)."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create session
    create_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 3,
        },
    )
    session_id = create_response.json()["session_id"]
    
    # Get question ID
    get_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    question_id = get_response.json()["current_question"]["question_id"]
    
    # Submit same answer concurrently
    async def submit_answer(index: int) -> dict:
        response = await async_client.post(
            f"/v1/sessions/{session_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "question_id": str(question_id),
                "selected_index": index,
            },
        )
        return response.json()
    
    # Submit with different indices concurrently
    results = await asyncio.gather(
        submit_answer(0),
        submit_answer(1),
        submit_answer(2),
    )
    
    # All should succeed (last write wins or idempotent)
    assert all(r.get("answer") is not None for r in results)
    
    # Verify only one answer exists in DB
    from app.models.session import SessionAnswer
    
    answers = db.query(SessionAnswer).filter(
        SessionAnswer.session_id == session_id,
        SessionAnswer.question_id == question_id,
    ).all()
    
    # Should have exactly one answer (concurrent writes handled by DB unique constraint)
    assert len(answers) == 1


@pytest.mark.asyncio
async def test_session_state_transitions(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test session state transitions correctly (ACTIVE -> SUBMITTED)."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create session (should be ACTIVE)
    create_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 3,
        },
    )
    session_id = create_response.json()["session_id"]
    
    # Verify ACTIVE
    get_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.json()["session"]["status"] == SessionStatus.ACTIVE.value
    
    # Submit session (should transition to SUBMITTED)
    await async_client.post(
        f"/v1/sessions/{session_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Verify SUBMITTED
    get_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.json()["session"]["status"] == SessionStatus.SUBMITTED.value
    assert get_response.json()["session"]["submitted_at"] is not None


@pytest.mark.asyncio
async def test_session_expiry_handling(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test that expired sessions are auto-submitted on access."""
    from datetime import datetime, timedelta
    from app.models.session import TestSession, SessionQuestion
    from uuid import uuid4
    
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create session with expiry in the past
    from app.models.session import SessionMode
    
    session_id = uuid4()
    expired_session = TestSession(
        id=session_id,
        user_id=test_user.id,
        mode=SessionMode.TUTOR,
        year=1,
        blocks_json=["A"],
        total_questions=3,
        status=SessionStatus.ACTIVE,
        started_at=datetime.utcnow() - timedelta(hours=2),
        expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        duration_seconds=3600,
    )
    db.add(expired_session)
    
    # Add questions to session
    for i, question in enumerate(published_questions[:3], 1):
        session_question = SessionQuestion(
            session_id=session_id,
            question_id=question.id,
            position=i,
        )
        db.add(session_question)
    
    db.commit()
    
    # Try to get session state (should auto-expire)
    get_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert get_response.status_code == 200
    data = get_response.json()
    # Session should be auto-submitted (EXPIRED status)
    assert data["session"]["status"] in (SessionStatus.EXPIRED.value, SessionStatus.SUBMITTED.value)
    assert data["session"]["submitted_at"] is not None
    
    # Try to submit answer after expiry (should fail)
    question_id = published_questions[0].id
    answer_response = await async_client.post(
        f"/v1/sessions/{session_id}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": str(question_id),
            "selected_index": 0,
        },
    )
    
    # Should return 400 (session not active)
    assert answer_response.status_code == 400


@pytest.mark.asyncio
async def test_concurrent_session_creation(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test that concurrent session creation works correctly."""
    import asyncio
    
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create multiple sessions concurrently
    async def create_session(index: int) -> dict:
        response = await async_client.post(
            "/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "mode": "TUTOR",
                "year": 1,
                "blocks": ["A"],
                "count": 3,
            },
        )
        return response.json()
    
    # Create 5 sessions concurrently
    results = await asyncio.gather(
        create_session(1),
        create_session(2),
        create_session(3),
        create_session(4),
        create_session(5),
    )
    
    # All should succeed
    assert all(r.get("session_id") is not None for r in results)
    assert all(r.get("status") == SessionStatus.ACTIVE.value for r in results)
    
    # Verify all sessions are unique
    session_ids = [r["session_id"] for r in results]
    assert len(session_ids) == len(set(session_ids)), "All sessions should have unique IDs"
    
    # Verify all sessions belong to the same user
    from app.models.session import TestSession
    
    for session_id in session_ids:
        session = db.query(TestSession).filter(TestSession.id == session_id).first()
        assert session is not None
        assert session.user_id == test_user.id
