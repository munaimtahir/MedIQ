"""Tests for authentication login endpoint."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
async def test_login_success(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test successful login returns access token and correct shape."""
    # Create test user
    user = create_test_student(
        db,
        email="test_student@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Login request
    response = await async_client.post(
        "/v1/auth/login",
        json={
            "email": "test_student@example.com",
            "password": "TestPass123!",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "user" in data
    assert "tokens" in data
    assert data["tokens"]["access_token"] is not None
    assert data["tokens"]["token_type"] == "bearer"
    
    # Check user data
    assert data["user"]["id"] == str(user.id)
    assert data["user"]["email"] == user.email
    assert data["user"]["role"] == user.role


@pytest.mark.asyncio
async def test_login_failure_invalid_credentials(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test login failure with invalid credentials returns 401 with stable error code."""
    # Create test user
    create_test_student(
        db,
        email="test_student@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Login with wrong password
    response = await async_client.post(
        "/v1/auth/login",
        json={
            "email": "test_student@example.com",
            "password": "WrongPassword123!",
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    
    # Check error structure
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "message" in data["error"]


@pytest.mark.asyncio
async def test_login_failure_nonexistent_user(
    async_client: AsyncClient,
) -> None:
    """Test login failure with nonexistent user returns 401 (no user enumeration)."""
    # Login with non-existent email
    response = await async_client.post(
        "/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "SomePassword123!",
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    
    # Check error structure (should not reveal if user exists)
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "message" in data["error"]


@pytest.mark.asyncio
async def test_login_failure_inactive_user(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test login failure with inactive user returns 403."""
    # Create inactive user
    user = create_test_student(
        db,
        email="inactive@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=False,  # Inactive
    )
    db.commit()
    
    # Login attempt
    response = await async_client.post(
        "/v1/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "TestPass123!",
        },
    )
    
    assert response.status_code == 403
    data = response.json()
    
    # Check error structure
    assert "error" in data
    assert data["error"]["code"] == "FORBIDDEN"
    assert "message" in data["error"]


@pytest.mark.asyncio
async def test_login_failure_unverified_email(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test login failure with unverified email returns 403."""
    # Create unverified user
    user = create_test_student(
        db,
        email="unverified@example.com",
        password="TestPass123!",
        email_verified=False,  # Not verified
        is_active=True,
    )
    db.commit()
    
    # Login attempt
    response = await async_client.post(
        "/v1/auth/login",
        json={
            "email": "unverified@example.com",
            "password": "TestPass123!",
        },
    )
    
    assert response.status_code == 403
    data = response.json()
    
    # Check error structure
    assert "error" in data
    assert data["error"]["code"] == "EMAIL_NOT_VERIFIED"
    assert "message" in data["error"]


@pytest.mark.asyncio
async def test_login_failure_missing_fields(
    async_client: AsyncClient,
) -> None:
    """Test login failure with missing required fields returns 422."""
    # Missing email
    response = await async_client.post(
        "/v1/auth/login",
        json={
            "password": "TestPass123!",
        },
    )
    assert response.status_code == 422
    
    # Missing password
    response = await async_client.post(
        "/v1/auth/login",
        json={
            "email": "test@example.com",
        },
    )
    assert response.status_code == 422
