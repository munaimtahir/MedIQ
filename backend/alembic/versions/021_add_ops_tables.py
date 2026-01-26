"""Add operational tables for jobs, queues, monitoring, and preferences

Revision ID: 021_ops_tables
Revises: 020_eval_harness
Create Date: 2026-01-24 10:00:00.000000

Adds tables for:
- job_run: Job execution tracking
- job_lock: Job locking mechanism
- revision_queue_theme: Theme-level revision queue aggregation
- revision_queue_user_summary: User-level revision queue summary
- queue_stats_daily: Daily queue statistics snapshots
- tag_quality_debt_log: BKT tag quality debt logging
- api_perf_sample: API performance sampling (optional)
- user_learning_prefs: User learning preferences
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "021_ops_tables"
down_revision: str | None = "020_eval_harness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create job_run table
    op.create_table(
        "job_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_key", sa.String(100), nullable=False),  # e.g. "revision_queue_regen"
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="QUEUED"),  # QUEUED, RUNNING, SUCCEEDED, FAILED
        sa.Column("stats_json", postgresql.JSONB, nullable=False, server_default="{}"),  # processed_users, due_items, errors
        sa.Column("error_text", sa.Text(), nullable=True),
        # Indexes
        sa.Index("ix_job_run_job_key", "job_key"),
        sa.Index("ix_job_run_status", "status"),
        sa.Index("ix_job_run_scheduled_for", "scheduled_for"),
    )

    # Create job_lock table
    op.create_table(
        "job_lock",
        sa.Column("job_key", sa.String(100), primary_key=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_by", sa.String(100), nullable=True),  # Process/host identifier
    )

    # Create revision_queue_theme table
    op.create_table(
        "revision_queue_theme",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theme_id", sa.Integer(), nullable=False),  # Themes use Integer IDs
        sa.Column("due_count_today", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overdue_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["theme_id"],
            ["themes.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        # Primary key
        sa.PrimaryKeyConstraint("user_id", "theme_id"),
        # Indexes
        sa.Index("ix_revision_queue_theme_user_due", "user_id", "due_count_today"),
    )

    # Create revision_queue_user_summary table
    op.create_table(
        "revision_queue_user_summary",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("due_today_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overdue_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_tomorrow_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
    )

    # Create queue_stats_daily table
    op.create_table(
        "queue_stats_daily",
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("due_today_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overdue_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_tomorrow_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("users_with_due", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Create tag_quality_debt_log table (themes.id is Integer)
    op.create_table(
        "tag_quality_debt_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("theme_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(50), nullable=False),  # MISSING_CONCEPT, MULTIPLE_CONCEPTS, INCONSISTENT_TAGS
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["theme_id"],
            ["themes.id"],
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        # Indexes
        sa.Index("ix_tag_quality_debt_log_occurred_at", "occurred_at"),
        sa.Index("ix_tag_quality_debt_log_reason", "reason"),
        sa.Index("ix_tag_quality_debt_log_theme_id", "theme_id"),
    )

    # Create api_perf_sample table (optional, for performance tracking)
    op.create_table(
        "api_perf_sample",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("route", sa.String(200), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("user_role", sa.String(20), nullable=True),
        # Indexes
        sa.Index("ix_api_perf_sample_route_occurred", "route", "occurred_at"),
        sa.Index("ix_api_perf_sample_occurred_at", "occurred_at"),
    )

    # Create user_learning_prefs table
    op.create_table(
        "user_learning_prefs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("revision_daily_target", sa.Integer(), nullable=True),  # Default from config
        sa.Column("spacing_multiplier", sa.Numeric(5, 2), nullable=False, server_default="1.0"),  # 0.8 = more frequent, 1.2 = less frequent
        sa.Column("retention_target_override", sa.Numeric(5, 4), nullable=True),  # Optional override for desired_retention
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
    )

    # Add fields to srs_user_params for A/B and cooldown
    op.add_column(
        "srs_user_params",
        sa.Column("training_cooldown_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "srs_user_params",
        sa.Column("assigned_group", sa.String(20), nullable=True),  # BASELINE_GLOBAL, TUNED_ELIGIBLE
    )


def downgrade() -> None:
    # Remove columns from srs_user_params
    op.drop_column("srs_user_params", "assigned_group")
    op.drop_column("srs_user_params", "training_cooldown_until")

    # Drop tables
    op.drop_table("user_learning_prefs")
    op.drop_table("api_perf_sample")
    op.drop_table("tag_quality_debt_log")
    op.drop_table("queue_stats_daily")
    op.drop_table("revision_queue_user_summary")
    op.drop_table("revision_queue_theme")
    op.drop_table("job_lock")
    op.drop_table("job_run")
