"""Database models."""

# Import all models here so Alembic can detect them
from app.models.academic import (
    AcademicBlock,
    AcademicSubject,
    AcademicYear,
    UserBlock,
    UserProfile,
    UserSubject,
)
from app.models.attempt import AttemptAnswer, AttemptSession
from app.models.auth import EmailVerificationToken, PasswordResetToken, RefreshToken
from app.models.mfa import MFATOTP, MFABackupCode
from app.models.oauth import OAuthIdentity, OAuthProvider
from app.models.question import Question
from app.models.syllabus import Block, Theme, Year
from app.models.user import User, UserRole
# UserAllowedBlock model deprecated - table left in DB but no longer used for restrictions
# from app.models.user_allowed_blocks import UserAllowedBlock
from app.models.notification import Notification
from app.models.platform_settings import PlatformSettings

__all__ = [
    "User",
    "UserRole",
    "RefreshToken",
    "PasswordResetToken",
    "EmailVerificationToken",
    "OAuthIdentity",
    "OAuthProvider",
    "MFATOTP",
    "MFABackupCode",
    "Year",
    "Block",
    "Theme",
    "Question",
    "AttemptSession",
    "AttemptAnswer",
    "AcademicYear",
    "AcademicBlock",
    "AcademicSubject",
    "UserProfile",
    "UserBlock",
    "UserSubject",
    # "UserAllowedBlock",  # Deprecated - no longer used
    "Notification",
    "PlatformSettings",
]
