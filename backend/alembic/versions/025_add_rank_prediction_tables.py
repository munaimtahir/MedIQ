"""Add rank prediction v1 (quantile-based) subsystem tables.

Revision ID: 025_rank_tables
Revises: 024_add_algo_runtime_kill_switch
Create Date: 2026-01-25 12:00:00.000000

Adds tables for shadow/offline rank prediction:
- rank_prediction_snapshot: Daily snapshots per user/cohort
- rank_model_run: Shadow evaluation run registry
- rank_activation_event: Activation audit trail
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "025_rank_tables"
down_revision: str | None = "024_add_algo_runtime_kill_switch"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum for rank snapshot status
    status_enum = postgresql.ENUM(
        "ok",
        "insufficient_data",
        "unstable",
        "blocked_frozen",
        "disabled",
        name="rank_snapshot_status",
        create_type=False,
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    # Create enum for rank run status
    run_status_enum = postgresql.ENUM(
        "QUEUED",
        "RUNNING",
        "DONE",
        "FAILED",
        "BLOCKED_FROZEN",
        "DISABLED",
        name="rank_run_status",
        create_type=False,
    )
    run_status_enum.create(op.get_bind(), checkfirst=True)

    # rank_prediction_snapshot (unique on user/cohort/model/date via index; expressions not supported in UniqueConstraint)
    op.create_table(
        "rank_prediction_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohort_key", sa.String(100), nullable=False),  # e.g., "year:1", "year:2:block:A"
        sa.Column("theta_proxy", sa.Float(), nullable=True),  # ability proxy used
        sa.Column("predicted_percentile", sa.Float(), nullable=True),  # 0..1
        sa.Column("band_low", sa.Float(), nullable=True),
        sa.Column("band_high", sa.Float(), nullable=True),
        sa.Column("status", status_enum, nullable=False, server_default="ok"),
        sa.Column("model_version", sa.String(50), nullable=False, server_default="rank_v1_empirical_cdf"),
        sa.Column("features_hash", sa.String(64), nullable=True),  # Hash of features used
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.Index("ix_rank_snapshot_user_id", "user_id"),
        sa.Index("ix_rank_snapshot_cohort_key", "cohort_key"),
        sa.Index("ix_rank_snapshot_computed_at", "computed_at"),
        sa.Index("ix_rank_snapshot_status", "status"),
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_rank_snapshot_user_cohort_model_date
        ON rank_prediction_snapshot (user_id, cohort_key, model_version, ((computed_at AT TIME ZONE 'UTC')::date))
        """
    )

    # rank_model_run
    op.create_table(
        "rank_model_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cohort_key", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False, server_default="rank_v1_empirical_cdf"),
        sa.Column("dataset_spec", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("metrics", postgresql.JSONB, nullable=True),
        sa.Column("status", run_status_enum, nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.Index("ix_rank_model_run_cohort_key", "cohort_key"),
        sa.Index("ix_rank_model_run_status", "status"),
        sa.Index("ix_rank_model_run_created_at", "created_at"),
    )

    # rank_activation_event
    op.create_table(
        "rank_activation_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("previous_state", postgresql.JSONB, nullable=True),
        sa.Column("new_state", postgresql.JSONB, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("confirmation_phrase", sa.String(200), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["rank_model_run.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE"),
        sa.Index("ix_rank_activation_event_created_at", "created_at"),
        sa.Index("ix_rank_activation_event_run_id", "run_id"),
    )

    # rank_config (policy settings, similar to algo_bridge_config)
    op.create_table(
        "rank_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_version", sa.String(50), nullable=False, server_default="rank_v1"),
        sa.Column("config_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("policy_version", name="uq_rank_config_policy_version"),
    )

    # Seed default config
    op.execute(
        """
        INSERT INTO rank_config (policy_version, config_json)
        VALUES (
            'rank_v1',
            '{
                "MIN_COHORT_N": 50,
                "THETA_PROXY_PRIORITY": ["elo_rating", "mastery_weighted", "zero"],
                "WINDOW_DAYS_COHORT_STATS": 90,
                "WINDOW_DAYS_MIN_STABILITY": 60,
                "RANK_BAND_Z": 1.28,
                "STABILITY_THRESHOLD_ABS_CHANGE": 0.05,
                "COVERAGE_THRESHOLD": 0.80,
                "ACTIVATION_MIN_COHORT_N": 100
            }'::jsonb
        )
        ON CONFLICT (policy_version) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("rank_activation_event")
    op.drop_table("rank_model_run")
    op.drop_table("rank_prediction_snapshot")
    op.drop_table("rank_config")
    op.execute("DROP TYPE IF EXISTS rank_snapshot_status CASCADE")
    op.execute("DROP TYPE IF EXISTS rank_run_status CASCADE")
