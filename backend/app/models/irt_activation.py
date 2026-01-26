"""IRT activation policy database models."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class IrtActivationEventType(str, Enum):
    """IRT activation event types."""

    EVALUATED = "EVALUATED"
    ACTIVATED = "ACTIVATED"
    DEACTIVATED = "DEACTIVATED"
    ROLLED_BACK = "ROLLED_BACK"


class IrtActivationPolicy(Base):
    """IRT activation policy configuration."""

    __tablename__ = "irt_activation_policy"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_version = Column(String(50), nullable=False)
    config = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_irt_activation_policy_version", "policy_version"),)


class IrtActivationDecision(Base):
    """IRT activation decision per calibration run."""

    __tablename__ = "irt_activation_decision"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("irt_calibration_run.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    policy_version = Column(String(50), nullable=False)
    decision_json = Column(JSONB, nullable=False)
    eligible = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
    )

    # Relationships
    run = relationship("IrtCalibrationRun")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index("ix_irt_activation_decision_run_id", "run_id"),
        Index("ix_irt_activation_decision_eligible", "eligible"),
        Index("ix_irt_activation_decision_created_at", "created_at"),
    )


class IrtActivationEvent(Base):
    """Immutable audit log of IRT activation events."""

    __tablename__ = "irt_activation_event"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(
        ENUM(IrtActivationEventType, name="irt_activation_event_type", create_type=False),
        nullable=False,
    )
    previous_state = Column(JSONB, nullable=True)
    new_state = Column(JSONB, nullable=False)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("irt_calibration_run.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    policy_version = Column(String(50), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
    )

    # Relationships
    run = relationship("IrtCalibrationRun")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index("ix_irt_activation_event_type", "event_type"),
        Index("ix_irt_activation_event_created_at", "created_at"),
        Index("ix_irt_activation_event_run_id", "run_id"),
    )
