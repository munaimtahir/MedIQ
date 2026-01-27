"""Tests for permission boundaries and RBAC."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from tests.helpers.seed import create_test_student, create_test_admin


@pytest.mark.asyncio
async def test_student_cannot_access_admin_endpoints(
    async_client: AsyncClient,
    db: Session,
    test_user,
) -> None:
    """Test that students cannot access admin-only endpoints."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Try to access admin questions endpoint
    response = await async_client.get(
        "/v1/admin/questions",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Should be forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_admin_endpoints(
    async_client: AsyncClient,
    db: Session,
    test_admin_user,
) -> None:
    """Test that admins can access admin-only endpoints."""
    token = create_access_token(user_id=str(test_admin_user.id), role=test_admin_user.role)
    
    # Access admin questions endpoint
    response = await async_client.get(
        "/v1/admin/questions",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Should succeed
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_student_cannot_create_questions(
    async_client: AsyncClient,
    db: Session,
    test_user,
) -> None:
    """Test that students cannot create questions via CMS."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Try to create a question
    response = await async_client.post(
        "/v1/admin/questions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "stem": "Test question",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "option_e": "E",
            "correct_index": 0,
        },
    )
    
    # Should be forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_access_other_user_sessions(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test that students cannot access other users' sessions."""
    from app.models.session import TestSession, SessionMode
    from datetime import datetime
    from uuid import uuid4
    
    # Create another user
    other_user = create_test_student(
        db,
        email="other_user@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Create a session for the other user
    other_session_id = uuid4()
    other_session = TestSession(
        id=other_session_id,
        user_id=other_user.id,
        mode=SessionMode.TUTOR,
        year=1,
        blocks_json=["A"],
        total_questions=1,
        status="ACTIVE",
        started_at=datetime.utcnow(),
    )
    db.add(other_session)
    db.commit()
    
    # Try to access other user's session with test_user's token
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    response = await async_client.get(
        f"/v1/sessions/{other_session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Should be forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_protected_endpoints(
    async_client: AsyncClient,
) -> None:
    """Test that unauthenticated requests are rejected."""
    # Try to access protected endpoint without token
    response = await async_client.get("/v1/sessions")
    
    # Should be unauthorized
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(
    async_client: AsyncClient,
) -> None:
    """Test that invalid tokens are rejected."""
    # Try to access protected endpoint with invalid token
    response = await async_client.get(
        "/v1/sessions",
        headers={"Authorization": "Bearer invalid_token_here"},
    )
    
    # Should be unauthorized
    assert response.status_code == 401
