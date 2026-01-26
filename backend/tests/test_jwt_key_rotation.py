"""Tests for JWT key rotation with CURRENT/PREVIOUS key support."""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
from app.core.security import create_access_token, verify_access_token
from app.core.config import settings


def test_token_signed_with_current_key_validates(test_client):
    """Test that tokens signed with CURRENT key validate successfully."""
    with patch.object(settings, "JWT_SIGNING_KEY_CURRENT", "current_key_123"):
        with patch.object(settings, "JWT_SECRET", None):
            with patch.object(settings, "JWT_SIGNING_KEY_PREVIOUS", None):
                token = create_access_token("user-123", "STUDENT")
                payload = verify_access_token(token)
                assert payload["sub"] == "user-123"
                assert payload["role"] == "STUDENT"


def test_token_signed_with_previous_key_validates_during_overlap(test_client):
    """Test that tokens signed with PREVIOUS key validate during overlap window."""
    with patch.object(settings, "JWT_SIGNING_KEY_CURRENT", "current_key_123"):
        with patch.object(settings, "JWT_SECRET", None):
            with patch.object(settings, "JWT_SIGNING_KEY_PREVIOUS", "previous_key_456"):
                # Create token signed with PREVIOUS key (simulating old token)
                now = datetime.now(UTC)
                expire = now + timedelta(minutes=15)
                old_token = jwt.encode(
                    {
                        "sub": "user-123",
                        "role": "STUDENT",
                        "iat": now,
                        "exp": expire,
                        "jti": "test-jti",
                        "type": "access",
                    },
                    "previous_key_456",
                    algorithm="HS256",
                )
                
                # Should validate successfully using PREVIOUS key
                payload = verify_access_token(old_token)
                assert payload["sub"] == "user-123"
                assert payload["role"] == "STUDENT"


def test_token_signed_with_previous_key_fails_after_rotation(test_client):
    """Test that tokens signed with PREVIOUS key fail after PREVIOUS is removed."""
    with patch.object(settings, "JWT_SIGNING_KEY_CURRENT", "current_key_123"):
        with patch.object(settings, "JWT_SECRET", None):
            with patch.object(settings, "JWT_SIGNING_KEY_PREVIOUS", None):
                # Create token signed with old PREVIOUS key
                now = datetime.now(UTC)
                expire = now + timedelta(minutes=15)
                old_token = jwt.encode(
                    {
                        "sub": "user-123",
                        "role": "STUDENT",
                        "iat": now,
                        "exp": expire,
                        "jti": "test-jti",
                        "type": "access",
                    },
                    "previous_key_456",  # Old key that's no longer in config
                    algorithm="HS256",
                )
                
                # Should fail validation
                with pytest.raises(jwt.InvalidTokenError, match="signature verification failed"):
                    verify_access_token(old_token)


def test_new_tokens_always_signed_with_current_key(test_client):
    """Test that new tokens are always signed with CURRENT key, not PREVIOUS."""
    with patch.object(settings, "JWT_SIGNING_KEY_CURRENT", "current_key_123"):
        with patch.object(settings, "JWT_SECRET", None):
            with patch.object(settings, "JWT_SIGNING_KEY_PREVIOUS", "previous_key_456"):
                token = create_access_token("user-123", "STUDENT")
                
                # Decode without verification to check which key was used
                # (We can't directly check, but we can verify it works with CURRENT)
                payload = verify_access_token(token)
                assert payload["sub"] == "user-123"
                
                # Token should work with CURRENT key
                decoded_current = jwt.decode(token, "current_key_123", algorithms=["HS256"])
                assert decoded_current["sub"] == "user-123"
                
                # Token should NOT work with PREVIOUS key (new tokens use CURRENT)
                with pytest.raises(jwt.InvalidSignatureError):
                    jwt.decode(token, "previous_key_456", algorithms=["HS256"])


def test_backward_compatibility_with_jwt_secret(test_client):
    """Test backward compatibility when only JWT_SECRET is set (no CURRENT/PREVIOUS)."""
    with patch.object(settings, "JWT_SECRET", "legacy_secret_789"):
        with patch.object(settings, "JWT_SIGNING_KEY_CURRENT", None):
            with patch.object(settings, "JWT_SIGNING_KEY_PREVIOUS", None):
                token = create_access_token("user-123", "STUDENT")
                payload = verify_access_token(token)
                assert payload["sub"] == "user-123"
                assert payload["role"] == "STUDENT"


def test_rotation_overlap_window_accepts_both_keys(test_client):
    """Test that during overlap window, tokens signed with either key are accepted."""
    with patch.object(settings, "JWT_SIGNING_KEY_CURRENT", "current_key_123"):
        with patch.object(settings, "JWT_SECRET", None):
            with patch.object(settings, "JWT_SIGNING_KEY_PREVIOUS", "previous_key_456"):
                # Create token with CURRENT key
                token_current = create_access_token("user-123", "STUDENT")
                payload_current = verify_access_token(token_current)
                assert payload_current["sub"] == "user-123"
                
                # Create token with PREVIOUS key (simulating old token)
                now = datetime.now(UTC)
                expire = now + timedelta(minutes=15)
                token_previous = jwt.encode(
                    {
                        "sub": "user-456",
                        "role": "ADMIN",
                        "iat": now,
                        "exp": expire,
                        "jti": "test-jti-2",
                        "type": "access",
                    },
                    "previous_key_456",
                    algorithm="HS256",
                )
                payload_previous = verify_access_token(token_previous)
                assert payload_previous["sub"] == "user-456"
                assert payload_previous["role"] == "ADMIN"
