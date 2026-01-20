"""CMS Question Bank models with versioning, media, and audit support."""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class QuestionStatus(str, PyEnum):
    """Question workflow status."""

    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"


class ChangeKind(str, PyEnum):
    """Type of change in version history."""

    CREATE = "CREATE"
    EDIT = "EDIT"
    STATUS_CHANGE = "STATUS_CHANGE"
    PUBLISH = "PUBLISH"
    UNPUBLISH = "UNPUBLISH"
    IMPORT = "IMPORT"


class StorageProvider(str, PyEnum):
    """Media storage provider."""

    LOCAL = "LOCAL"
    S3 = "S3"


class MediaRole(str, PyEnum):
    """Role of media attachment in question."""

    STEM = "STEM"
    EXPLANATION = "EXPLANATION"
    OPTION_A = "OPTION_A"
    OPTION_B = "OPTION_B"
    OPTION_C = "OPTION_C"
    OPTION_D = "OPTION_D"
    OPTION_E = "OPTION_E"


class Question(Base):
    """CMS Question model with workflow status and full metadata."""

    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(200), nullable=True, index=True)  # For import tracking
    stem = Column(Text, nullable=True)  # Required for submit/publish, nullable for drafts
    option_a = Column(Text, nullable=True)
    option_b = Column(Text, nullable=True)
    option_c = Column(Text, nullable=True)
    option_d = Column(Text, nullable=True)
    option_e = Column(Text, nullable=True)
    correct_index = Column(SmallInteger, nullable=True)  # 0-4, required for submit/publish
    explanation_md = Column(Text, nullable=True)  # Required for approve/publish

    # Status workflow
    status = Column(
        Enum(QuestionStatus, name="question_status", create_type=True),
        nullable=False,
        default=QuestionStatus.DRAFT,
    )

    # Tag anchors
    year_id = Column(Integer, ForeignKey("years.id", onupdate="CASCADE"), nullable=True)
    block_id = Column(Integer, ForeignKey("blocks.id", onupdate="CASCADE"), nullable=True)
    theme_id = Column(Integer, ForeignKey("themes.id", onupdate="CASCADE"), nullable=True)
    topic_id = Column(Integer, nullable=True)  # No FK yet - table may not exist
    concept_id = Column(Integer, nullable=True)  # No FK yet - table may not exist

    # Taxonomy
    cognitive_level = Column(String(50), nullable=True)
    difficulty = Column(String(50), nullable=True)

    # Source anchoring
    source_book = Column(String(200), nullable=True)
    source_page = Column(String(50), nullable=True)  # e.g., "p. 12-13"
    source_ref = Column(String(100), nullable=True)

    # Metadata
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False
    )
    updated_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False
    )
    approved_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    year = relationship("Year", backref="cms_questions")
    block = relationship("Block", backref="cms_questions")
    theme = relationship("Theme", backref="cms_questions")
    versions = relationship(
        "QuestionVersion", back_populates="question", cascade="all, delete-orphan"
    )
    media_attachments = relationship(
        "QuestionMedia", back_populates="question", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "correct_index >= 0 AND correct_index <= 4", name="ck_question_correct_index"
        ),
        Index("ix_questions_status", "status"),
        Index("ix_questions_updated_at", "updated_at"),
        Index("ix_questions_theme_id", "theme_id"),
        Index("ix_questions_block_id", "block_id"),
        Index("ix_questions_year_id", "year_id"),
    )


class QuestionVersion(Base):
    """Version history for questions (snapshot-based)."""

    __tablename__ = "question_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    version_no = Column(Integer, nullable=False)  # Starts at 1, increments
    snapshot = Column(JSONB, nullable=False)  # Full snapshot of question fields
    change_kind = Column(
        Enum(ChangeKind, name="change_kind", create_type=True),
        nullable=False,
    )
    change_reason = Column(String(500), nullable=True)
    changed_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False
    )
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    question = relationship("Question", back_populates="versions")
    changed_by_user = relationship("User", foreign_keys=[changed_by])

    __table_args__ = (
        UniqueConstraint("question_id", "version_no", name="uq_question_version"),
        Index("ix_question_versions_question_id", "question_id"),
        Index("ix_question_versions_version_no", "version_no"),
    )


class MediaAsset(Base):
    """Media assets (images, etc.) for questions."""

    __tablename__ = "media_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    storage_provider = Column(
        Enum(StorageProvider, name="storage_provider", create_type=True),
        nullable=False,
        default=StorageProvider.LOCAL,
    )
    path = Column(String(500), nullable=False)  # Relative path for LOCAL, S3 key for S3
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=True)  # For deduplication
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    question_attachments = relationship(
        "QuestionMedia", back_populates="media_asset", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_media_assets_sha256", "sha256"),)


class QuestionMedia(Base):
    """Junction table for question-media attachments."""

    __tablename__ = "question_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    media_id = Column(
        UUID(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    role = Column(
        Enum(MediaRole, name="media_role", create_type=True),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    question = relationship("Question", back_populates="media_attachments")
    media_asset = relationship("MediaAsset", back_populates="question_attachments")

    __table_args__ = (
        Index("ix_question_media_question_id", "question_id"),
        Index("ix_question_media_media_id", "media_id"),
    )


class AuditLog(Base):
    """Audit log for all admin actions."""

    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", onupdate="CASCADE"), nullable=False
    )
    action = Column(String(100), nullable=False)  # e.g., "question.create", "question.publish"
    entity_type = Column(String(50), nullable=False)  # e.g., "QUESTION", "MEDIA"
    entity_id = Column(
        UUID(as_uuid=True), nullable=False
    )  # ID of the entity (can be UUID or converted)
    before = Column(JSONB, nullable=True)  # State before change
    after = Column(JSONB, nullable=True)  # State after change
    meta = Column(JSONB, nullable=True)  # IP, user-agent, request-id, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_audit_log_entity_type", "entity_type"),
        Index("ix_audit_log_entity_id", "entity_id"),
        Index("ix_audit_log_created_at", "created_at"),
        Index("ix_audit_log_actor_user_id", "actor_user_id"),
    )
