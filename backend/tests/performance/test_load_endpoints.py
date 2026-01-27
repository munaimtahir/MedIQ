"""Load tests for critical endpoints using pytest with concurrent requests."""

import asyncio
import time
from typing import List

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_login_requests(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test login endpoint under concurrent load."""
    # Create test user
    user = create_test_student(
        db,
        email="load_test@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Make concurrent login requests
    async def login_request(index: int) -> dict:
        response = await async_client.post(
            "/v1/auth/login",
            json={
                "email": "load_test@example.com",
                "password": "TestPass123!",
            },
        )
        return {
            "index": index,
            "status": response.status_code,
            "response_time": response.elapsed.total_seconds(),
        }
    
    # Run 10 concurrent requests
    start_time = time.time()
    results = await asyncio.gather(*[login_request(i) for i in range(10)])
    end_time = time.time()
    
    # Verify all succeeded
    assert all(r["status"] == 200 for r in results)
    
    # Verify response times are reasonable (< 2 seconds each)
    assert all(r["response_time"] < 2.0 for r in results)
    
    # Verify total time is reasonable (concurrent should be faster than sequential)
    total_time = end_time - start_time
    assert total_time < 5.0  # 10 requests should complete in < 5 seconds


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_session_creation(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test session creation under concurrent load."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    async def create_session(index: int) -> dict:
        start = time.time()
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
        elapsed = time.time() - start
        
        return {
            "index": index,
            "status": response.status_code,
            "response_time": elapsed,
            "session_id": response.json().get("session_id") if response.status_code == 200 else None,
        }
    
    # Run 5 concurrent session creations
    start_time = time.time()
    results = await asyncio.gather(*[create_session(i) for i in range(5)])
    end_time = time.time()
    
    # Verify all succeeded
    assert all(r["status"] == 200 for r in results)
    
    # Verify all sessions are unique
    session_ids = [r["session_id"] for r in results if r["session_id"]]
    assert len(session_ids) == len(set(session_ids))
    
    # Verify response times
    assert all(r["response_time"] < 3.0 for r in results)
    
    # Verify total time
    total_time = end_time - start_time
    assert total_time < 10.0


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_answer_submissions(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test answer submission under concurrent load."""
    from app.models.session import TestSession, SessionQuestion, SessionMode, SessionStatus
    from datetime import datetime
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
        total_questions=5,
        status=SessionStatus.ACTIVE,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    
    # Add questions
    for i, question in enumerate(published_questions[:5], 1):
        session_question = SessionQuestion(
            session_id=session_id,
            question_id=question.id,
            position=i,
        )
        db.add(session_question)
    
    db.commit()
    
    # Submit answers concurrently
    async def submit_answer(index: int) -> dict:
        question = published_questions[index % 5]
        start = time.time()
        response = await async_client.post(
            f"/v1/sessions/{session_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "question_id": str(question.id),
                "selected_index": 0,
            },
        )
        elapsed = time.time() - start
        
        return {
            "index": index,
            "status": response.status_code,
            "response_time": elapsed,
        }
    
    # Run 10 concurrent answer submissions
    start_time = time.time()
    results = await asyncio.gather(*[submit_answer(i) for i in range(10)])
    end_time = time.time()
    
    # Most should succeed (some may fail due to concurrency, but that's expected)
    success_count = sum(1 for r in results if r["status"] == 200)
    assert success_count >= 5  # At least half should succeed
    
    # Verify response times
    successful = [r for r in results if r["status"] == 200]
    if successful:
        assert all(r["response_time"] < 2.0 for r in successful)
    
    # Verify total time
    total_time = end_time - start_time
    assert total_time < 5.0


@pytest.mark.asyncio
@pytest.mark.performance
async def test_endpoint_response_time_health_check(
    async_client: AsyncClient,
) -> None:
    """Test that health check endpoint responds quickly."""
    start = time.time()
    response = await async_client.get("/health")
    elapsed = time.time() - start
    
    assert response.status_code == 200
    # Health check should be very fast
    assert elapsed < 0.5  # Should respond in < 500ms
