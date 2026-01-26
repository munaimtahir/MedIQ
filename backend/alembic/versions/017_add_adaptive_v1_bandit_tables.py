"""Add adaptive v1 bandit tables

Revision ID: 017
Revises: 016
Create Date: 2026-01-21

Adds tables for constrained multi-armed bandit adaptive selection:
- bandit_user_theme_state: Per-user per-theme Beta posterior for Thompson Sampling
- adaptive_selection_log: Append-only log of selection requests and outcomes
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bandit_user_theme_state table
    op.create_table(
        "bandit_user_theme_state",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "theme_id",
            sa.Integer(),
            sa.ForeignKey("themes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        # Beta posterior parameters
        sa.Column("a", sa.Float(), nullable=False, server_default="1.0", comment="Beta alpha"),
        sa.Column("b", sa.Float(), nullable=False, server_default="1.0", comment="Beta beta"),
        # Tracking
        sa.Column(
            "n_sessions", sa.Integer(), nullable=False, server_default="0", comment="Sessions selected"
        ),
        sa.Column("last_selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reward", sa.Float(), nullable=True, comment="Reward from last session"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Indexes for bandit_user_theme_state
    op.create_index(
        "idx_bandit_user_theme_state_user_last_selected",
        "bandit_user_theme_state",
        ["user_id", "last_selected_at"],
    )

    # Create adaptive_selection_log table (append-only)
    op.create_table(
        "adaptive_selection_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Request parameters
        sa.Column(
            "mode", sa.String(20), nullable=False, comment="tutor, exam, revision"
        ),
        sa.Column(
            "source", sa.String(20), nullable=False, comment="mixed, revision, weakness"
        ),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("block_ids", postgresql.JSONB(), nullable=False),
        sa.Column("theme_ids_filter", postgresql.JSONB(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False),
        # Determinism
        sa.Column("seed", sa.String(100), nullable=False, comment="Seed for RNG reproducibility"),
        # Algo provenance
        sa.Column(
            "algo_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("algo_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "params_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("algo_params.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Diagnostic data
        sa.Column(
            "candidates_json",
            postgresql.JSONB(),
            nullable=False,
            comment="Candidate themes with computed features and scores",
        ),
        sa.Column(
            "selected_json",
            postgresql.JSONB(),
            nullable=False,
            comment="Selected themes with quotas",
        ),
        sa.Column(
            "question_ids_json",
            postgresql.JSONB(),
            nullable=False,
            comment="Final ordered question IDs",
        ),
        sa.Column(
            "stats_json",
            postgresql.JSONB(),
            nullable=False,
            comment="Stats: due_ratio, avg_p, difficulty dist, exclusions",
        ),
    )

    # Indexes for adaptive_selection_log
    op.create_index(
        "idx_adaptive_selection_log_user_requested",
        "adaptive_selection_log",
        ["user_id", "requested_at"],
    )
    op.create_index(
        "idx_adaptive_selection_log_run_id",
        "adaptive_selection_log",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_adaptive_selection_log_run_id", table_name="adaptive_selection_log")
    op.drop_index(
        "idx_adaptive_selection_log_user_requested", table_name="adaptive_selection_log"
    )
    op.drop_table("adaptive_selection_log")

    op.drop_index(
        "idx_bandit_user_theme_state_user_last_selected", table_name="bandit_user_theme_state"
    )
    op.drop_table("bandit_user_theme_state")
