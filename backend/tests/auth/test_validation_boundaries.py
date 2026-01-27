"""Tests for data validation boundaries."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from tests.helpers.seed import create_test_student, create_test_admin


@pytest.mark.asyncio
async def test_email_validation_boundaries(
    async_client: AsyncClient,
) -> None:
    """Test email validation with boundary cases."""
    # Test empty email
    response = await async_client.post(
        "/v1/auth/register",
        json={
            "email": "",
            "password": "TestPass123!",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 422  # Validation error

    # Test invalid email format
    response = await async_client.post(
        "/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "TestPass123!",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 422

    # Test very long email
    long_email = "a" * 200 + "@example.com"
    response = await async_client.post(
        "/v1/auth/register",
        json={
            "email": long_email,
            "password": "TestPass123!",
            "full_name": "Test User",
        },
    )
    # Should either validate or reject
    assert response.status_code in (422, 400)


@pytest.mark.asyncio
async def test_password_validation_boundaries(
    async_client: AsyncClient,
) -> None:
    """Test password validation with boundary cases."""
    # Test empty password
    response = await async_client.post(
        "/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 422

    # Test too short password
    response = await async_client.post(
        "/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "Short1!",
            "full_name": "Test User",
        },
    )
    # Should validate minimum length
    assert response.status_code in (422, 400)

    # Test very long password
    long_password = "A" * 1000 + "1!"
    response = await async_client.post(
        "/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": long_password,
            "full_name": "Test User",
        },
    )
    # Should either validate or reject
    assert response.status_code in (422, 400)


@pytest.mark.asyncio
async def test_session_count_boundaries(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test session creation with boundary question counts."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Test zero questions
    response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 0,
        },
    )
    assert response.status_code in (400, 422)  # Should reject zero
    
    # Test negative count
    response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": -1,
        },
    )
    assert response.status_code in (400, 422)  # Should reject negative
    
    # Test very large count
    response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 10000,
        },
    )
    # Should either reject or limit to available questions
    assert response.status_code in (200, 400, 422)


@pytest.mark.asyncio
async def test_answer_index_boundaries(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test answer submission with boundary indices."""
    from app.models.session import TestSession, SessionQuestion, SessionMode
    from datetime import datetime, timedelta
    from uuid import uuid4
    
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create a session
    session_id = uuid4()
    session = TestSession(
        id=session_id,
        user_id=test_user.id,
        mode=SessionMode.TUTOR,
        year=1,
        blocks_json=["A"],
        total_questions=1,
        status="ACTIVE",
        started_at=datetime.utcnow(),
    )
    db.add(session)
    
    question = published_questions[0]
    session_question = SessionQuestion(
        session_id=session_id,
        question_id=question.id,
        position=1,
    )
    db.add(session_question)
    db.commit()
    
    # Test negative index
    response = await async_client.post(
        f"/v1/sessions/{session_id}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": str(question.id),
            "selected_index": -1,
        },
    )
    assert response.status_code in (400, 422)  # Should reject negative
    
    # Test index out of range (assuming 5 options: 0-4)
    response = await async_client.post(
        f"/v1/sessions/{session_id}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": str(question.id),
            "selected_index": 10,
        },
    )
    # Should either reject or handle gracefully
    assert response.status_code in (200, 400, 422)
