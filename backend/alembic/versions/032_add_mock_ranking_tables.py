"""Add mock result, mock ranking, and ranking run tables.

Revision ID: 032_add_mock_ranking_tables
Revises: 031_add_mock_blueprint_tables
Create Date: 2026-01-24 12:00:00.000000

Adds tables for mock exam ranking (Task 145):
- mock_result: Per-user raw scores for a mock instance
- mock_ranking: Computed rank/percentile per cohort, engine-tracked
- ranking_run: Run metadata, parity report for go_shadow
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "032_add_mock_ranking_tables"
down_revision: str | None = "031_add_mock_blueprint_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    status_enum = postgresql.ENUM(
        "queued",
        "running",
        "done",
        "failed",
        name="ranking_run_status",
        create_type=False,
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    # mock_result: raw scores per user per mock instance
    op.create_table(
        "mock_result",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mock_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mock_instance.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_score", sa.Integer(), nullable=False),
        sa.Column("percent", sa.Float(), nullable=False),
        sa.Column("time_taken_seconds", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mock_instance_id", "user_id", name="uq_mock_result_instance_user"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], onupdate="CASCADE", ondelete="CASCADE"),
    )
    op.create_index("ix_mock_result_mock_instance_id", "mock_result", ["mock_instance_id"])
    op.create_index("ix_mock_result_user_id", "mock_result", ["user_id"])

    # mock_ranking: computed rank/percentile per cohort, engine_used
    op.create_table(
        "mock_ranking",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mock_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mock_instance.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cohort_id", sa.Text(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("percentile", sa.Float(), nullable=False),
        sa.Column("engine_used", sa.Text(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("meta", postgresql.JSONB, nullable=True),
        sa.UniqueConstraint(
            "mock_instance_id", "cohort_id", "user_id", "engine_used",
            name="uq_mock_ranking_instance_cohort_user_engine",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], onupdate="CASCADE", ondelete="CASCADE"),
    )
    op.create_index("ix_mock_ranking_mock_instance_id", "mock_ranking", ["mock_instance_id"])
    op.create_index("ix_mock_ranking_cohort_id", "mock_ranking", ["cohort_id"])
    op.create_index("ix_mock_ranking_engine_used", "mock_ranking", ["engine_used"])

    # ranking_run: run metadata, parity_report for go_shadow
    op.create_table(
        "ranking_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mock_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mock_instance.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cohort_id", sa.Text(), nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="queued"),
        sa.Column("engine_requested", sa.Text(), nullable=True),
        sa.Column("engine_effective", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("n_users", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("parity_report", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ranking_run_mock_instance_id", "ranking_run", ["mock_instance_id"])
    op.create_index("ix_ranking_run_cohort_id", "ranking_run", ["cohort_id"])
    op.create_index("ix_ranking_run_status", "ranking_run", ["status"])
    op.create_index("ix_ranking_run_created_at", "ranking_run", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ranking_run_created_at", table_name="ranking_run")
    op.drop_index("ix_ranking_run_status", table_name="ranking_run")
    op.drop_index("ix_ranking_run_cohort_id", table_name="ranking_run")
    op.drop_index("ix_ranking_run_mock_instance_id", table_name="ranking_run")
    op.drop_table("ranking_run")

    op.drop_index("ix_mock_ranking_engine_used", table_name="mock_ranking")
    op.drop_index("ix_mock_ranking_cohort_id", table_name="mock_ranking")
    op.drop_index("ix_mock_ranking_mock_instance_id", table_name="mock_ranking")
    op.drop_table("mock_ranking")

    op.drop_index("ix_mock_result_user_id", table_name="mock_result")
    op.drop_index("ix_mock_result_mock_instance_id", table_name="mock_result")
    op.drop_table("mock_result")

    op.execute("DROP TYPE IF EXISTS ranking_run_status")
