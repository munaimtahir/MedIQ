"""Add system_flags table and exam_mode_at_start column

Revision ID: 042
Revises: 041
Create Date: 2026-01-25 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "042"
down_revision = "041_admin_security_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create system_flags table
    op.create_table(
        "system_flags",
        sa.Column("key", sa.String(100), primary_key=True, nullable=False),
        sa.Column("value", sa.Boolean(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_system_flags_key", "system_flags", ["key"], unique=True)

    # Seed EXAM_MODE=false
    op.execute(
        """
        INSERT INTO system_flags (key, value, updated_at, updated_by, reason)
        VALUES ('EXAM_MODE', false, now(), NULL, 'Initial seed')
        ON CONFLICT (key) DO NOTHING
        """
    )

    # Add exam_mode_at_start column to test_sessions
    op.add_column(
        "test_sessions",
        sa.Column(
            "exam_mode_at_start",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    # Remove exam_mode_at_start column
    op.drop_column("test_sessions", "exam_mode_at_start")

    # Drop system_flags table
    op.drop_index("ix_system_flags_key", table_name="system_flags")
    op.drop_table("system_flags")
