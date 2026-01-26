"""Add IRT (Item Response Theory) subsystem tables.

Revision ID: 022_irt_tables
Revises: 021_ops_tables
Create Date: 2026-01-25 10:00:00.000000

Adds tables for shadow/offline IRT calibration (2PL + 3PL):
- irt_calibration_run: Run metadata, dataset_spec, status, metrics, artifacts
- irt_item_params: Item parameters (a, b, c) per run/question
- irt_user_ability: User ability (theta) per run/user
- irt_item_fit: Optional fit statistics per run/question
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "022_irt_tables"
down_revision: str | None = "021_ops_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum for IRT model type and run status
    model_type_enum = postgresql.ENUM("IRT_2PL", "IRT_3PL", name="irt_model_type", create_type=False)
    model_type_enum.create(op.get_bind(), checkfirst=True)
    status_enum = postgresql.ENUM(
        "QUEUED", "RUNNING", "SUCCEEDED", "FAILED", name="irt_run_status", create_type=False
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    # irt_calibration_run
    op.create_table(
        "irt_calibration_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_type", model_type_enum, nullable=False),
        sa.Column("dataset_spec", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", status_enum, nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metrics", postgresql.JSONB, nullable=True),
        sa.Column("artifact_paths", postgresql.JSONB, nullable=True),
        sa.Column("eval_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["eval_run_id"], ["eval_run.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.Index("ix_irt_calibration_run_status", "status"),
        sa.Index("ix_irt_calibration_run_created_at", "created_at"),
        sa.Index("ix_irt_calibration_run_model_type", "model_type"),
    )

    # irt_item_params
    op.create_table(
        "irt_item_params",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("a", sa.Float(), nullable=False),
        sa.Column("b", sa.Float(), nullable=False),
        sa.Column("c", sa.Float(), nullable=True),
        sa.Column("a_se", sa.Float(), nullable=True),
        sa.Column("b_se", sa.Float(), nullable=True),
        sa.Column("c_se", sa.Float(), nullable=True),
        sa.Column("flags", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["irt_calibration_run.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "question_id", name="uq_irt_item_params_run_question"),
        sa.Index("ix_irt_item_params_run_id", "run_id"),
        sa.Index("ix_irt_item_params_question_id", "question_id"),
    )

    # irt_user_ability
    op.create_table(
        "irt_user_ability",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theta", sa.Float(), nullable=False),
        sa.Column("theta_se", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["irt_calibration_run.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "user_id", name="uq_irt_user_ability_run_user"),
        sa.Index("ix_irt_user_ability_run_id", "run_id"),
        sa.Index("ix_irt_user_ability_user_id", "user_id"),
    )

    # irt_item_fit
    op.create_table(
        "irt_item_fit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("loglik", sa.Float(), nullable=True),
        sa.Column("infit", sa.Float(), nullable=True),
        sa.Column("outfit", sa.Float(), nullable=True),
        sa.Column("info_curve_summary", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["irt_calibration_run.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "question_id", name="uq_irt_item_fit_run_question"),
        sa.Index("ix_irt_item_fit_run_id", "run_id"),
        sa.Index("ix_irt_item_fit_question_id", "question_id"),
    )


def downgrade() -> None:
    op.drop_index("ix_irt_item_fit_question_id", table_name="irt_item_fit")
    op.drop_index("ix_irt_item_fit_run_id", table_name="irt_item_fit")
    op.drop_table("irt_item_fit")

    op.drop_index("ix_irt_user_ability_user_id", table_name="irt_user_ability")
    op.drop_index("ix_irt_user_ability_run_id", table_name="irt_user_ability")
    op.drop_table("irt_user_ability")

    op.drop_index("ix_irt_item_params_question_id", table_name="irt_item_params")
    op.drop_index("ix_irt_item_params_run_id", table_name="irt_item_params")
    op.drop_table("irt_item_params")

    op.drop_index("ix_irt_calibration_run_model_type", table_name="irt_calibration_run")
    op.drop_index("ix_irt_calibration_run_created_at", table_name="irt_calibration_run")
    op.drop_index("ix_irt_calibration_run_status", table_name="irt_calibration_run")
    op.drop_table("irt_calibration_run")

    op.execute("DROP TYPE IF EXISTS irt_run_status CASCADE")
    op.execute("DROP TYPE IF EXISTS irt_model_type CASCADE")
