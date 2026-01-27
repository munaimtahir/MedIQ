"""Tests for password reset flow."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.auth import PasswordResetToken
from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
async def test_password_reset_request_success(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test password reset request returns success (even if user doesn't exist)."""
    # Create test user
    user = create_test_student(
        db,
        email="test_student@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Request password reset
    response = await async_client.post(
        "/v1/auth/password-reset/request",
        json={
            "email": "test_student@example.com",
        },
    )
    
    # Should always return success (security: prevent email enumeration)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    
    # Verify reset token was created
    reset_tokens = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id
    ).all()
    assert len(reset_tokens) > 0


@pytest.mark.asyncio
async def test_password_reset_request_nonexistent_user(
    async_client: AsyncClient,
) -> None:
    """Test password reset request for nonexistent user still returns success."""
    # Request password reset for non-existent user
    response = await async_client.post(
        "/v1/auth/password-reset/request",
        json={
            "email": "nonexistent@example.com",
        },
    )
    
    # Should still return success (security: prevent email enumeration)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_password_reset_confirm_success(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test password reset confirmation with valid token."""
    # Create test user
    user = create_test_student(
        db,
        email="test_student@example.com",
        password="OldPassword123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Create reset token manually
    from datetime import UTC, datetime, timedelta
    from app.core.security import generate_password_reset_token, hash_token
    
    reset_token = generate_password_reset_token()
    token_hash = hash_token(reset_token)
    
    reset_token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(reset_token_record)
    db.commit()
    
    # Confirm password reset
    new_password = "NewPassword123!"
    response = await async_client.post(
        "/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": new_password,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    
    # Verify password was changed
    db.refresh(user)
    assert verify_password(new_password, user.password_hash)
    
    # Verify old password no longer works
    assert not verify_password("OldPassword123!", user.password_hash)


@pytest.mark.asyncio
async def test_password_reset_confirm_invalid_token(
    async_client: AsyncClient,
) -> None:
    """Test password reset confirmation with invalid token returns 401."""
    response = await async_client.post(
        "/v1/auth/reset-password",
        json={
            "token": "invalid_token_here",
            "new_password": "NewPassword123!",
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] in ["UNAUTHORIZED", "TOKEN_INVALID"]


@pytest.mark.asyncio
async def test_password_reset_confirm_expired_token(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test password reset confirmation with expired token returns 401."""
    # Create test user
    user = create_test_student(
        db,
        email="test_student@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Create expired reset token
    from datetime import UTC, datetime, timedelta
    from app.core.security import generate_password_reset_token, hash_token
    
    reset_token = generate_password_reset_token()
    token_hash = hash_token(reset_token)
    
    expired_token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
    )
    db.add(expired_token_record)
    db.commit()
    
    # Try to confirm with expired token
    response = await async_client.post(
        "/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "NewPassword123!",
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] in ["UNAUTHORIZED", "TOKEN_EXPIRED"]


@pytest.mark.asyncio
async def test_password_reset_confirm_weak_password(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test password reset confirmation with weak password returns 422."""
    # Create test user
    user = create_test_student(
        db,
        email="test_student@example.com",
        password="TestPass123!",
        email_verified=True,
        is_active=True,
    )
    db.commit()
    
    # Create reset token
    from datetime import UTC, datetime, timedelta
    from app.core.security import generate_password_reset_token, hash_token
    
    reset_token = generate_password_reset_token()
    token_hash = hash_token(reset_token)
    
    reset_token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(reset_token_record)
    db.commit()
    
    # Try to confirm with weak password (too short)
    response = await async_client.post(
        "/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "short",  # Too short
        },
    )
    
    assert response.status_code == 422  # Validation error
