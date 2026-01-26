"""Add difficulty v1 Elo rating tables

Revision ID: 016
Revises: 015
Create Date: 2026-01-21

Adds tables for production-grade Elo difficulty calibration:
- difficulty_user_rating: User ability (θ) with uncertainty
- difficulty_question_rating: Question difficulty (b) with uncertainty
- difficulty_update_log: Append-only audit log of all updates
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "016"
down_revision = "015_add_srs_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create difficulty_user_rating table
    op.create_table(
        "difficulty_user_rating",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("uncertainty", sa.Float(), nullable=False),
        sa.Column("n_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Indexes for difficulty_user_rating
    op.create_index(
        "idx_difficulty_user_rating_lookup",
        "difficulty_user_rating",
        ["user_id", "scope_type", "scope_id"],
        unique=True,
    )
    op.create_index(
        "idx_difficulty_user_rating_activity",
        "difficulty_user_rating",
        ["user_id", "scope_type", "last_seen_at"],
    )

    # Create difficulty_question_rating table
    op.create_table(
        "difficulty_question_rating",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("uncertainty", sa.Float(), nullable=False),
        sa.Column("n_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Indexes for difficulty_question_rating
    op.create_index(
        "idx_difficulty_question_rating_lookup",
        "difficulty_question_rating",
        ["question_id", "scope_type", "scope_id"],
        unique=True,
    )
    op.create_index(
        "idx_difficulty_question_rating_distribution",
        "difficulty_question_rating",
        ["scope_type", "rating"],
    )

    # Create difficulty_update_log table
    op.create_table(
        "difficulty_update_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("questions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("theme_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope_used", sa.String(20), nullable=False),
        sa.Column("score", sa.Boolean(), nullable=False),
        sa.Column("p_pred", sa.Float(), nullable=False),
        sa.Column("user_rating_pre", sa.Float(), nullable=False),
        sa.Column("user_rating_post", sa.Float(), nullable=False),
        sa.Column("user_unc_pre", sa.Float(), nullable=False),
        sa.Column("user_unc_post", sa.Float(), nullable=False),
        sa.Column("q_rating_pre", sa.Float(), nullable=False),
        sa.Column("q_rating_post", sa.Float(), nullable=False),
        sa.Column("q_unc_pre", sa.Float(), nullable=False),
        sa.Column("q_unc_post", sa.Float(), nullable=False),
        sa.Column("k_u_used", sa.Float(), nullable=False),
        sa.Column("k_q_used", sa.Float(), nullable=False),
        sa.Column("guess_floor_used", sa.Float(), nullable=False),
        sa.Column("scale_used", sa.Float(), nullable=False),
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
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("algo_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # Indexes for difficulty_update_log
    op.create_index(
        "idx_difficulty_update_log_user", "difficulty_update_log", ["user_id", "created_at"]
    )
    op.create_index(
        "idx_difficulty_update_log_question", "difficulty_update_log", ["question_id", "created_at"]
    )
    op.create_index(
        "idx_difficulty_update_log_theme", "difficulty_update_log", ["theme_id", "created_at"]
    )
    op.create_index(
        "idx_difficulty_update_log_attempt", "difficulty_update_log", ["attempt_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("idx_difficulty_update_log_attempt", table_name="difficulty_update_log")
    op.drop_index("idx_difficulty_update_log_theme", table_name="difficulty_update_log")
    op.drop_index("idx_difficulty_update_log_question", table_name="difficulty_update_log")
    op.drop_index("idx_difficulty_update_log_user", table_name="difficulty_update_log")
    op.drop_table("difficulty_update_log")

    op.drop_index(
        "idx_difficulty_question_rating_distribution", table_name="difficulty_question_rating"
    )
    op.drop_index("idx_difficulty_question_rating_lookup", table_name="difficulty_question_rating")
    op.drop_table("difficulty_question_rating")

    op.drop_index("idx_difficulty_user_rating_activity", table_name="difficulty_user_rating")
    op.drop_index("idx_difficulty_user_rating_lookup", table_name="difficulty_user_rating")
    op.drop_table("difficulty_user_rating")
