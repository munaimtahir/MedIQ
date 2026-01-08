"""Academic structure models for student onboarding."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AcademicYear(Base):
    """Academic year model (e.g., 1st Year, 2nd Year, Final Year)."""

    __tablename__ = "academic_years"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)  # e.g., year1, final
    display_name = Column(String(100), nullable=False)  # e.g., "1st Year"
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    blocks = relationship("AcademicBlock", back_populates="year", cascade="all, delete-orphan")
    subjects = relationship("AcademicSubject", back_populates="year", cascade="all, delete-orphan")


class AcademicBlock(Base):
    """Academic block within a year (e.g., Block A, Block D, Block-1)."""

    __tablename__ = "academic_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)  # e.g., A, B, Block-1
    display_name = Column(String(100), nullable=False)  # e.g., "Block A"
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    year = relationship("AcademicYear", back_populates="blocks")

    __table_args__ = (UniqueConstraint("year_id", "code", name="uq_academic_block_year_code"),)


class AcademicSubject(Base):
    """Academic subject within a year (e.g., Anatomy, Physiology)."""

    __tablename__ = "academic_subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=True)  # Optional short code
    display_name = Column(String(100), nullable=False)  # e.g., "Anatomy"
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    year = relationship("AcademicYear", back_populates="subjects")

    __table_args__ = (
        UniqueConstraint("year_id", "display_name", name="uq_academic_subject_year_name"),
    )


class UserProfile(Base):
    """Extended user profile for onboarding preferences."""

    __tablename__ = "user_profiles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    selected_year_id = Column(
        Integer,
        ForeignKey("academic_years.id", ondelete="SET NULL"),
        nullable=True,
    )
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    selected_year = relationship("AcademicYear")
    selected_blocks = relationship(
        "UserBlock", back_populates="user_profile", cascade="all, delete-orphan"
    )
    selected_subjects = relationship(
        "UserSubject", back_populates="user_profile", cascade="all, delete-orphan"
    )


class UserBlock(Base):
    """User's selected blocks."""

    __tablename__ = "user_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    block_id = Column(
        Integer,
        ForeignKey("academic_blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user_profile = relationship("UserProfile", back_populates="selected_blocks")
    block = relationship("AcademicBlock")

    __table_args__ = (UniqueConstraint("user_id", "block_id", name="uq_user_block"),)


class UserSubject(Base):
    """User's selected subjects."""

    __tablename__ = "user_subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id = Column(
        Integer,
        ForeignKey("academic_subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user_profile = relationship("UserProfile", back_populates="selected_subjects")
    subject = relationship("AcademicSubject")

    __table_args__ = (UniqueConstraint("user_id", "subject_id", name="uq_user_subject"),)
