"""Integration test: Auth + Session creation flow."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
async def test_login_then_create_session(
    async_client: AsyncClient,
    db: Session,
    published_questions,
) -> None:
    """Test complete flow: login -> create session -> get session state."""
    # Create user
    user = create_test_student(
        db,
        email="integration_test@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Step 1: Login
    login_response = await async_client.post(
        "/v1/auth/login",
        json={
            "email": "integration_test@example.com",
            "password": "TestPass123!",
        },
    )
    
    assert login_response.status_code == 200
    login_data = login_response.json()
    access_token = login_data["tokens"]["access_token"]
    
    # Step 2: Create session using token from login
    session_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 5,
        },
    )
    
    assert session_response.status_code == 200
    session_data = session_response.json()
    session_id = session_data["session_id"]
    
    # Step 3: Get session state
    state_response = await async_client.get(
        f"/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    
    assert state_response.status_code == 200
    state_data = state_response.json()
    assert state_data["session"]["id"] == str(session_id)
    assert len(state_data["questions"]) == 5


@pytest.mark.asyncio
async def test_refresh_token_then_create_session(
    async_client: AsyncClient,
    db: Session,
    published_questions,
) -> None:
    """Test flow: login -> refresh token -> create session."""
    # Create user
    user = create_test_student(
        db,
        email="refresh_integration@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Step 1: Login
    login_response = await async_client.post(
        "/v1/auth/login",
        json={
            "email": "refresh_integration@example.com",
            "password": "TestPass123!",
        },
    )
    
    assert login_response.status_code == 200
    login_data = login_response.json()
    refresh_token = login_data["tokens"]["refresh_token"]
    
    # Step 2: Refresh token
    refresh_response = await async_client.post(
        "/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    new_access_token = refresh_data["tokens"]["access_token"]
    
    # Step 3: Create session with new token
    session_response = await async_client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {new_access_token}"},
        json={
            "mode": "TUTOR",
            "year": 1,
            "blocks": ["A"],
            "count": 3,
        },
    )
    
    assert session_response.status_code == 200
    session_data = session_response.json()
    assert session_data["session_id"] is not None
