"""Add mistake log table

Revision ID: 013_mistake_log
Revises: 012_difficulty_adaptive
Create Date: 2026-01-21 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013_mistake_log"
down_revision: str | None = "012_difficulty_adaptive"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create mistake_log table
    op.create_table(
        "mistake_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        # Frozen tags
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("block_id", sa.Integer(), nullable=True),
        sa.Column("theme_id", sa.Integer(), nullable=True),
        # Outcome
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("mistake_type", sa.String(), nullable=False),
        sa.Column("severity", sa.SmallInteger(), nullable=True),
        # Explainability
        sa.Column("evidence_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Provenance
        sa.Column("algo_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("params_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Foreign keys
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["session_id"], ["test_sessions.id"], onupdate="CASCADE", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["question_id"], ["questions.id"], onupdate="CASCADE", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["block_id"], ["blocks.id"], onupdate="CASCADE", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["theme_id"], ["themes.id"], onupdate="CASCADE", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["algo_version_id"], ["algo_versions.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["params_id"], ["algo_params.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["algo_runs.id"], onupdate="CASCADE"),
        # Unique constraint
        sa.UniqueConstraint("session_id", "question_id", name="uq_mistake_log_session_question"),
    )

    # Create indexes
    op.create_index("ix_mistake_log_user_id", "mistake_log", ["user_id"])
    op.create_index("ix_mistake_log_session_id", "mistake_log", ["session_id"])
    op.create_index("ix_mistake_log_question_id", "mistake_log", ["question_id"])
    op.create_index("ix_mistake_log_user_created", "mistake_log", ["user_id", "created_at"])
    op.create_index("ix_mistake_log_mistake_type", "mistake_log", ["mistake_type"])
    op.create_index("ix_mistake_log_year", "mistake_log", ["year"])
    op.create_index("ix_mistake_log_block_id", "mistake_log", ["block_id"])
    op.create_index("ix_mistake_log_theme_id", "mistake_log", ["theme_id"])
    op.create_index("ix_mistake_log_algo_version_id", "mistake_log", ["algo_version_id"])
    op.create_index("ix_mistake_log_params_id", "mistake_log", ["params_id"])
    op.create_index("ix_mistake_log_run_id", "mistake_log", ["run_id"])

    # Update mistakes v0 parameters
    op.execute(
        """
        UPDATE algo_params
        SET params_json = '{
            "fast_wrong_sec": 20,
            "slow_wrong_sec": 90,
            "time_pressure_remaining_sec": 60,
            "blur_threshold": 1,
            "severity_rules": {
                "FAST_WRONG": 1,
                "DISTRACTED_WRONG": 1,
                "CHANGED_ANSWER_WRONG": 2,
                "TIME_PRESSURE_WRONG": 2,
                "SLOW_WRONG": 2,
                "KNOWLEDGE_GAP": 2
            }
        }'::jsonb,
        updated_at = now()
        WHERE algo_version_id IN (
            SELECT id FROM algo_versions WHERE algo_key = 'mistakes' AND version = 'v0'
        )
        AND is_active = true
    """
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_mistake_log_run_id")
    op.drop_index("ix_mistake_log_params_id")
    op.drop_index("ix_mistake_log_algo_version_id")
    op.drop_index("ix_mistake_log_theme_id")
    op.drop_index("ix_mistake_log_block_id")
    op.drop_index("ix_mistake_log_year")
    op.drop_index("ix_mistake_log_mistake_type")
    op.drop_index("ix_mistake_log_user_created")
    op.drop_index("ix_mistake_log_question_id")
    op.drop_index("ix_mistake_log_session_id")
    op.drop_index("ix_mistake_log_user_id")

    # Drop table
    op.drop_table("mistake_log")
