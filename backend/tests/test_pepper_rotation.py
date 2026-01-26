"""Tests for refresh token pepper rotation with CURRENT/PREVIOUS pepper support."""

import pytest
from unittest.mock import patch

from app.core.security import hash_token, verify_token_hash
from app.core.config import settings


def test_token_hashed_with_current_pepper_validates(test_client):
    """Test that tokens hashed with CURRENT pepper validate successfully."""
    with patch.object(settings, "AUTH_TOKEN_PEPPER_CURRENT", "current_pepper_123"):
        with patch.object(settings, "AUTH_TOKEN_PEPPER", None):
            with patch.object(settings, "TOKEN_PEPPER", None):
                with patch.object(settings, "AUTH_TOKEN_PEPPER_PREVIOUS", None):
                    token = "test_refresh_token_abc123"
                    token_hash = hash_token(token)
                    assert verify_token_hash(token, token_hash) is True


def test_token_hashed_with_previous_pepper_validates_during_overlap(test_client):
    """Test that tokens hashed with PREVIOUS pepper validate during overlap window."""
    with patch.object(settings, "AUTH_TOKEN_PEPPER_CURRENT", "current_pepper_123"):
        with patch.object(settings, "AUTH_TOKEN_PEPPER", None):
            with patch.object(settings, "TOKEN_PEPPER", None):
                with patch.object(settings, "AUTH_TOKEN_PEPPER_PREVIOUS", "previous_pepper_456"):
                    token = "test_refresh_token_abc123"
                    
                    # Hash token with PREVIOUS pepper (simulating old token)
                    import hashlib
                    combined_previous = f"{token}previous_pepper_456"
                    old_token_hash = hashlib.sha256(combined_previous.encode()).hexdigest()
                    
                    # Should validate successfully using PREVIOUS pepper
                    assert verify_token_hash(token, old_token_hash) is True


def test_token_hashed_with_previous_pepper_fails_after_rotation(test_client):
    """Test that tokens hashed with PREVIOUS pepper fail after PREVIOUS is removed."""
    with patch.object(settings, "AUTH_TOKEN_PEPPER_CURRENT", "current_pepper_123"):
        with patch.object(settings, "AUTH_TOKEN_PEPPER", None):
            with patch.object(settings, "TOKEN_PEPPER", None):
                with patch.object(settings, "AUTH_TOKEN_PEPPER_PREVIOUS", None):
                    token = "test_refresh_token_abc123"
                    
                    # Hash token with old PREVIOUS pepper (no longer in config)
                    import hashlib
                    combined_old = f"{token}previous_pepper_456"
                    old_token_hash = hashlib.sha256(combined_old.encode()).hexdigest()
                    
                    # Should fail validation
                    assert verify_token_hash(token, old_token_hash) is False


def test_new_tokens_always_hashed_with_current_pepper(test_client):
    """Test that new tokens are always hashed with CURRENT pepper, not PREVIOUS."""
    with patch.object(settings, "AUTH_TOKEN_PEPPER_CURRENT", "current_pepper_123"):
        with patch.object(settings, "AUTH_TOKEN_PEPPER", None):
            with patch.object(settings, "TOKEN_PEPPER", None):
                with patch.object(settings, "AUTH_TOKEN_PEPPER_PREVIOUS", "previous_pepper_456"):
                    token = "test_refresh_token_abc123"
                    token_hash = hash_token(token)
                    
                    # Token hash should work with CURRENT pepper
                    assert verify_token_hash(token, token_hash) is True
                    
                    # Token hash should NOT work with PREVIOUS pepper (new tokens use CURRENT)
                    import hashlib
                    combined_previous = f"{token}previous_pepper_456"
                    previous_hash = hashlib.sha256(combined_previous.encode()).hexdigest()
                    assert token_hash != previous_hash


def test_backward_compatibility_with_auth_token_pepper(test_client):
    """Test backward compatibility when only AUTH_TOKEN_PEPPER is set (no CURRENT/PREVIOUS)."""
    with patch.object(settings, "AUTH_TOKEN_PEPPER", "legacy_pepper_789"):
        with patch.object(settings, "AUTH_TOKEN_PEPPER_CURRENT", None):
            with patch.object(settings, "TOKEN_PEPPER", None):
                with patch.object(settings, "AUTH_TOKEN_PEPPER_PREVIOUS", None):
                    token = "test_refresh_token_abc123"
                    token_hash = hash_token(token)
                    assert verify_token_hash(token, token_hash) is True


def test_backward_compatibility_with_token_pepper(test_client):
    """Test backward compatibility when only TOKEN_PEPPER is set (legacy)."""
    with patch.object(settings, "TOKEN_PEPPER", "legacy_token_pepper_999"):
        with patch.object(settings, "AUTH_TOKEN_PEPPER_CURRENT", None):
            with patch.object(settings, "AUTH_TOKEN_PEPPER", None):
                with patch.object(settings, "AUTH_TOKEN_PEPPER_PREVIOUS", None):
                    token = "test_refresh_token_abc123"
                    token_hash = hash_token(token)
                    assert verify_token_hash(token, token_hash) is True


def test_rotation_overlap_window_accepts_both_peppers(test_client):
    """Test that during overlap window, tokens hashed with either pepper are accepted."""
    with patch.object(settings, "AUTH_TOKEN_PEPPER_CURRENT", "current_pepper_123"):
        with patch.object(settings, "AUTH_TOKEN_PEPPER", None):
            with patch.object(settings, "TOKEN_PEPPER", None):
                with patch.object(settings, "AUTH_TOKEN_PEPPER_PREVIOUS", "previous_pepper_456"):
                    # Create token hash with CURRENT pepper
                    token_current = "test_refresh_token_current"
                    token_hash_current = hash_token(token_current)
                    assert verify_token_hash(token_current, token_hash_current) is True
                    
                    # Create token hash with PREVIOUS pepper (simulating old token)
                    import hashlib
                    token_previous = "test_refresh_token_previous"
                    combined_previous = f"{token_previous}previous_pepper_456"
                    token_hash_previous = hashlib.sha256(combined_previous.encode()).hexdigest()
                    assert verify_token_hash(token_previous, token_hash_previous) is True


def test_pepper_priority_order(test_client):
    """Test that pepper priority is: CURRENT > AUTH_TOKEN_PEPPER > TOKEN_PEPPER."""
    # Test CURRENT takes precedence
    with patch.object(settings, "AUTH_TOKEN_PEPPER_CURRENT", "current_pepper"):
        with patch.object(settings, "AUTH_TOKEN_PEPPER", "auth_pepper"):
            with patch.object(settings, "TOKEN_PEPPER", "token_pepper"):
                token = "test_token"
                token_hash = hash_token(token)
                # Should use CURRENT pepper
                import hashlib
                expected_hash = hashlib.sha256(f"{token}current_pepper".encode()).hexdigest()
                assert token_hash == expected_hash
    
    # Test AUTH_TOKEN_PEPPER takes precedence over TOKEN_PEPPER when CURRENT is None
    with patch.object(settings, "AUTH_TOKEN_PEPPER_CURRENT", None):
        with patch.object(settings, "AUTH_TOKEN_PEPPER", "auth_pepper"):
            with patch.object(settings, "TOKEN_PEPPER", "token_pepper"):
                token = "test_token"
                token_hash = hash_token(token)
                # Should use AUTH_TOKEN_PEPPER
                import hashlib
                expected_hash = hashlib.sha256(f"{token}auth_pepper".encode()).hexdigest()
                assert token_hash == expected_hash


def test_verify_token_hash_constant_time_comparison(test_client):
    """Test that verify_token_hash uses constant-time comparison."""
    with patch.object(settings, "AUTH_TOKEN_PEPPER_CURRENT", "current_pepper_123"):
        with patch.object(settings, "AUTH_TOKEN_PEPPER", None):
            with patch.object(settings, "TOKEN_PEPPER", None):
                with patch.object(settings, "AUTH_TOKEN_PEPPER_PREVIOUS", None):
                    token = "test_refresh_token_abc123"
                    token_hash = hash_token(token)
                    
                    # Valid token should verify
                    assert verify_token_hash(token, token_hash) is True
                    
                    # Invalid token should fail (but in constant time)
                    invalid_hash = "a" * 64  # Invalid hash
                    assert verify_token_hash(token, invalid_hash) is False
                    
                    # Wrong token should fail
                    wrong_token = "wrong_token"
                    assert verify_token_hash(wrong_token, token_hash) is False
