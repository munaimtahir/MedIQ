"""Tests for token revocation (logout)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import verify_access_token
from app.models.auth import AuthSession, RefreshToken
from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
async def test_logout_success(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test successful logout revokes refresh token."""
    # Create test user
    user = create_test_student(
        db,
        email="test_student@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Login to get tokens
    login_response = await async_client.post(
        "/v1/auth/login",
        json={
            "email": "test_student@example.com",
            "password": "TestPass123!",
        },
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    refresh_token = login_data["tokens"]["refresh_token"]
    
    # Logout
    logout_response = await async_client.post(
        "/v1/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )
    
    assert logout_response.status_code == 200
    data = logout_response.json()
    assert data["status"] == "ok"
    
    # Verify refresh token is revoked
    db.refresh(user)
    token_record = db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.token_hash.isnot(None),
    ).first()
    
    if token_record:
        assert token_record.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_all_success(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test logout-all revokes all refresh tokens for user."""
    # Create test user
    user = create_test_student(
        db,
        email="test_student@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Login to get tokens
    login_response = await async_client.post(
        "/v1/auth/login",
        json={
            "email": "test_student@example.com",
            "password": "TestPass123!",
        },
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    access_token = login_data["tokens"]["access_token"]
    
    # Logout all
    logout_all_response = await async_client.post(
        "/v1/auth/logout-all",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )
    
    assert logout_all_response.status_code == 200
    data = logout_all_response.json()
    assert data["status"] == "ok"
    
    # Verify all refresh tokens are revoked
    db.refresh(user)
    active_tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).all()
    assert len(active_tokens) == 0


@pytest.mark.asyncio
async def test_logout_invalid_token(
    async_client: AsyncClient,
) -> None:
    """Test logout with invalid token still returns success (idempotent)."""
    response = await async_client.post(
        "/v1/auth/logout",
        json={
            "refresh_token": "invalid_token_here",
        },
    )
    
    # Logout is idempotent - should return success even for invalid tokens
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_logout_all_requires_authentication(
    async_client: AsyncClient,
) -> None:
    """Test logout-all requires authentication."""
    response = await async_client.post(
        "/v1/auth/logout-all",
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
