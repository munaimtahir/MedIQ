"""Security utilities: password hashing, JWT, token hashing."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
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


def create_access_token(user_id: str, role: str) -> str:
    """Create a JWT access token."""
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET must be set")

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
        "jti": str(uuid4()),
        "type": "access",
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def verify_access_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT access token."""
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET must be set")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Token is not an access token")
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f"Invalid token: {e}")


def create_refresh_token() -> str:
    """Create an opaque refresh token (random string)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token using SHA256 with pepper."""
    if not settings.TOKEN_PEPPER:
        raise ValueError("TOKEN_PEPPER must be set")

    # Use pepper + token for hashing
    combined = f"{settings.TOKEN_PEPPER}:{token}"
    return hashlib.sha256(combined.encode()).hexdigest()


def generate_password_reset_token() -> str:
    """Generate a password reset token (opaque random string)."""
    return secrets.token_urlsafe(32)

