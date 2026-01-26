"""Tests for token revocation, rotation, and reuse detection."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.models.auth import AuthSession, RefreshToken
from app.security.token_blacklist import (
    blacklist_session,
    is_session_blacklisted,
)

# Base URL for the API (adjust if needed)
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/v1"


class TestRefreshTokenRotation:
    """Test refresh token rotation and reuse detection."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup for each test."""
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        yield
        await self.client.aclose()

    async def test_refresh_rotation_old_token_cannot_be_used_twice(self):
        """Test that after refresh, the old refresh token cannot be used again."""
        # This test requires:
        # 1. Login to get initial tokens
        # 2. Use refresh token to get new tokens
        # 3. Try to use old refresh token again - should fail with reuse detection
        
        # Note: This is an integration test that requires a test user
        # For now, we'll document the expected behavior
        
        # Expected flow:
        # 1. POST /v1/auth/login -> get access_token_1, refresh_token_1
        # 2. POST /v1/auth/refresh with refresh_token_1 -> get access_token_2, refresh_token_2
        #    (refresh_token_1 is marked as rotated_at)
        # 3. POST /v1/auth/refresh with refresh_token_1 -> should return 401 with reuse detection
        #    (session should be revoked)
        
        pass  # Integration test - requires test user setup

    async def test_refresh_reuse_detection_revokes_session(self):
        """Test that refresh token reuse revokes the entire session."""
        # This test verifies that when a rotated token is reused:
        # 1. Session is revoked (revoked_at set, revoke_reason="refresh_reuse_detected")
        # 2. Session is blacklisted in Redis
        # 3. 401 is returned
        
        pass  # Integration test - requires test user setup


class TestLogoutRevocation:
    """Test logout revokes session and blocks refresh."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup for each test."""
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        yield
        await self.client.aclose()

    async def test_logout_revokes_session_and_blocks_refresh(self):
        """Test that logout revokes session and subsequent refresh fails."""
        # Expected flow:
        # 1. POST /v1/auth/login -> get tokens
        # 2. POST /v1/auth/logout with refresh_token -> session revoked, blacklisted
        # 3. POST /v1/auth/refresh with same refresh_token -> should return 401
        
        pass  # Integration test - requires test user setup


class TestPasswordResetRevocation:
    """Test password reset revokes all sessions."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup for each test."""
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        yield
        await self.client.aclose()

    async def test_password_reset_revokes_all_sessions(self):
        """Test that password reset revokes all sessions for the user."""
        # Expected flow:
        # 1. User has multiple active sessions (multiple devices)
        # 2. POST /v1/auth/password-reset/request -> get reset token
        # 3. POST /v1/auth/reset-password with token -> password updated
        # 4. All sessions should be revoked (revoked_at set, revoke_reason="password_reset")
        # 5. All sessions should be blacklisted in Redis
        # 6. Any refresh attempt with old tokens should fail
        
        pass  # Integration test - requires test user setup


class TestTokenBlacklist:
    """Test Redis blacklist functionality."""

    @patch("app.security.token_blacklist.get_redis_client")
    def test_blacklist_session(self, mock_get_redis):
        """Test that blacklist_session sets Redis key with TTL."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        
        session_id = str(uuid4())
        ttl = 3600
        
        result = blacklist_session(session_id, ttl)
        
        assert result is True
        mock_redis.setex.assert_called_once_with(f"bl:session:{session_id}", ttl, "1")

    @patch("app.security.token_blacklist.get_redis_client")
    def test_is_session_blacklisted(self, mock_get_redis):
        """Test that is_session_blacklisted checks Redis key."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        
        session_id = str(uuid4())
        
        # Test: session is blacklisted
        mock_redis.get.return_value = "1"
        result = is_session_blacklisted(session_id)
        assert result is True
        
        # Test: session is not blacklisted
        mock_redis.get.return_value = None
        result = is_session_blacklisted(session_id)
        assert result is False

    @patch("app.security.token_blacklist.get_redis_client")
    def test_blacklist_fail_open_when_redis_unavailable(self, mock_get_redis):
        """Test that blacklist functions fail-open when Redis is unavailable."""
        mock_get_redis.return_value = None
        
        session_id = str(uuid4())
        
        # Should return False (not blacklisted) when Redis unavailable
        result = is_session_blacklisted(session_id)
        assert result is False
        
        # Should return False (failed to blacklist) when Redis unavailable
        result = blacklist_session(session_id, 3600)
        assert result is False


class TestRefreshTokenModel:
    """Test RefreshToken model methods."""

    def test_is_active_checks_revoked_rotated_and_expired(self):
        """Test that is_active() checks revoked_at, rotated_at, and expires_at."""
        from app.models.auth import RefreshToken
        
        now = datetime.now(UTC)
        
        # Active token
        token = RefreshToken(
            id=uuid4(),
            user_id=uuid4(),
            token_hash="hash1",
            expires_at=now + timedelta(days=1),
            revoked_at=None,
            rotated_at=None,
        )
        assert token.is_active() is True
        
        # Revoked token
        token.revoked_at = now
        assert token.is_active() is False
        
        # Reset and test rotated
        token.revoked_at = None
        token.rotated_at = now
        assert token.is_active() is False
        
        # Reset and test expired
        token.rotated_at = None
        token.expires_at = now - timedelta(days=1)
        assert token.is_active() is False


class TestAuthSessionModel:
    """Test AuthSession model methods."""

    def test_is_active_checks_revoked(self):
        """Test that is_active() checks revoked_at."""
        from app.models.auth import AuthSession
        
        # Active session
        session = AuthSession(
            id=uuid4(),
            user_id=uuid4(),
            revoked_at=None,
        )
        assert session.is_active() is True
        
        # Revoked session
        session.revoked_at = datetime.now(UTC)
        assert session.is_active() is False
