"""Add algorithm runtime kill switch and canonical state store.

Revision ID: 024_algo_runtime_kill_switch
Revises: 023_irt_activation
Create Date: 2026-01-25 14:00:00.000000

Adds:
- algo_runtime_config: Runtime profile configuration (singleton)
- algo_switch_event: Audit trail for profile switches
- user_theme_stats: Canonical theme-level aggregates
- user_revision_state: Canonical revision state (v0/v1 compatible)
- user_mastery_state: Canonical mastery state (v0/v1 compatible)
- algo_state_bridge: Bridge job tracking
- Add algo_profile_at_start to test_sessions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "024_add_algo_runtime_kill_switch"
down_revision: str | None = "023_irt_activation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum for runtime profile
    profile_enum = postgresql.ENUM(
        "V1_PRIMARY", "V0_FALLBACK", name="algo_runtime_profile", create_type=False
    )
    profile_enum.create(op.get_bind(), checkfirst=True)

    # algo_runtime_config (singleton)
    op.create_table(
        "algo_runtime_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("active_profile", profile_enum, nullable=False, server_default="V1_PRIMARY"),
        sa.Column("active_since", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("config_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], onupdate="CASCADE"),
    )
    # Create singleton row (only if empty)
    op.execute(
        """
        INSERT INTO algo_runtime_config (id, active_profile, config_json)
        SELECT gen_random_uuid(), 'V1_PRIMARY'::algo_runtime_profile,
               '{"profile": "V1_PRIMARY", "overrides": {}, "safe_mode": {"freeze_updates": false, "prefer_cache": true}}'::jsonb
        WHERE NOT EXISTS (SELECT 1 FROM algo_runtime_config LIMIT 1)
        """
    )

    # algo_switch_event (audit trail)
    op.create_table(
        "algo_switch_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("previous_config", postgresql.JSONB, nullable=False),
        sa.Column("new_config", postgresql.JSONB, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE"),
    )
    op.create_index("ix_algo_switch_event_created_at", "algo_switch_event", ["created_at"])

    # user_theme_stats (canonical aggregates)
    op.create_table(
        "user_theme_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theme_id", sa.Integer(), nullable=False),
        sa.Column("attempts_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("avg_time_spent", sa.Numeric(10, 2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], onupdate="CASCADE"),
        sa.UniqueConstraint("user_id", "theme_id", name="uq_user_theme_stats"),
    )
    op.create_index("ix_user_theme_stats_user_id", "user_theme_stats", ["user_id"])
    op.create_index("ix_user_theme_stats_theme_id", "user_theme_stats", ["theme_id"])

    # user_revision_state (canonical revision facts)
    op.create_table(
        "user_revision_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theme_id", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),  # Canonical due time
        sa.Column("last_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stability", sa.Numeric(10, 4), nullable=True),  # FSRS v1 state
        sa.Column("difficulty", sa.Numeric(10, 4), nullable=True),  # FSRS v1 state
        sa.Column("retrievability", sa.Numeric(10, 4), nullable=True),  # Optional
        sa.Column("v0_interval_days", sa.Integer(), nullable=True),  # v0 state
        sa.Column("v0_stage", sa.Integer(), nullable=True),  # v0 state (Leitner bucket)
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], onupdate="CASCADE"),
        sa.UniqueConstraint("user_id", "theme_id", name="uq_user_revision_state"),
    )
    op.create_index("ix_user_revision_state_user_id", "user_revision_state", ["user_id"])
    op.create_index("ix_user_revision_state_user_due", "user_revision_state", ["user_id", "due_at"])

    # user_mastery_state (canonical mastery facts)
    op.create_table(
        "user_mastery_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theme_id", sa.Integer(), nullable=False),
        sa.Column("mastery_score", sa.Numeric(6, 4), nullable=False, server_default="0"),  # Canonical 0..1
        sa.Column("mastery_model", sa.String(20), nullable=False, server_default="v0"),  # "v0"|"v1"|"hybrid"
        sa.Column("mastery_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("bkt_p_mastered", sa.Numeric(6, 4), nullable=True),  # BKT v1 state
        sa.Column("bkt_state_json", postgresql.JSONB, nullable=True),  # BKT internals
        sa.Column("v0_components_json", postgresql.JSONB, nullable=True),  # v0 heuristic components
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], onupdate="CASCADE"),
        sa.UniqueConstraint("user_id", "theme_id", name="uq_user_mastery_state"),
    )
    op.create_index("ix_user_mastery_state_user_id", "user_mastery_state", ["user_id"])
    op.create_index("ix_user_mastery_state_user_mastery", "user_mastery_state", ["user_id", "mastery_score"])

    # algo_state_bridge (bridge job tracking)
    op.create_table(
        "algo_state_bridge",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_profile", profile_enum, nullable=False),
        sa.Column("to_profile", profile_enum, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),  # queued|running|done|failed
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details_json", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
    )
    op.create_index("ix_algo_state_bridge_user_id", "algo_state_bridge", ["user_id"])
    op.create_index("ix_algo_state_bridge_status", "algo_state_bridge", ["status"])

    # algo_bridge_config (policy settings)
    op.create_table(
        "algo_bridge_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_version", sa.String(50), nullable=False, server_default="ALGO_BRIDGE_SPEC_v1"),
        sa.Column("config_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("policy_version", name="uq_algo_bridge_config_policy_version"),
    )
    # Seed default config
    op.execute(
        """
        INSERT INTO algo_bridge_config (policy_version, config_json)
        VALUES (
            'ALGO_BRIDGE_SPEC_v1',
            '{
                "MASTERY_FLOOR": 0.01,
                "MASTERY_CEIL": 0.99,
                "MASTERY_MIN_ATTEMPTS_FOR_CONFIDENCE": 10,
                "MASTERY_RECENCY_TAU_DAYS": 21,
                "V0_INTERVAL_BINS_DAYS": [1,3,7,14,30,60,120],
                "V0_STAGE_MAX": 6,
                "DUE_AT_PRESERVATION_MODE": "preserve",
                "BKT_INIT_PRIOR_FROM_MASTERY": "direct",
                "BKT_PRIOR_SHRINK_ALPHA": 0.15,
                "BKT_MIN_OBS_FOR_STRONG_INIT": 20,
                "FSRS_STABILITY_FROM_INTERVAL_MODE": "monotonic_log",
                "FSRS_DIFFICULTY_FROM_ERROR_RATE_MODE": "linear_clip",
                "FSRS_DIFFICULTY_MIN": 0.05,
                "FSRS_DIFFICULTY_MAX": 0.95,
                "BANDIT_PRIOR_FROM_MASTERY_MODE": "beta_from_mastery",
                "BANDIT_PRIOR_STRENGTH_MIN": 5,
                "BANDIT_PRIOR_STRENGTH_MAX": 50
            }'::jsonb
        )
        ON CONFLICT (policy_version) DO NOTHING
        """
    )

    # bandit_theme_state (if needed by v1 adaptive)
    op.create_table(
        "bandit_theme_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theme_id", sa.Integer(), nullable=False),
        sa.Column("alpha", sa.Numeric(10, 4), nullable=False, server_default="1"),
        sa.Column("beta", sa.Numeric(10, 4), nullable=False, server_default="1"),
        sa.Column("init_from", sa.String(50), nullable=True),
        sa.Column("policy_version", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], onupdate="CASCADE"),
        sa.UniqueConstraint("user_id", "theme_id", name="uq_bandit_theme_state"),
    )
    op.create_index("ix_bandit_theme_state_user_id", "bandit_theme_state", ["user_id"])

    # Update algo_state_bridge to include policy_version
    op.add_column(
        "algo_state_bridge",
        sa.Column("policy_version", sa.String(50), nullable=True, server_default="ALGO_BRIDGE_SPEC_v1"),
    )
    op.create_unique_constraint(
        "uq_algo_state_bridge_user_profile_policy",
        "algo_state_bridge",
        ["user_id", "from_profile", "to_profile", "policy_version"],
    )

    # Add algo_profile_at_start to test_sessions
    op.add_column(
        "test_sessions",
        sa.Column("algo_profile_at_start", sa.String(50), nullable=False, server_default="V1_PRIMARY"),
    )
    op.add_column(
        "test_sessions",
        sa.Column("algo_overrides_at_start", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.add_column(
        "test_sessions",
        sa.Column("algo_policy_version_at_start", sa.String(50), nullable=True),
    )
    op.create_index("ix_test_sessions_algo_profile", "test_sessions", ["algo_profile_at_start"])


def downgrade() -> None:
    op.drop_index("ix_test_sessions_algo_profile", table_name="test_sessions")
    op.drop_column("test_sessions", "algo_policy_version_at_start")
    op.drop_column("test_sessions", "algo_overrides_at_start")
    op.drop_column("test_sessions", "algo_profile_at_start")

    op.drop_constraint("uq_algo_state_bridge_user_profile_policy", "algo_state_bridge", type_="unique")
    op.drop_column("algo_state_bridge", "policy_version")

    op.drop_index("ix_bandit_theme_state_user_id", table_name="bandit_theme_state")
    op.drop_table("bandit_theme_state")

    op.drop_table("algo_bridge_config")

    op.drop_index("ix_algo_state_bridge_status", table_name="algo_state_bridge")
    op.drop_index("ix_algo_state_bridge_user_id", table_name="algo_state_bridge")
    op.drop_table("algo_state_bridge")

    op.drop_index("ix_user_mastery_state_user_mastery", table_name="user_mastery_state")
    op.drop_index("ix_user_mastery_state_user_id", table_name="user_mastery_state")
    op.drop_table("user_mastery_state")

    op.drop_index("ix_user_revision_state_user_due", table_name="user_revision_state")
    op.drop_index("ix_user_revision_state_user_id", table_name="user_revision_state")
    op.drop_table("user_revision_state")

    op.drop_index("ix_user_theme_stats_theme_id", table_name="user_theme_stats")
    op.drop_index("ix_user_theme_stats_user_id", table_name="user_theme_stats")
    op.drop_table("user_theme_stats")

    op.drop_index("ix_algo_switch_event_created_at", table_name="algo_switch_event")
    op.drop_table("algo_switch_event")

    op.drop_table("algo_runtime_config")

    op.execute("DROP TYPE IF EXISTS algo_runtime_profile")
