"""Add neo4j_sync_run table for concept graph sync tracking.

Revision ID: 028_neo4j_sync_run
Revises: 027_search_indexing_tables
Create Date: 2026-01-26 15:00:00.000000

Adds table for Neo4j concept graph sync job tracking:
- neo4j_sync_run: Tracks incremental and full rebuild sync runs
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "028_neo4j_sync_run"
down_revision: str | None = "027_search_indexing_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum for sync run status
    sync_run_status_enum = postgresql.ENUM(
        "queued",
        "running",
        "done",
        "failed",
        "blocked_frozen",
        "disabled",
        name="neo4j_sync_run_status",
        create_type=False,
    )
    sync_run_status_enum.create(op.get_bind(), checkfirst=True)

    # Create enum for sync run type
    sync_run_type_enum = postgresql.ENUM(
        "incremental",
        "full",
        name="neo4j_sync_run_type",
        create_type=False,
    )
    sync_run_type_enum.create(op.get_bind(), checkfirst=True)

    # Create neo4j_sync_run table
    op.create_table(
        "neo4j_sync_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_type", sync_run_type_enum, nullable=False),
        sa.Column("status", sync_run_status_enum, nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nodes_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("edges_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nodes_inactivated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("edges_inactivated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cycle_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Index("ix_neo4j_sync_run_status", "status"),
        sa.Index("ix_neo4j_sync_run_run_type", "run_type"),
        sa.Index("ix_neo4j_sync_run_created_at", "created_at"),
    )


def downgrade() -> None:
    op.drop_table("neo4j_sync_run")
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS neo4j_sync_run_status")
    op.execute("DROP TYPE IF EXISTS neo4j_sync_run_type")
