"""add_notifications_table

Revision ID: 8e9f0123a4b
Revises: 7d8e9f0123a
Create Date: 2026-01-16 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "8e9f0123a4b"
down_revision = "7d8e9f0123a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notifications table
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"], unique=False)
    # Composite index for common queries
    op.create_index(
        "ix_notifications_user_created", "notifications", ["user_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_notifications_user_read", "notifications", ["user_id", "read_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_read", table_name="notifications")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_notifications_read_at", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
