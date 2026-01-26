"""Security utilities: password hashing, JWT, token hashing."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Password hasher instance
_password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """Hash a plain password using Argon2."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain password against a hash."""
    try:
        _password_hasher.verify(password_hash, plain_password)
        return True
    except VerifyMismatchError:
        return False
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def create_access_token(user_id: str, role: str, session_id: str | None = None) -> str:
    """
    Create a JWT access token.
    
    Always signs with CURRENT key (or JWT_SECRET for backward compatibility).
    During rotation, tokens are verified against both CURRENT and PREVIOUS.
    
    Args:
        user_id: User UUID as string
        role: User role
        session_id: Optional session UUID as string (for future force logout support)
    """
    # Use CURRENT key if available, fallback to JWT_SECRET for backward compatibility
    signing_key = settings.JWT_SIGNING_KEY_CURRENT or settings.JWT_SECRET
    if not signing_key:
        raise ValueError("JWT_SIGNING_KEY_CURRENT or JWT_SECRET must be set")

    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
        "jti": str(uuid4()),
        "type": "access",
    }
    
    # Include session_id if provided
    if session_id:
        payload["sid"] = session_id

    return jwt.encode(payload, signing_key, algorithm=settings.JWT_ALG)


def verify_access_token(token: str) -> dict[str, Any]:
    """
    Verify and decode a JWT access token.
    
    Supports zero-downtime key rotation:
    - First tries CURRENT key (or JWT_SECRET for backward compatibility)
    - If that fails and PREVIOUS key exists, tries PREVIOUS key
    - This allows old tokens to remain valid during rotation overlap window
    """
    # Get signing keys (CURRENT preferred, fallback to JWT_SECRET)
    current_key = settings.JWT_SIGNING_KEY_CURRENT or settings.JWT_SECRET
    previous_key = settings.JWT_SIGNING_KEY_PREVIOUS
    
    if not current_key:
        raise ValueError("JWT_SIGNING_KEY_CURRENT or JWT_SECRET must be set")

    # Try CURRENT key first
    try:
        payload = jwt.decode(token, current_key, algorithms=[settings.JWT_ALG])
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Token is not an access token")
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.InvalidTokenError("Token has expired") from None
    except jwt.InvalidTokenError:
        # If CURRENT key fails and PREVIOUS key exists, try PREVIOUS key
        # This supports zero-downtime rotation during overlap window
        if previous_key:
            try:
                payload = jwt.decode(token, previous_key, algorithms=[settings.JWT_ALG])
                if payload.get("type") != "access":
                    raise jwt.InvalidTokenError("Token is not an access token")
                logger.debug("Token verified with PREVIOUS key (rotation overlap window)")
                return payload
            except jwt.ExpiredSignatureError:
                raise jwt.InvalidTokenError("Token has expired") from None
            except jwt.InvalidTokenError:
                pass  # Fall through to raise error below
        # Both keys failed, raise error
        raise jwt.InvalidTokenError("Invalid token: signature verification failed") from None


def create_refresh_token() -> str:
    """Create an opaque refresh token (random string)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """
    Hash a token using SHA256 with pepper.
    
    Always uses CURRENT pepper (or AUTH_TOKEN_PEPPER/TOKEN_PEPPER for backward compatibility).
    During rotation, tokens are verified against both CURRENT and PREVIOUS.
    """
    # Use CURRENT pepper if available, fallback to AUTH_TOKEN_PEPPER, then TOKEN_PEPPER
    pepper = (
        getattr(settings, "AUTH_TOKEN_PEPPER_CURRENT", None)
        or getattr(settings, "AUTH_TOKEN_PEPPER", None)
        or settings.TOKEN_PEPPER
    )
    if not pepper:
        raise ValueError("AUTH_TOKEN_PEPPER_CURRENT, AUTH_TOKEN_PEPPER, or TOKEN_PEPPER must be set")

    # Use pepper + token for hashing (sha256(raw_token + pepper))
    combined = f"{token}{pepper}"
    return hashlib.sha256(combined.encode()).hexdigest()


def verify_token_hash(token: str, stored_hash: str) -> bool:
    """
    Verify a token against a stored hash using constant-time comparison.
    
    Supports zero-downtime pepper rotation:
    - First tries CURRENT pepper (or AUTH_TOKEN_PEPPER/TOKEN_PEPPER for backward compatibility)
    - If that fails and PREVIOUS pepper exists, tries PREVIOUS pepper
    - This allows old tokens to remain valid during rotation overlap window
    
    Prevents timing attacks by using secrets.compare_digest.
    """
    # Get peppers (CURRENT preferred, fallback to AUTH_TOKEN_PEPPER, then TOKEN_PEPPER)
    current_pepper = (
        getattr(settings, "AUTH_TOKEN_PEPPER_CURRENT", None)
        or getattr(settings, "AUTH_TOKEN_PEPPER", None)
        or settings.TOKEN_PEPPER
    )
    previous_pepper = getattr(settings, "AUTH_TOKEN_PEPPER_PREVIOUS", None)
    
    if not current_pepper:
        raise ValueError("AUTH_TOKEN_PEPPER_CURRENT, AUTH_TOKEN_PEPPER, or TOKEN_PEPPER must be set")

    # Try CURRENT pepper first
    combined_current = f"{token}{current_pepper}"
    computed_hash_current = hashlib.sha256(combined_current.encode()).hexdigest()
    if secrets.compare_digest(computed_hash_current, stored_hash):
        return True
    
    # If CURRENT pepper fails and PREVIOUS pepper exists, try PREVIOUS pepper
    # This supports zero-downtime rotation during overlap window
    if previous_pepper:
        combined_previous = f"{token}{previous_pepper}"
        computed_hash_previous = hashlib.sha256(combined_previous.encode()).hexdigest()
        if secrets.compare_digest(computed_hash_previous, stored_hash):
            logger.debug("Token verified with PREVIOUS pepper (rotation overlap window)")
            return True
    
    # Both peppers failed
    return False


def generate_password_reset_token() -> str:
    """Generate a password reset token (opaque random string)."""
    return secrets.token_urlsafe(32)


def generate_email_verification_token() -> str:
    """Generate an email verification token (opaque random string)."""
    return secrets.token_urlsafe(32)
