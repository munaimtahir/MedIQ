"""Tests for refresh token endpoint."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_refresh_token, hash_token
from app.models.auth import RefreshToken
from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
async def test_refresh_token_success(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test successful token refresh returns new tokens."""
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
    
    # Refresh tokens
    refresh_response = await async_client.post(
        "/v1/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )
    
    assert refresh_response.status_code == 200
    data = refresh_response.json()
    
    # Check response structure
    assert "tokens" in data
    assert data["tokens"]["access_token"] is not None
    assert data["tokens"]["refresh_token"] is not None
    assert data["tokens"]["token_type"] == "bearer"
    
    # Verify new tokens are different
    assert data["tokens"]["access_token"] != login_data["tokens"]["access_token"]
    assert data["tokens"]["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_refresh_token_invalid_token(
    async_client: AsyncClient,
) -> None:
    """Test refresh with invalid token returns 401."""
    response = await async_client.post(
        "/v1/auth/refresh",
        json={
            "refresh_token": "invalid_token_here",
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test that reusing a refresh token revokes the session."""
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
    
    # First refresh (should succeed)
    refresh_response1 = await async_client.post(
        "/v1/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )
    assert refresh_response1.status_code == 200
    
    # Try to reuse the old refresh token (should fail and revoke session)
    refresh_response2 = await async_client.post(
        "/v1/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )
    
    assert refresh_response2.status_code == 401
    data = refresh_response2.json()
    assert "error" in data
    assert "REFRESH_TOKEN_REUSE" in data["error"]["code"] or "UNAUTHORIZED" in data["error"]["code"]


@pytest.mark.asyncio
async def test_refresh_token_expired(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test refresh with expired token returns 401."""
    # Create test user
    user = create_test_student(
        db,
        email="test_student@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Create an expired refresh token manually
    from datetime import UTC, datetime, timedelta
    from app.core.security import hash_token
    
    expired_token = create_refresh_token()
    token_hash = hash_token(expired_token)
    
    expired_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired
    )
    db.add(expired_refresh_token)
    db.commit()
    
    # Try to refresh with expired token
    response = await async_client.post(
        "/v1/auth/refresh",
        json={
            "refresh_token": expired_token,
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] in ["UNAUTHORIZED", "TOKEN_EXPIRED"]
