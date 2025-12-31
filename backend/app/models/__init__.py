"""Database models."""

# Import all models here so Alembic can detect them
from app.models.auth import PasswordResetToken, RefreshToken
from app.models.attempt import AttemptAnswer, AttemptSession
from app.models.mfa import MFABackupCode, MFATOTP
from app.models.oauth import OAuthIdentity, OAuthProvider
from app.models.question import Question
from app.models.syllabus import Block, Theme
from app.models.user import User, UserRole

__all__ = [
    "User",
    "UserRole",
    "RefreshToken",
    "PasswordResetToken",
    "OAuthIdentity",
    "OAuthProvider",
    "MFATOTP",
    "MFABackupCode",
    "Block",
    "Theme",
    "Question",
    "AttemptSession",
    "AttemptAnswer",
]

