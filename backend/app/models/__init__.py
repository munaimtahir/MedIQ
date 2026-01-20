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
from app.models.bookmark import Bookmark
from app.models.learning import AlgoParams, AlgoRun, AlgoVersion
from app.models.learning_difficulty import QuestionDifficulty
from app.models.learning_mastery import UserThemeMastery
from app.models.learning_revision import RevisionQueue
from app.models.mistakes import MistakeLog
from app.models.mfa import MFATOTP, MFABackupCode

# UserAllowedBlock model deprecated - table left in DB but no longer used for restrictions
# from app.models.user_allowed_blocks import UserAllowedBlock
from app.models.notification import Notification
from app.models.oauth import OAuthIdentity, OAuthProvider
from app.models.platform_settings import PlatformSettings
# Legacy Question model - commented out to avoid conflicts with CMS Question
# from app.models.question import Question
from app.models.question_cms import (
    AuditLog,
    ChangeKind,
    MediaAsset,
    MediaRole,
    Question as CMSQuestion,
    QuestionMedia,
    QuestionStatus,
    QuestionVersion,
    StorageProvider,
)
from app.models.import_schema import (
    ImportFileType,
    ImportJob,
    ImportJobRow,
    ImportJobStatus,
    ImportSchema,
)
from app.models.session import (
    AttemptEvent,
    SessionAnswer,
    SessionMode,
    SessionQuestion,
    SessionStatus,
    TestSession,
)
from app.models.syllabus import Block, Theme, Year
from app.models.user import User, UserRole

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
    # "Question",  # Legacy question model - disabled to avoid conflicts
    "CMSQuestion",  # New CMS question model (aliased as Question in question_cms.py)
    "QuestionStatus",
    "QuestionVersion",
    "ChangeKind",
    "MediaAsset",
    "QuestionMedia",
    "StorageProvider",
    "MediaRole",
    "AuditLog",
    "ImportSchema",
    "ImportFileType",
    "ImportJob",
    "ImportJobStatus",
    "ImportJobRow",
    "TestSession",
    "SessionMode",
    "SessionStatus",
    "SessionQuestion",
    "SessionAnswer",
    "AttemptEvent",
    "AttemptSession",
    "AttemptAnswer",
    "Bookmark",
    "AlgoVersion",
    "AlgoParams",
    "AlgoRun",
    "UserThemeMastery",
    "RevisionQueue",
    "QuestionDifficulty",
    "MistakeLog",
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
