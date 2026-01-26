"""Add platform_settings table

Revision ID: 002
Revises: 8e9f0123a4b
Create Date: 2024-01-01 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "8e9f0123a4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create platform_settings table
    op.create_table(
        "platform_settings",
        sa.Column("id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Insert default settings
    default_data = {
        "general": {
            "platform_name": "Exam Prep Platform",
            "platform_description": "",
            "default_language": "en",
            "timezone": "Asia/Karachi",
            "default_landing": "dashboard",
        },
        "academic_defaults": {"default_year_id": None, "blocks_visibility_mode": "user_selected"},
        "practice_defaults": {
            "default_mode": "tutor",
            "timer_default": "untimed",
            "review_policy": "always",
            "allow_mixed_blocks": True,
            "allow_any_block_anytime": True,
        },
        "security": {
            "access_token_minutes": 30,
            "refresh_token_days": 14,
            "force_logout_on_password_reset": True,
        },
        "notifications": {
            "password_reset_emails_enabled": True,
            "practice_reminders_enabled": False,
            "admin_alerts_enabled": False,
            "inapp_announcements_enabled": True,
        },
        "version": 1,
    }

    # Insert default settings
    import json

    op.execute(
        f"""
        INSERT INTO platform_settings (id, data)
        VALUES (1, '{json.dumps(default_data)}'::jsonb)
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("platform_settings")
