"""Algorithm runtime configuration and kill switch models."""

import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AlgoRuntimeProfile(str, Enum):
    """Algorithm runtime profile."""

    V1_PRIMARY = "V1_PRIMARY"
    V0_FALLBACK = "V0_FALLBACK"


class AlgoRuntimeConfig(Base):
    """Algorithm runtime configuration (singleton)."""

    __tablename__ = "algo_runtime_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    active_profile = Column(
        ENUM(AlgoRuntimeProfile, name="algo_runtime_profile", create_type=False),
        nullable=False,
        server_default="V1_PRIMARY",
    )
    active_since = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reason = Column(Text, nullable=True)
    changed_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
    )
    config_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    changed_by = relationship("User", foreign_keys=[changed_by_user_id])


class AlgoSwitchEvent(Base):
    """Immutable audit trail for algorithm profile switches."""

    __tablename__ = "algo_switch_event"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    previous_config = Column(JSONB, nullable=False)
    new_config = Column(JSONB, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
    )

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (Index("ix_algo_switch_event_created_at", "created_at"),)


class UserThemeStats(Base):
    """Canonical theme-level aggregates (version-agnostic)."""

    __tablename__ = "user_theme_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    theme_id = Column(
        Integer,
        ForeignKey("themes.id", onupdate="CASCADE"),
        nullable=False,
    )
    attempts_total = Column(Integer, nullable=False, server_default="0")
    correct_total = Column(Integer, nullable=False, server_default="0")
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    avg_time_spent = Column(Numeric(10, 2), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    theme = relationship("Theme")

    __table_args__ = (
        UniqueConstraint("user_id", "theme_id", name="uq_user_theme_stats"),
        Index("ix_user_theme_stats_user_id", "user_id"),
        Index("ix_user_theme_stats_theme_id", "theme_id"),
    )


class UserRevisionState(Base):
    """Canonical revision state (v0/v1 compatible)."""

    __tablename__ = "user_revision_state"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    theme_id = Column(
        Integer,
        ForeignKey("themes.id", onupdate="CASCADE"),
        nullable=False,
    )
    due_at = Column(DateTime(timezone=True), nullable=True)  # Canonical due time
    last_review_at = Column(DateTime(timezone=True), nullable=True)
    stability = Column(Numeric(10, 4), nullable=True)  # FSRS v1 state
    difficulty = Column(Numeric(10, 4), nullable=True)  # FSRS v1 state
    retrievability = Column(Numeric(10, 4), nullable=True)  # Optional
    v0_interval_days = Column(Integer, nullable=True)  # v0 state
    v0_stage = Column(Integer, nullable=True)  # v0 state (Leitner bucket)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    theme = relationship("Theme")

    __table_args__ = (
        UniqueConstraint("user_id", "theme_id", name="uq_user_revision_state"),
        Index("ix_user_revision_state_user_id", "user_id"),
        Index("ix_user_revision_state_user_due", "user_id", "due_at"),
    )


class UserMasteryState(Base):
    """Canonical mastery state (v0/v1 compatible)."""

    __tablename__ = "user_mastery_state"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    theme_id = Column(
        Integer,
        ForeignKey("themes.id", onupdate="CASCADE"),
        nullable=False,
    )
    mastery_score = Column(Numeric(6, 4), nullable=False, server_default="0")  # Canonical 0..1
    mastery_model = Column(String(20), nullable=False, server_default="v0")  # "v0"|"v1"|"hybrid"
    mastery_updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    bkt_p_mastered = Column(Numeric(6, 4), nullable=True)  # BKT v1 state
    bkt_state_json = Column(JSONB, nullable=True)  # BKT internals
    v0_components_json = Column(JSONB, nullable=True)  # v0 heuristic components

    # Relationships
    user = relationship("User")
    theme = relationship("Theme")

    __table_args__ = (
        UniqueConstraint("user_id", "theme_id", name="uq_user_mastery_state"),
        Index("ix_user_mastery_state_user_id", "user_id"),
        Index("ix_user_mastery_state_user_mastery", "user_id", "mastery_score"),
    )


class AlgoBridgeConfig(Base):
    """Bridge policy configuration (ALGO_BRIDGE_SPEC_v1 settings)."""

    __tablename__ = "algo_bridge_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_version = Column(String(50), nullable=False, server_default="ALGO_BRIDGE_SPEC_v1")
    config_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("policy_version", name="uq_algo_bridge_config_policy_version"),)


class AlgoStateBridge(Base):
    """Bridge job tracking for state conversion."""

    __tablename__ = "algo_state_bridge"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    from_profile = Column(
        ENUM(AlgoRuntimeProfile, name="algo_runtime_profile", create_type=False),
        nullable=False,
    )
    to_profile = Column(
        ENUM(AlgoRuntimeProfile, name="algo_runtime_profile", create_type=False),
        nullable=False,
    )
    policy_version = Column(String(50), nullable=False, server_default="ALGO_BRIDGE_SPEC_v1")
    status = Column(String(20), nullable=False, server_default="queued")  # queued|running|done|failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    details_json = Column(JSONB, nullable=True)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "from_profile", "to_profile", "policy_version",
            name="uq_algo_state_bridge_user_profile_policy",
        ),
        Index("ix_algo_state_bridge_user_id", "user_id"),
        Index("ix_algo_state_bridge_status", "status"),
    )


class BanditThemeState(Base):
    """Bandit per-theme state (Beta priors)."""

    __tablename__ = "bandit_theme_state"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    theme_id = Column(
        Integer,
        ForeignKey("themes.id", onupdate="CASCADE"),
        nullable=False,
    )
    alpha = Column(Numeric(10, 4), nullable=False, server_default="1")
    beta = Column(Numeric(10, 4), nullable=False, server_default="1")
    init_from = Column(String(50), nullable=True)  # "mastery", "prior", etc.
    policy_version = Column(String(50), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    theme = relationship("Theme")

    __table_args__ = (
        UniqueConstraint("user_id", "theme_id", name="uq_bandit_theme_state"),
        Index("ix_bandit_theme_state_user_id", "user_id"),
    )
