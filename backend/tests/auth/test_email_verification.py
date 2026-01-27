"""Tests for email verification flow."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.auth import EmailVerificationToken
from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
async def test_email_verification_success(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test email verification with valid token."""
    # Create unverified user
    user = create_test_student(
        db,
        email="unverified@example.com",
        password="TestPass123!",
        email_verified=False,  # Not verified
        is_active=True,
    )
    db.commit()
    
    # Create verification token manually
    from datetime import UTC, datetime, timedelta
    from app.core.security import generate_email_verification_token, hash_token
    
    verification_token = generate_email_verification_token()
    token_hash = hash_token(verification_token)
    
    verification_token_record = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(verification_token_record)
    db.commit()
    
    # Verify email
    response = await async_client.post(
        "/v1/auth/verify-email",
        json={
            "token": verification_token,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    
    # Verify user email is now verified
    db.refresh(user)
    assert user.email_verified is True
    assert user.email_verified_at is not None


@pytest.mark.asyncio
async def test_email_verification_invalid_token(
    async_client: AsyncClient,
) -> None:
    """Test email verification with invalid token returns 401."""
    response = await async_client.post(
        "/v1/auth/verify-email",
        json={
            "token": "invalid_token_here",
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] in ["UNAUTHORIZED", "TOKEN_INVALID"]


@pytest.mark.asyncio
async def test_email_verification_expired_token(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test email verification with expired token returns 401."""
    # Create unverified user
    user = create_test_student(
        db,
        email="unverified@example.com",
        password="TestPass123!",
        email_verified=False,
        is_active=True,
    )
    db.commit()
    
    # Create expired verification token
    from datetime import UTC, datetime, timedelta
    from app.core.security import generate_email_verification_token, hash_token
    
    verification_token = generate_email_verification_token()
    token_hash = hash_token(verification_token)
    
    expired_token_record = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
    )
    db.add(expired_token_record)
    db.commit()
    
    # Try to verify with expired token
    response = await async_client.post(
        "/v1/auth/verify-email",
        json={
            "token": verification_token,
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] in ["UNAUTHORIZED", "TOKEN_EXPIRED"]


@pytest.mark.asyncio
async def test_resend_verification_success(
    async_client: AsyncClient,
    db: Session,
) -> None:
    """Test resend verification email returns success (even if user doesn't exist)."""
    # Create unverified user
    user = create_test_student(
        db,
        email="unverified@example.com",
        password="TestPass123!",
        email_verified=False,
        is_active=True,
    )
    db.commit()
    
    # Resend verification
    response = await async_client.post(
        "/v1/auth/resend-verification",
        json={
            "email": "unverified@example.com",
        },
    )
    
    # Should always return success (security: prevent email enumeration)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    
    # Verify new verification token was created
    verification_tokens = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id
    ).all()
    assert len(verification_tokens) > 0


@pytest.mark.asyncio
async def test_resend_verification_nonexistent_user(
    async_client: AsyncClient,
) -> None:
    """Test resend verification for nonexistent user still returns success."""
    response = await async_client.post(
        "/v1/auth/resend-verification",
        json={
            "email": "nonexistent@example.com",
        },
    )
    
    # Should still return success (security: prevent email enumeration)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
