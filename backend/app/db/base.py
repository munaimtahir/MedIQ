"""Database base and model registry."""

from sqlalchemy.orm import DeclarativeBase

from app.db.engine import engine


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Import all models here so Alembic can detect them
from app.models import (  # noqa: F401
    AttemptAnswer,
    AttemptSession,
    Block,
    MFABackupCode,
    MFATOTP,
    OAuthIdentity,
    PasswordResetToken,
    Question,
    RefreshToken,
    Theme,
    User,
)

