"""Add search indexing tables (outbox + sync runs).

Revision ID: 027_search_indexing_tables
Revises: 026_graph_revision_tables
Create Date: 2026-01-26 14:00:00.000000

Adds tables for Elasticsearch indexing:
- search_outbox: Event queue for incremental indexing (outbox pattern)
- search_sync_run: Run registry for nightly reindex jobs
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "027_search_indexing_tables"
down_revision: str | None = "026_graph_revision_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum for outbox event status
    outbox_status_enum = postgresql.ENUM(
        "pending",
        "processing",
        "done",
        "failed",
        name="search_outbox_status",
        create_type=False,
    )
    outbox_status_enum.create(op.get_bind(), checkfirst=True)

    # Create enum for outbox event type
    outbox_event_type_enum = postgresql.ENUM(
        "QUESTION_PUBLISHED",
        "QUESTION_UNPUBLISHED",
        "QUESTION_UPDATED",
        "QUESTION_DELETED",
        name="search_outbox_event_type",
        create_type=False,
    )
    outbox_event_type_enum.create(op.get_bind(), checkfirst=True)

    # Create enum for sync run status
    sync_run_status_enum = postgresql.ENUM(
        "queued",
        "running",
        "done",
        "failed",
        "blocked_frozen",
        "disabled",
        name="search_sync_run_status",
        create_type=False,
    )
    sync_run_status_enum.create(op.get_bind(), checkfirst=True)

    # Create enum for sync run type
    sync_run_type_enum = postgresql.ENUM(
        "incremental",
        "nightly",
        name="search_sync_run_type",
        create_type=False,
    )
    sync_run_type_enum.create(op.get_bind(), checkfirst=True)

    # search_outbox: Event queue for incremental indexing
    op.create_table(
        "search_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "event_type",
            postgresql.ENUM(
                "QUESTION_PUBLISHED",
                "QUESTION_UNPUBLISHED",
                "QUESTION_UPDATED",
                "QUESTION_DELETED",
                name="search_outbox_event_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),  # {question_id, version_id}
        sa.Column(
            "status",
            postgresql.ENUM("pending", "processing", "done", "failed", name="search_outbox_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Index("ix_search_outbox_status_next_attempt", "status", "next_attempt_at"),
        sa.Index("ix_search_outbox_event_type", "event_type"),
    )

    # search_sync_run: Run registry for nightly reindex jobs
    op.create_table(
        "search_sync_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "run_type",
            postgresql.ENUM("incremental", "nightly", name="search_sync_run_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued",
                "running",
                "done",
                "failed",
                "blocked_frozen",
                "disabled",
                name="search_sync_run_status",
                create_type=False,
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("indexed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("details", postgresql.JSONB(), nullable=True),  # Additional metrics, errors, etc.
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Index("ix_search_sync_run_status", "status"),
        sa.Index("ix_search_sync_run_run_type", "run_type"),
        sa.Index("ix_search_sync_run_created_at", "created_at"),
    )


def downgrade() -> None:
    op.drop_table("search_sync_run")
    op.drop_table("search_outbox")
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS search_sync_run_type")
    op.execute("DROP TYPE IF EXISTS search_sync_run_status")
    op.execute("DROP TYPE IF EXISTS search_outbox_event_type")
    op.execute("DROP TYPE IF EXISTS search_outbox_status")
