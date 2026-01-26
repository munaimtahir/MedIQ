"""Extend attempt_events table for full telemetry envelope

Revision ID: 009
Revises: 008
Create Date: 2026-01-20 17:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to attempt_events
    op.add_column(
        "attempt_events", sa.Column("event_version", sa.Integer, nullable=False, server_default="1")
    )
    op.add_column(
        "attempt_events", sa.Column("client_ts", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("attempt_events", sa.Column("seq", sa.Integer, nullable=True))
    op.add_column(
        "attempt_events",
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("questions.id", onupdate="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column("attempt_events", sa.Column("source", sa.String(50), nullable=True))

    # Update payload_json to have default
    op.alter_column(
        "attempt_events",
        "payload_json",
        existing_type=postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )

    # Create new indexes
    op.create_index("ix_attempt_events_event_type", "attempt_events", ["event_type"])
    op.create_index("ix_attempt_events_event_ts", "attempt_events", ["event_ts"])
    op.create_index("ix_attempt_events_user_id", "attempt_events", ["user_id"])
    op.create_index("ix_attempt_events_question_id", "attempt_events", ["question_id"])
    op.create_index("ix_attempt_events_user_ts", "attempt_events", ["user_id", "event_ts"])
    op.create_index("ix_attempt_events_type_ts", "attempt_events", ["event_type", "event_ts"])
    op.create_index("ix_attempt_events_session_seq", "attempt_events", ["session_id", "seq"])


def downgrade() -> None:
    # Drop new indexes
    op.drop_index("ix_attempt_events_session_seq", table_name="attempt_events")
    op.drop_index("ix_attempt_events_type_ts", table_name="attempt_events")
    op.drop_index("ix_attempt_events_user_ts", table_name="attempt_events")
    op.drop_index("ix_attempt_events_question_id", table_name="attempt_events")
    op.drop_index("ix_attempt_events_user_id", table_name="attempt_events")
    op.drop_index("ix_attempt_events_event_ts", table_name="attempt_events")
    op.drop_index("ix_attempt_events_event_type", table_name="attempt_events")

    # Remove added columns
    op.drop_column("attempt_events", "source")
    op.drop_column("attempt_events", "question_id")
    op.drop_column("attempt_events", "seq")
    op.drop_column("attempt_events", "client_ts")
    op.drop_column("attempt_events", "event_version")

    # Revert payload_json
    op.alter_column(
        "attempt_events",
        "payload_json",
        existing_type=postgresql.JSONB,
        nullable=True,
        server_default=None,
    )
