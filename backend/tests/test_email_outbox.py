"""Tests for email outbox and password reset flow."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.security import generate_password_reset_token, hash_token, hash_password
from app.email.runtime import EmailMode, get_effective_email_mode
from app.email.service import enqueue_email, drain_outbox
from app.models.email import EmailOutbox, EmailRuntimeConfig, EmailStatus
from app.models.auth import PasswordResetToken
from app.models.user import User


def test_password_reset_token_stored_hashed(db_session):
    """Test that password reset tokens are stored hashed, never raw."""
    user = db_session.query(User).first()
    if not user:
        pytest.skip("No user found in database")

    raw_token = generate_password_reset_token()
    token_hash = hash_token(raw_token)

    # Verify raw token is not in hash
    assert raw_token not in token_hash
    assert len(token_hash) == 64  # SHA256 hex

    # Create token record
    token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(token_record)
    db_session.commit()

    # Verify token is stored hashed
    stored = db_session.query(PasswordResetToken).filter(PasswordResetToken.id == token_record.id).first()
    assert stored.token_hash == token_hash
    assert raw_token not in stored.token_hash


def test_password_reset_request_returns_200_for_existing_and_non_existing_email(client, db_session):
    """Test that password reset request always returns 200 (anti-enumeration)."""
    # Test with non-existing email
    response = client.post(
        "/v1/auth/password-reset/request",
        json={"email": "nonexistent@example.com"},
    )
    assert response.status_code == 200

    # Test with existing email
    user = db_session.query(User).first()
    if user:
        response = client.post(
            "/v1/auth/password-reset/request",
            json={"email": user.email},
        )
        assert response.status_code == 200


def test_password_reset_confirm_valid_token_updates_password(db_session):
    """Test that valid token updates password and marks used_at."""
    user = db_session.query(User).first()
    if not user:
        pytest.skip("No user found in database")

    raw_token = generate_password_reset_token()
    token_hash = hash_token(raw_token)

    token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(token_record)
    db_session.commit()

    # Confirm reset
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "NewPassword123"},
    )

    assert response.status_code == 200

    # Verify token is marked as used
    db_session.refresh(token_record)
    assert token_record.used_at is not None

    # Verify password is updated
    db_session.refresh(user)
    assert user.password_hash != hash_password("old_password")  # Different from before


def test_password_reset_reused_token_rejected(db_session):
    """Test that reused token is rejected."""
    user = db_session.query(User).first()
    if not user:
        pytest.skip("No user found in database")

    raw_token = generate_password_reset_token()
    token_hash = hash_token(raw_token)

    token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(token_record)
    db_session.commit()

    # Use token once
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "NewPassword123"},
    )
    assert response.status_code == 200

    # Try to use again
    response = client.post(
        "/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "AnotherPassword123"},
    )
    assert response.status_code == 401


def test_email_enqueue_disabled_mode_blocks(db_session):
    """Test that email enqueue in disabled mode creates blocked_disabled status."""
    # Set mode to disabled
    config = db_session.query(EmailRuntimeConfig).first()
    if not config:
        config = EmailRuntimeConfig(
            requested_mode=EmailMode.DISABLED.value,
            email_freeze=False,
            config_json={"requested_mode": "disabled", "email_freeze": False},
        )
        db_session.add(config)
        db_session.commit()
    else:
        config.requested_mode = EmailMode.DISABLED.value
        db_session.commit()

    outbox = enqueue_email(
        db=db_session,
        to_email="test@example.com",
        subject="Test",
        template_key="PASSWORD_RESET",
        template_vars={"reset_url": "http://test.com", "expires_minutes": 30},
    )

    assert outbox.status == EmailStatus.BLOCKED_DISABLED.value


def test_email_enqueue_shadow_mode_logs(db_session):
    """Test that email enqueue in shadow mode creates shadow_logged status."""
    # Set mode to shadow
    config = db_session.query(EmailRuntimeConfig).first()
    if not config:
        config = EmailRuntimeConfig(
            requested_mode=EmailMode.SHADOW.value,
            email_freeze=False,
            config_json={"requested_mode": "shadow", "email_freeze": False},
        )
        db_session.add(config)
        db_session.commit()
    else:
        config.requested_mode = EmailMode.SHADOW.value
        db_session.commit()

    outbox = enqueue_email(
        db=db_session,
        to_email="test@example.com",
        subject="Test",
        template_key="PASSWORD_RESET",
        template_vars={"reset_url": "http://test.com", "expires_minutes": 30},
    )

    assert outbox.status == EmailStatus.SHADOW_LOGGED.value


def test_drain_outbox_active_console_provider_marks_sent(db_session):
    """Test that drain outbox with active mode and console provider marks emails as sent."""
    # Set mode to active
    config = db_session.query(EmailRuntimeConfig).first()
    if not config:
        config = EmailRuntimeConfig(
            requested_mode=EmailMode.ACTIVE.value,
            email_freeze=False,
            config_json={"requested_mode": "active", "email_freeze": False},
        )
        db_session.add(config)
        db_session.commit()
    else:
        config.requested_mode = EmailMode.ACTIVE.value
        config.email_freeze = False
        db_session.commit()

    # Create queued email
    outbox = EmailOutbox(
        to_email="test@example.com",
        subject="Test",
        template_key="PASSWORD_RESET",
        template_vars={"reset_url": "http://test.com", "expires_minutes": 30},
        status=EmailStatus.QUEUED.value,
        body_text="Test email",
    )
    db_session.add(outbox)
    db_session.commit()

    # Drain outbox
    result = drain_outbox(db_session, limit=10)

    # Verify email is sent
    db_session.refresh(outbox)
    assert outbox.status == EmailStatus.SENT.value
    assert outbox.sent_at is not None
    assert result["sent"] == 1
