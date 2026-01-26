"""IRT (Item Response Theory) subsystem database models.

Shadow/offline calibration only. Never used for student-facing decisions
unless FEATURE_IRT_ACTIVE is enabled.
"""

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class IrtCalibrationRun(Base):
    """IRT calibration run metadata and configuration."""

    __tablename__ = "irt_calibration_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_type = Column(
        ENUM("IRT_2PL", "IRT_3PL", name="irt_model_type", create_type=False),
        nullable=False,
    )
    dataset_spec = Column(JSONB, nullable=False, server_default="{}")
    status = Column(
        ENUM("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", name="irt_run_status", create_type=False),
        nullable=False,
        server_default="QUEUED",
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    seed = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    metrics = Column(JSONB, nullable=True)
    artifact_paths = Column(JSONB, nullable=True)
    eval_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("eval_run.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    item_params = relationship(
        "IrtItemParams", back_populates="run", cascade="all, delete-orphan"
    )
    user_abilities = relationship(
        "IrtUserAbility", back_populates="run", cascade="all, delete-orphan"
    )
    item_fits = relationship(
        "IrtItemFit", back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_irt_calibration_run_status", "status"),
        Index("ix_irt_calibration_run_created_at", "created_at"),
        Index("ix_irt_calibration_run_model_type", "model_type"),
    )


class IrtItemParams(Base):
    """IRT item parameters (a, b, c) per run and question."""

    __tablename__ = "irt_item_params"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("irt_calibration_run.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    a = Column(Float, nullable=False)
    b = Column(Float, nullable=False)
    c = Column(Float, nullable=True)
    a_se = Column(Float, nullable=True)
    b_se = Column(Float, nullable=True)
    c_se = Column(Float, nullable=True)
    flags = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("IrtCalibrationRun", back_populates="item_params")

    __table_args__ = (
        UniqueConstraint("run_id", "question_id", name="uq_irt_item_params_run_question"),
        Index("ix_irt_item_params_run_id", "run_id"),
        Index("ix_irt_item_params_question_id", "question_id"),
    )


class IrtUserAbility(Base):
    """IRT user ability (theta) per run and user."""

    __tablename__ = "irt_user_ability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("irt_calibration_run.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    theta = Column(Float, nullable=False)
    theta_se = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("IrtCalibrationRun", back_populates="user_abilities")

    __table_args__ = (
        UniqueConstraint("run_id", "user_id", name="uq_irt_user_ability_run_user"),
        Index("ix_irt_user_ability_run_id", "run_id"),
        Index("ix_irt_user_ability_user_id", "user_id"),
    )


class IrtItemFit(Base):
    """IRT item fit statistics per run and question."""

    __tablename__ = "irt_item_fit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("irt_calibration_run.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    loglik = Column(Float, nullable=True)
    infit = Column(Float, nullable=True)
    outfit = Column(Float, nullable=True)
    info_curve_summary = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("IrtCalibrationRun", back_populates="item_fits")

    __table_args__ = (
        UniqueConstraint("run_id", "question_id", name="uq_irt_item_fit_run_question"),
        Index("ix_irt_item_fit_run_id", "run_id"),
        Index("ix_irt_item_fit_question_id", "question_id"),
    )
