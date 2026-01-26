"""Add mistake v1 model tables

Revision ID: 019_mistake_v1
Revises: 018_activate_v1_algorithms
Create Date: 2026-01-22 10:00:00.000000

Adds tables for Mistake Engine v1 supervised classifier:
- mistake_model_version: Model artifacts and metadata
- mistake_training_run: Training job logs
- mistake_inference_log: Runtime inference logs (sampled)

Also updates mistake_log to support v1:
- source: RULE_V0 or MODEL_V1
- model_version_id: nullable reference to model
- confidence: nullable prediction confidence
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "019_mistake_v1"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create mistake_model_version table
    op.create_table(
        "mistake_model_version",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(20), nullable=False),  # DRAFT, ACTIVE, ROLLED_BACK
        sa.Column("model_type", sa.String(20), nullable=False),  # LOGREG, LGBM
        sa.Column("feature_schema_version", sa.String(50), nullable=False),
        sa.Column("label_schema_version", sa.String(50), nullable=False),
        sa.Column("training_window_start", sa.Date(), nullable=True),
        sa.Column("training_window_end", sa.Date(), nullable=True),
        sa.Column("metrics_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("artifact_path", sa.Text(), nullable=True),  # Path to model file
        sa.Column("calibration_type", sa.String(20), nullable=True),  # NONE, SIGMOID, ISOTONIC
        sa.Column("notes", sa.Text(), nullable=True),
        # Indexes
        sa.Index("ix_mistake_model_version_status", "status"),
        sa.Index("ix_mistake_model_version_created_at", "created_at"),
    )

    # Create mistake_training_run table
    op.create_table(
        "mistake_training_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_row_count", sa.Integer(), nullable=True),
        sa.Column("class_distribution_json", postgresql.JSONB, nullable=True),
        sa.Column("hyperparams_json", postgresql.JSONB, nullable=True),
        sa.Column("git_commit", sa.String(100), nullable=True),
        sa.Column("run_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("error_text", sa.Text(), nullable=True),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["mistake_model_version.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_by"],
            ["users.id"],
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        # Indexes
        sa.Index("ix_mistake_training_run_model_version_id", "model_version_id"),
        sa.Index("ix_mistake_training_run_started_at", "started_at"),
    )

    # Create mistake_inference_log table (append-only, sampled)
    op.create_table(
        "mistake_inference_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=True),  # session_id + question_id combo identifier
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("predicted_type", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("top_features_json", postgresql.JSONB, nullable=True),
        sa.Column("raw_features_json", postgresql.JSONB, nullable=True),  # Optional, can be gated/sampled
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["test_sessions.id"],
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["mistake_model_version.id"],
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        # Indexes
        sa.Index("ix_mistake_inference_log_user_id", "user_id"),
        sa.Index("ix_mistake_inference_log_occurred_at", "occurred_at"),
        sa.Index("ix_mistake_inference_log_model_version_id", "model_version_id"),
        sa.Index("ix_mistake_inference_log_fallback_used", "fallback_used"),
    )

    # Update mistake_log to support v1
    op.add_column(
        "mistake_log",
        sa.Column("source", sa.String(20), nullable=True),  # RULE_V0, MODEL_V1
    )
    op.add_column(
        "mistake_log",
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "mistake_log",
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
    )

    # Add foreign key for model_version_id
    op.create_foreign_key(
        "fk_mistake_log_model_version",
        "mistake_log",
        "mistake_model_version",
        ["model_version_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="SET NULL",
    )

    # Add index for model_version_id
    op.create_index("ix_mistake_log_model_version_id", "mistake_log", ["model_version_id"])
    op.create_index("ix_mistake_log_source", "mistake_log", ["source"])

    # Set existing records to RULE_V0
    op.execute(
        """
        UPDATE mistake_log
        SET source = 'RULE_V0'
        WHERE source IS NULL
        """
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_mistake_log_source")
    op.drop_index("ix_mistake_log_model_version_id")

    # Drop foreign key
    op.drop_constraint("fk_mistake_log_model_version", "mistake_log", type_="foreignkey")

    # Drop columns from mistake_log
    op.drop_column("mistake_log", "confidence")
    op.drop_column("mistake_log", "model_version_id")
    op.drop_column("mistake_log", "source")

    # Drop mistake_inference_log table
    op.drop_index("ix_mistake_inference_log_fallback_used")
    op.drop_index("ix_mistake_inference_log_model_version_id")
    op.drop_index("ix_mistake_inference_log_occurred_at")
    op.drop_index("ix_mistake_inference_log_user_id")
    op.drop_table("mistake_inference_log")

    # Drop mistake_training_run table
    op.drop_index("ix_mistake_training_run_started_at")
    op.drop_index("ix_mistake_training_run_model_version_id")
    op.drop_table("mistake_training_run")

    # Drop mistake_model_version table
    op.drop_index("ix_mistake_model_version_created_at")
    op.drop_index("ix_mistake_model_version_status")
    op.drop_table("mistake_model_version")
