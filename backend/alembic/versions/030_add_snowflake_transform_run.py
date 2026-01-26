"""Add snowflake_transform_run table for transform registry.

Revision ID: 030_snowflake_transform_run
Revises: 029_warehouse_export_tables
Create Date: 2026-01-27 12:00:00.000000

Adds table for tracking Snowflake transform runs:
- snowflake_transform_run: Tracks transform execution (curated, marts)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "030_snowflake_transform_run"
down_revision: str | None = "029_warehouse_export_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum for transform run status
    transform_run_status_enum = postgresql.ENUM(
        "queued",
        "running",
        "done",
        "failed",
        "disabled",
        name="snowflake_transform_run_status",
        create_type=False,
    )
    transform_run_status_enum.create(op.get_bind(), checkfirst=True)

    # Create enum for transform run type
    transform_run_type_enum = postgresql.ENUM(
        "curated_attempts",
        "curated_mastery",
        "curated_revision_queue",
        "mart_percentiles",
        "mart_comparisons",
        "mart_rank_sim",
        "all",
        name="snowflake_transform_run_type",
        create_type=False,
    )
    transform_run_type_enum.create(op.get_bind(), checkfirst=True)

    # snowflake_transform_run
    op.create_table(
        "snowflake_transform_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_type", transform_run_type_enum, nullable=False),
        sa.Column("status", transform_run_status_enum, nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Index("ix_snowflake_transform_run_status", "status"),
        sa.Index("ix_snowflake_transform_run_created_at", sa.text("created_at DESC")),
    )


def downgrade() -> None:
    op.drop_table("snowflake_transform_run")
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS snowflake_transform_run_status")
    op.execute("DROP TYPE IF EXISTS snowflake_transform_run_type")
