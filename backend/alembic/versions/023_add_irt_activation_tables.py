"""Add IRT activation policy tables.

Revision ID: 023_irt_activation
Revises: 022_irt_tables
Create Date: 2026-01-25 12:00:00.000000

Adds tables for IRT activation policy:
- irt_activation_policy: Policy configuration and thresholds
- irt_activation_decision: Activation decisions per run
- irt_activation_event: Immutable audit log of activation events
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "023_irt_activation"
down_revision: str | None = "022_irt_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum for activation event type
    event_type_enum = postgresql.ENUM(
        "EVALUATED", "ACTIVATED", "DEACTIVATED", "ROLLED_BACK", name="irt_activation_event_type", create_type=False
    )
    event_type_enum.create(op.get_bind(), checkfirst=True)

    # irt_activation_policy
    op.create_table(
        "irt_activation_policy",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_version", sa.String(50), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_irt_activation_policy_version", "irt_activation_policy", ["policy_version"])

    # irt_activation_decision
    op.create_table(
        "irt_activation_decision",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.String(50), nullable=False),
        sa.Column("decision_json", postgresql.JSONB, nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["irt_calibration_run.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE"),
    )
    op.create_index("ix_irt_activation_decision_run_id", "irt_activation_decision", ["run_id"])
    op.create_index("ix_irt_activation_decision_eligible", "irt_activation_decision", ["eligible"])
    op.create_index("ix_irt_activation_decision_created_at", "irt_activation_decision", ["created_at"])

    # irt_activation_event
    op.create_table(
        "irt_activation_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", event_type_enum, nullable=False),
        sa.Column("previous_state", postgresql.JSONB, nullable=True),
        sa.Column("new_state", postgresql.JSONB, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_version", sa.String(50), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["irt_calibration_run.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE"),
    )
    op.create_index("ix_irt_activation_event_type", "irt_activation_event", ["event_type"])
    op.create_index("ix_irt_activation_event_created_at", "irt_activation_event", ["created_at"])
    op.create_index("ix_irt_activation_event_run_id", "irt_activation_event", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_irt_activation_event_run_id", table_name="irt_activation_event")
    op.drop_index("ix_irt_activation_event_created_at", table_name="irt_activation_event")
    op.drop_index("ix_irt_activation_event_type", table_name="irt_activation_event")
    op.drop_table("irt_activation_event")

    op.drop_index("ix_irt_activation_decision_created_at", table_name="irt_activation_decision")
    op.drop_index("ix_irt_activation_decision_eligible", table_name="irt_activation_decision")
    op.drop_index("ix_irt_activation_decision_run_id", table_name="irt_activation_decision")
    op.drop_table("irt_activation_decision")

    op.drop_index("ix_irt_activation_policy_version", table_name="irt_activation_policy")
    op.drop_table("irt_activation_policy")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS irt_activation_event_type")
