"""Add mock blueprint and generation tables.

Revision ID: 031_add_mock_blueprint_tables
Revises: 030_snowflake_transform_run
Create Date: 2026-01-23 12:00:00.000000

Adds tables for mock blueprint management and deterministic generation:
- mock_blueprint: Blueprint definitions
- mock_blueprint_version: Version history for config changes
- mock_generation_run: Generation run tracking
- mock_instance: Generated mock question sets
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "031_add_mock_blueprint_tables"
down_revision: str | None = "030_snowflake_transform_run"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enums
    blueprint_mode_enum = postgresql.ENUM(
        "EXAM",
        "TUTOR",
        name="mock_blueprint_mode",
        create_type=False,
    )
    blueprint_mode_enum.create(op.get_bind(), checkfirst=True)

    blueprint_status_enum = postgresql.ENUM(
        "DRAFT",
        "ACTIVE",
        "ARCHIVED",
        name="mock_blueprint_status",
        create_type=False,
    )
    blueprint_status_enum.create(op.get_bind(), checkfirst=True)

    generation_run_status_enum = postgresql.ENUM(
        "queued",
        "running",
        "done",
        "failed",
        name="mock_generation_run_status",
        create_type=False,
    )
    generation_run_status_enum.create(op.get_bind(), checkfirst=True)

    # mock_blueprint
    op.create_table(
        "mock_blueprint",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("mode", blueprint_mode_enum, nullable=False, server_default="EXAM"),
        sa.Column("status", blueprint_status_enum, nullable=False, server_default="DRAFT"),
        sa.Column("config", postgresql.JSONB, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", onupdate="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Index("ix_mock_blueprint_year_status", "year", "status"),
        sa.Index("ix_mock_blueprint_updated_at", "updated_at"),
    )

    # mock_blueprint_version
    op.create_table(
        "mock_blueprint_version",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blueprint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mock_blueprint.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", onupdate="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("diff_summary", sa.Text(), nullable=True),
        sa.UniqueConstraint("blueprint_id", "version", name="uq_mock_blueprint_version_blueprint_version"),
        sa.Index("ix_mock_blueprint_version_blueprint_id", "blueprint_id"),
    )

    # mock_generation_run
    op.create_table(
        "mock_generation_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blueprint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mock_blueprint.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", generation_run_status_enum, nullable=False, server_default="queued"),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("config_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mock_blueprint_version.id", onupdate="CASCADE"), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", onupdate="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings", postgresql.JSONB, nullable=True),
        sa.Column("errors", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Index("ix_mock_generation_run_blueprint_created", "blueprint_id", "created_at"),
        sa.Index("ix_mock_generation_run_status", "status"),
    )

    # mock_instance
    op.create_table(
        "mock_instance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blueprint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mock_blueprint.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mock_generation_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("question_ids", postgresql.JSONB, nullable=False),
        sa.Column("meta", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Index("ix_mock_instance_blueprint_id", "blueprint_id"),
        sa.Index("ix_mock_instance_generation_run_id", "generation_run_id"),
        sa.Index("ix_mock_instance_created_at", "created_at"),
    )


def downgrade() -> None:
    op.drop_table("mock_instance")
    op.drop_table("mock_generation_run")
    op.drop_table("mock_blueprint_version")
    op.drop_table("mock_blueprint")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS mock_generation_run_status")
    op.execute("DROP TYPE IF EXISTS mock_blueprint_status")
    op.execute("DROP TYPE IF EXISTS mock_blueprint_mode")
