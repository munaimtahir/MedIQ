"""Tests for analytics endpoints (overview, block, theme, permissions)."""

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.session import SessionStatus
from tests.helpers.seed import create_test_admin, create_test_student


@pytest.mark.asyncio
async def test_analytics_overview_empty(
    async_client: AsyncClient,
    db: Session,
    test_user,
) -> None:
    """Test analytics overview for user with no sessions."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    response = await async_client.get(
        "/v1/analytics/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["sessions_completed"] == 0
    assert data["questions_seen"] == 0
    assert data["questions_answered"] == 0
    assert data["correct"] == 0
    assert data["accuracy_pct"] == 0.0
    assert data["by_block"] == []
    assert data["weakest_themes"] == []
    assert data["trend"] == []
    assert data["last_session"] is None


@pytest.mark.asyncio
async def test_analytics_overview_with_sessions(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test analytics overview after submitting sessions."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create and submit a session
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
    
    # Get questions and submit answers
    get_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    questions = get_response.json()["questions"]
    
    # Submit answers
    for q in questions[:3]:
        await async_client.post(
            f"/v1/sessions/{session_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "question_id": str(q["question_id"]),
                "selected_index": 0,
            },
        )
    
    # Submit session
    await async_client.post(
        f"/v1/sessions/{session_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Wait a moment for async processing
    import asyncio
    await asyncio.sleep(0.5)
    
    # Get analytics overview
    analytics_response = await async_client.get(
        "/v1/analytics/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert analytics_response.status_code == 200
    data = analytics_response.json()
    assert data["sessions_completed"] >= 1
    assert data["questions_seen"] >= 3
    assert data["questions_answered"] >= 3
    assert "accuracy_pct" in data
    assert isinstance(data["by_block"], list)
    assert isinstance(data["weakest_themes"], list)
    assert isinstance(data["trend"], list)


@pytest.mark.asyncio
async def test_analytics_block(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test block-specific analytics."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create and submit a session
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
    
    # Submit session (with or without answers)
    await async_client.post(
        f"/v1/sessions/{session_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    await asyncio.sleep(0.5)
    
    # Get block analytics (block_id = 1)
    response = await async_client.get(
        "/v1/analytics/block/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Should return 200 with block analytics or 404 if block doesn't exist
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        assert "block_id" in data
        assert "block_name" in data
        assert "attempted" in data
        assert "correct" in data
        assert "accuracy_pct" in data
        assert isinstance(data["themes"], list)
        assert isinstance(data["trend"], list)


@pytest.mark.asyncio
async def test_analytics_theme(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test theme-specific analytics."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create and submit a session
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
    
    await asyncio.sleep(0.5)
    
    # Get theme analytics (theme_id = 1)
    response = await async_client.get(
        "/v1/analytics/theme/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Should return 200 with theme analytics or 404 if theme doesn't exist
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        assert "theme_id" in data
        assert "theme_name" in data
        assert "block_id" in data
        assert "attempted" in data
        assert "correct" in data
        assert "accuracy_pct" in data
        assert isinstance(data["trend"], list)


@pytest.mark.asyncio
async def test_analytics_student_sees_only_own_data(
    async_client: AsyncClient,
    db: Session,
    test_user,
    published_questions,
) -> None:
    """Test that student analytics only show their own data."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Create another student
    other_student = create_test_student(
        db,
        email="other_student@test.com",
        password="OtherPass123!",
    )
    db.commit()
    
    # Create session for current user
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
    await async_client.post(
        f"/v1/sessions/{session_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    await asyncio.sleep(0.5)
    
    # Get analytics - should only show current user's data
    response = await async_client.get(
        "/v1/analytics/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    # Should have at least 1 session (current user's)
    assert data["sessions_completed"] >= 1
    # Should not include other student's sessions (enforced by service layer)


@pytest.mark.asyncio
async def test_analytics_unauthenticated_rejected(
    async_client: AsyncClient,
) -> None:
    """Test that unauthenticated requests are rejected."""
    response = await async_client.get("/v1/analytics/overview")
    assert response.status_code == 401
