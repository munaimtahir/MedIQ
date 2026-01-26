"""Add warehouse export tables for Snowflake data pipeline.

Revision ID: 029_warehouse_export_tables
Revises: 028_neo4j_sync_run
Create Date: 2026-01-27 10:00:00.000000

Adds tables for warehouse export tracking:
- warehouse_export_run: Tracks export runs (incremental, backfill, full_rebuild)
- warehouse_export_state: Singleton watermark tracking
- Extends algo_runtime_config.config_json with warehouse_mode and warehouse_freeze
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "029_warehouse_export_tables"
down_revision: str | None = "028_neo4j_sync_run"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum for export run status
    export_run_status_enum = postgresql.ENUM(
        "queued",
        "running",
        "done",
        "failed",
        "blocked_disabled",
        "blocked_frozen",
        "shadow_done_files_only",
        name="warehouse_export_run_status",
        create_type=False,
    )
    export_run_status_enum.create(op.get_bind(), checkfirst=True)

    # Create enum for export run type
    export_run_type_enum = postgresql.ENUM(
        "incremental",
        "backfill",
        "full_rebuild",
        name="warehouse_export_run_type",
        create_type=False,
    )
    export_run_type_enum.create(op.get_bind(), checkfirst=True)

    # Create enum for export dataset
    export_dataset_enum = postgresql.ENUM(
        "attempts",
        "events",
        "mastery",
        "revision_queue",
        "dim_question",
        "dim_syllabus",
        "all",
        name="warehouse_export_dataset",
        create_type=False,
    )
    export_dataset_enum.create(op.get_bind(), checkfirst=True)

    # warehouse_export_run
    op.create_table(
        "warehouse_export_run",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_type", export_run_type_enum, nullable=False),
        sa.Column("status", export_run_status_enum, nullable=False, server_default="queued"),
        sa.Column("dataset", export_dataset_enum, nullable=False),
        sa.Column("range_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("range_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_exported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manifest_path", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Index("ix_warehouse_export_run_dataset_created", "dataset", sa.text("created_at DESC")),
        sa.Index("ix_warehouse_export_run_status", "status"),
    )

    # warehouse_export_state (singleton)
    op.create_table(
        "warehouse_export_state",
        sa.Column("id", sa.Integer(), primary_key=True, server_default="1"),
        sa.Column("attempts_watermark", sa.DateTime(timezone=True), nullable=True),
        sa.Column("events_watermark", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mastery_watermark", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision_queue_watermark", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("id = 1", name="ck_warehouse_export_state_singleton"),
    )
    # Create singleton row
    op.execute(
        """
        INSERT INTO warehouse_export_state (id, updated_at)
        VALUES (1, now())
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("warehouse_export_state")
    op.drop_table("warehouse_export_run")
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS warehouse_export_run_status")
    op.execute("DROP TYPE IF EXISTS warehouse_export_run_type")
    op.execute("DROP TYPE IF EXISTS warehouse_export_dataset")
