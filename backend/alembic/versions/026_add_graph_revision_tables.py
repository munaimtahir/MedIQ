"""Add graph-aware revision planning subsystem tables.

Revision ID: 026_graph_revision_tables
Revises: 025_rank_tables
Create Date: 2026-01-26 12:00:00.000000

Adds tables for graph-aware revision planning:
- prereq_edges: Authoritative prerequisite edges (Postgres source, synced to Neo4j)
- prereq_sync_run: Neo4j sync job tracking
- shadow_revision_plan: Shadow plans computed but not applied
- graph_revision_run: Run registry with metrics
- graph_revision_config: Planner configuration
- graph_revision_activation_event: Activation audit trail
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "026_graph_revision_tables"
down_revision: str | None = "025_rank_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum for prereq sync run status
    sync_status_enum = postgresql.ENUM(
        "QUEUED",
        "RUNNING",
        "DONE",
        "FAILED",
        name="prereq_sync_status",
        create_type=False,
    )
    sync_status_enum.create(op.get_bind(), checkfirst=True)

    # Create enum for graph revision run status
    run_status_enum = postgresql.ENUM(
        "QUEUED",
        "RUNNING",
        "DONE",
        "FAILED",
        "BLOCKED_FROZEN",
        "DISABLED",
        name="graph_revision_run_status",
        create_type=False,
    )
    run_status_enum.create(op.get_bind(), checkfirst=True)

    # prereq_edges: Authoritative source in Postgres
    op.create_table(
        "prereq_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("from_theme_id", sa.Integer(), nullable=False),  # Prerequisite theme
        sa.Column("to_theme_id", sa.Integer(), nullable=False),  # Theme that requires from_theme_id
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),  # manual, imported, inferred
        sa.Column("confidence", sa.Float(), nullable=True),  # 0..1 if inferred
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["from_theme_id"], ["themes.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_theme_id"], ["themes.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.Index(
            "ix_prereq_edges_unique_active",
            "from_theme_id",
            "to_theme_id",
            unique=True,
            postgresql_where=sa.text("is_active = true"),
        ),
        sa.Index("ix_prereq_edges_from_theme_id", "from_theme_id"),
        sa.Index("ix_prereq_edges_to_theme_id", "to_theme_id"),
        sa.Index("ix_prereq_edges_is_active", "is_active"),
    )

    # prereq_sync_run: Track Neo4j sync jobs
    op.create_table(
        "prereq_sync_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("status", sync_status_enum, nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details_json", postgresql.JSONB, nullable=True),  # node_count, edge_count, errors, etc.
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Index("ix_prereq_sync_run_status", "status"),
        sa.Index("ix_prereq_sync_run_created_at", "created_at"),
    )

    # shadow_revision_plan: Shadow plans (not applied unless activated)
    op.create_table(
        "shadow_revision_plan",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),  # Date for which plan was computed
        sa.Column("mode", sa.String(20), nullable=False, server_default="baseline"),  # baseline|shadow
        sa.Column("baseline_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("injected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("plan_json", postgresql.JSONB, nullable=False, server_default="[]"),  # Ordered list of plan items
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "run_date", name="uq_shadow_revision_plan_user_date"),
        sa.Index("ix_shadow_revision_plan_user_id", "user_id"),
        sa.Index("ix_shadow_revision_plan_run_date", "run_date"),
        sa.Index("ix_shadow_revision_plan_mode", "mode"),
    )

    # graph_revision_run: Run registry with metrics
    op.create_table(
        "graph_revision_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False, server_default="shadow"),  # shadow|active
        sa.Column("cohort_key", sa.String(100), nullable=True),  # Optional cohort filter
        sa.Column("metrics", postgresql.JSONB, nullable=True),  # coverage, injection_rate, neo4j_availability, cycle_count
        sa.Column("status", run_status_enum, nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.Index("ix_graph_revision_run_run_date", "run_date"),
        sa.Index("ix_graph_revision_run_status", "status"),
        sa.Index("ix_graph_revision_run_mode", "mode"),
        sa.Index("ix_graph_revision_run_created_at", "created_at"),
    )

    # graph_revision_config: Planner configuration
    op.create_table(
        "graph_revision_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_version", sa.String(50), nullable=False, server_default="graph_revision_v1"),
        sa.Column("config_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("policy_version", name="uq_graph_revision_config_policy_version"),
    )

    # graph_revision_activation_event: Activation audit trail
    op.create_table(
        "graph_revision_activation_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("previous_state", postgresql.JSONB, nullable=True),
        sa.Column("new_state", postgresql.JSONB, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("confirmation_phrase", sa.String(200), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["graph_revision_run.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE"),
        sa.Index("ix_graph_revision_activation_event_created_at", "created_at"),
        sa.Index("ix_graph_revision_activation_event_run_id", "run_id"),
    )

    # Seed default config
    op.execute(
        """
        INSERT INTO graph_revision_config (policy_version, config_json)
        VALUES (
            'graph_revision_v1',
            '{
                "prereq_depth": 2,
                "injection_cap_ratio": 0.25,
                "max_prereq_per_theme": 2,
                "scoring_weights": {
                    "mastery_inverse": 0.5,
                    "is_overdue": 0.3,
                    "recency_need": 0.2
                },
                "coverage_threshold": 0.50,
                "neo4j_availability_threshold": 0.95,
                "cycle_check_enabled": true
            }'::jsonb
        )
        ON CONFLICT (policy_version) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("graph_revision_activation_event")
    op.drop_table("graph_revision_config")
    op.drop_table("graph_revision_run")
    op.drop_table("shadow_revision_plan")
    op.drop_table("prereq_sync_run")
    op.drop_table("prereq_edges")
    op.execute("DROP TYPE IF EXISTS graph_revision_run_status CASCADE")
    op.execute("DROP TYPE IF EXISTS prereq_sync_status CASCADE")
