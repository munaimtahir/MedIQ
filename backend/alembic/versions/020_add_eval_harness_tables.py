"""Add evaluation harness tables

Revision ID: 020_eval_harness
Revises: 019_mistake_v1
Create Date: 2026-01-23 10:00:00.000000

Adds tables for Learning Engine Evaluation Harness:
- eval_run: Evaluation run metadata and configuration
- eval_metric: Computed metrics per run
- eval_artifact: Generated artifacts (reports, plots, summaries)
- eval_curve: Curve data (reliability curves, etc.)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "020_eval_harness"
down_revision: str | None = "019_mistake_v1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create eval_run table
    op.create_table(
        "eval_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="QUEUED"),  # QUEUED, RUNNING, SUCCEEDED, FAILED
        sa.Column("suite_name", sa.String(100), nullable=False),  # e.g. "bkt_v1", "full_stack_v1"
        sa.Column("suite_versions", postgresql.JSONB, nullable=False, server_default="{}"),  # {"bkt":"1.0.3", ...}
        sa.Column("dataset_spec", postgresql.JSONB, nullable=False, server_default="{}"),  # time_min, time_max, years, blocks, cohort_filters, split_strategy
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),  # bins, mastery_threshold, horizons, seeds, toggles
        sa.Column("git_sha", sa.String(100), nullable=True),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        # Indexes
        sa.Index("ix_eval_run_status", "status"),
        sa.Index("ix_eval_run_created_at", "created_at"),
        sa.Index("ix_eval_run_suite_name", "suite_name"),
    )

    # Create eval_metric table
    op.create_table(
        "eval_metric",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),  # e.g. "logloss", "brier", "ece", "time_to_mastery_p90"
        sa.Column("scope_type", sa.String(50), nullable=False),  # GLOBAL, YEAR, BLOCK, THEME, CONCEPT, USER
        sa.Column("scope_id", sa.String(100), nullable=True),  # ID for block/theme/concept/user
        sa.Column("value", sa.Numeric(12, 6), nullable=False),
        sa.Column("n", sa.Integer(), nullable=False),  # number of observations
        sa.Column("extra", postgresql.JSONB, nullable=True),  # optional (confidence intervals, etc.)
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["eval_run.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        # Indexes
        sa.Index("ix_eval_metric_run_id", "run_id"),
        sa.Index("ix_eval_metric_metric_name", "metric_name"),
        sa.Index("ix_eval_metric_scope", "scope_type", "scope_id"),
    )

    # Create eval_artifact table
    op.create_table(
        "eval_artifact",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False),  # REPORT_MD, RELIABILITY_BINS, CONFUSION, RAW_SUMMARY
        sa.Column("path", sa.Text(), nullable=True),  # Path to artifact file
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["eval_run.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        # Indexes
        sa.Index("ix_eval_artifact_run_id", "run_id"),
        sa.Index("ix_eval_artifact_type", "artifact_type"),
    )

    # Create eval_curve table
    op.create_table(
        "eval_curve",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("curve_name", sa.String(100), nullable=False),  # e.g. "reliability_curve_p_correct"
        sa.Column("data", postgresql.JSONB, nullable=False),  # Curve data points
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["eval_run.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        # Indexes
        sa.Index("ix_eval_curve_run_id", "run_id"),
        sa.Index("ix_eval_curve_name", "curve_name"),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index("ix_eval_curve_name")
    op.drop_index("ix_eval_curve_run_id")
    op.drop_table("eval_curve")

    op.drop_index("ix_eval_artifact_type")
    op.drop_index("ix_eval_artifact_run_id")
    op.drop_table("eval_artifact")

    op.drop_index("ix_eval_metric_scope")
    op.drop_index("ix_eval_metric_metric_name")
    op.drop_index("ix_eval_metric_run_id")
    op.drop_table("eval_metric")

    op.drop_index("ix_eval_run_suite_name")
    op.drop_index("ix_eval_run_created_at")
    op.drop_index("ix_eval_run_status")
    op.drop_table("eval_run")
