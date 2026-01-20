"""Add user_theme_mastery table

Revision ID: 010_user_theme_mastery
Revises: 009_learning_engine
Create Date: 2026-01-21 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "010_user_theme_mastery"
down_revision: Union[str, None] = "009_learning_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_theme_mastery table
    op.create_table(
        "user_theme_mastery",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("theme_id", sa.Integer(), nullable=False),
        # Aggregates
        sa.Column("attempts_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accuracy_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        # Mastery
        sa.Column("mastery_score", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Provenance
        sa.Column("algo_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("params_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("breakdown_json", postgresql.JSONB, nullable=False, server_default="{}"),
        # Foreign keys
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["algo_version_id"], ["algo_versions.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["params_id"], ["algo_params.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["algo_runs.id"], onupdate="CASCADE"),
        # Unique constraint
        sa.UniqueConstraint("user_id", "theme_id", name="uq_user_theme_mastery"),
    )

    # Create indexes
    op.create_index("ix_user_theme_mastery_user_id", "user_theme_mastery", ["user_id"])
    op.create_index(
        "ix_user_theme_mastery_user_id_mastery_score",
        "user_theme_mastery",
        ["user_id", "mastery_score"],
    )
    op.create_index(
        "ix_user_theme_mastery_user_id_computed_at",
        "user_theme_mastery",
        ["user_id", "computed_at"],
    )
    op.create_index(
        "ix_user_theme_mastery_theme_id_mastery_score",
        "user_theme_mastery",
        ["theme_id", "mastery_score"],
    )
    op.create_index(
        "ix_user_theme_mastery_algo_version_id", "user_theme_mastery", ["algo_version_id"]
    )
    op.create_index("ix_user_theme_mastery_params_id", "user_theme_mastery", ["params_id"])
    op.create_index("ix_user_theme_mastery_run_id", "user_theme_mastery", ["run_id"])

    # Update mastery v0 parameters to new spec
    op.execute(
        """
        UPDATE algo_params
        SET params_json = '{
            "lookback_days": 90,
            "min_attempts": 5,
            "recency_buckets": [
                {"days": 7, "weight": 0.50},
                {"days": 30, "weight": 0.30},
                {"days": 90, "weight": 0.20}
            ],
            "difficulty_weights": {
                "easy": 0.90,
                "medium": 1.00,
                "hard": 1.10
            },
            "use_difficulty": false
        }'::jsonb,
        updated_at = now()
        WHERE algo_version_id IN (
            SELECT id FROM algo_versions WHERE algo_key = 'mastery' AND version = 'v0'
        )
        AND is_active = true
    """
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_user_theme_mastery_run_id")
    op.drop_index("ix_user_theme_mastery_params_id")
    op.drop_index("ix_user_theme_mastery_algo_version_id")
    op.drop_index("ix_user_theme_mastery_theme_id_mastery_score")
    op.drop_index("ix_user_theme_mastery_user_id_computed_at")
    op.drop_index("ix_user_theme_mastery_user_id_mastery_score")
    op.drop_index("ix_user_theme_mastery_user_id")

    # Drop table
    op.drop_table("user_theme_mastery")
