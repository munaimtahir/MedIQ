"""MFA utilities: TOTP and backup codes."""

import hashlib
import secrets
from datetime import datetime, timezone

import pyotp
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import hash_token

logger = get_logger(__name__)

# Fernet cipher for encrypting TOTP secrets
_fernet: Fernet | None = None


def get_fernet() -> Fernet:
    """Get Fernet cipher instance."""
    global _fernet
    if _fernet is None:
        if not settings.MFA_ENCRYPTION_KEY:
            raise ValueError("MFA_ENCRYPTION_KEY must be set")
        _fernet = Fernet(settings.MFA_ENCRYPTION_KEY.encode())
    return _fernet


def encrypt_totp_secret(secret: str) -> str:
    """Encrypt TOTP secret."""
    fernet = get_fernet()
    return fernet.encrypt(secret.encode()).decode()


def decrypt_totp_secret(encrypted_secret: str) -> str:
    """Decrypt TOTP secret."""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_secret.encode()).decode()


def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def generate_totp_provisioning_uri(secret: str, email: str) -> str:
    """Generate TOTP provisioning URI for QR code."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=email,
        issuer_name=settings.MFA_TOTP_ISSUER,
    )


def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """Verify TOTP code with clock drift tolerance (±1 timestep)."""
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)  # window=1 allows ±1 timestep drift
    except Exception as e:
        logger.warning(f"TOTP verification error: {e}")
        return False


def generate_backup_codes(count: int = None) -> list[str]:
    """Generate backup codes."""
    if count is None:
        count = settings.MFA_BACKUP_CODES_COUNT
    return [secrets.token_urlsafe(16) for _ in range(count)]


def hash_backup_code(code: str) -> str:
    """Hash a backup code for storage."""
    # Use same token hashing as refresh tokens
    return hash_token(code)


def verify_backup_code(code: str, code_hash: str) -> bool:
    """Verify a backup code against its hash."""
    return hash_backup_code(code) == code_hash


def create_mfa_token(user_id: str) -> str:
    """Create a short-lived MFA pending token (JWT)."""
    from app.core.security import create_access_token

    # Reuse access token creation but with different type and shorter TTL
    from datetime import timedelta
    from uuid import uuid4

    import jwt

    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET must be set")

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.MFA_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
        "jti": str(uuid4()),
        "type": "mfa_pending",
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def verify_mfa_token(token: str) -> dict:
    """Verify and decode MFA pending token."""
    import jwt

    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET must be set")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        if payload.get("type") != "mfa_pending":
            raise jwt.InvalidTokenError("Token is not an MFA pending token")
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.InvalidTokenError("MFA token has expired")
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f"Invalid MFA token: {e}") from e

