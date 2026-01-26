"""Tests for refresh token family isolation and per-session revocation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.auth import AuthSession, RefreshToken
from app.models.user import User, UserRole
from app.core.security import create_refresh_token, hash_token


@pytest.fixture
def test_user(db: Session) -> User:
    u = User(
        id=uuid.uuid4(),
        email="token-test@test.local",
        role=UserRole.STUDENT.value,
        password_hash="dummy",
        is_active=True,
        email_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def client(db: Session, test_user: User):
    from app.core.dependencies import get_current_user
    from app.db.session import get_db

    def override_get_db():
        yield db

    def override_get_current_user(_):
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def session1(db: Session, test_user: User) -> AuthSession:
    s = AuthSession(
        user_id=test_user.id,
        user_agent="Device1",
        ip_address="192.168.1.1",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@pytest.fixture
def session2(db: Session, test_user: User) -> AuthSession:
    s = AuthSession(
        user_id=test_user.id,
        user_agent="Device2",
        ip_address="192.168.1.2",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


class TestTokenRotation:
    """Refresh rotates token and invalidates previous."""

    def test_refresh_rotates_token(self, db: Session, test_user: User, session1: AuthSession):
        """Refreshing a token rotates it and invalidates the old one."""
        # Create initial refresh token
        old_token = create_refresh_token()
        old_hash = hash_token(old_token)
        expires_at = datetime.now(UTC) + timedelta(days=7)
        
        old_refresh = RefreshToken(
            user_id=test_user.id,
            session_id=session1.id,
            token_hash=old_hash,
            expires_at=expires_at,
        )
        db.add(old_refresh)
        db.commit()
        db.refresh(old_refresh)
        
        # Simulate refresh: mark old as rotated, create new
        from app.core.security import create_access_token
        
        old_refresh.rotated_at = datetime.now(UTC)
        new_token = create_refresh_token()
        new_hash = hash_token(new_token)
        new_refresh = RefreshToken(
            user_id=test_user.id,
            session_id=session1.id,
            token_hash=new_hash,
            expires_at=expires_at,
        )
        new_refresh.replaced_by_token_id = old_refresh.id
        db.add(new_refresh)
        db.flush()  # Get new_refresh.id
        old_refresh.replaced_by_token_id = new_refresh.id
        db.commit()
        db.refresh(old_refresh)
        db.refresh(new_refresh)
        
        # Verify old token is rotated (not active)
        assert old_refresh.rotated_at is not None
        assert not old_refresh.is_active()
        
        # Verify new token is active
        assert new_refresh.rotated_at is None
        assert new_refresh.revoked_at is None
        assert new_refresh.is_active()
        
        # Verify linkage
        assert new_refresh.replaced_by_token_id == old_refresh.id
        assert old_refresh.replaced_by_token_id == new_refresh.id


class TestRevocationIsolation:
    """Revoking one session doesn't revoke others."""

    def test_revoke_one_session_keeps_others_active(
        self, db: Session, test_user: User, session1: AuthSession, session2: AuthSession
    ):
        """Revoking session1 doesn't affect session2."""
        # Create tokens for both sessions
        token1 = create_refresh_token()
        token2 = create_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=7)
        
        rt1 = RefreshToken(
            user_id=test_user.id,
            session_id=session1.id,
            token_hash=hash_token(token1),
            expires_at=expires_at,
        )
        rt2 = RefreshToken(
            user_id=test_user.id,
            session_id=session2.id,
            token_hash=hash_token(token2),
            expires_at=expires_at,
        )
        db.add(rt1)
        db.add(rt2)
        db.commit()
        
        # Revoke session1
        session1.revoked_at = datetime.now(UTC)
        session1.revoke_reason = "test"
        db.query(RefreshToken).filter(RefreshToken.session_id == session1.id).update(
            {"revoked_at": datetime.now(UTC)}
        )
        db.commit()
        db.refresh(session1)
        db.refresh(session2)
        db.refresh(rt1)
        db.refresh(rt2)
        
        # Verify session1 is revoked, session2 is active
        assert session1.revoked_at is not None
        assert session2.revoked_at is None
        assert rt1.revoked_at is not None
        assert rt2.revoked_at is None
        assert not session1.is_active()
        assert session2.is_active()
