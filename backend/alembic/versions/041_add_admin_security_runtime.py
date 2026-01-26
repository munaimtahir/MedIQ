"""Add admin_security_runtime table for admin freeze.

Revision ID: 041_admin_security_runtime
Revises: 040_auth_sessions
Create Date: 2026-01-25 13:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "041_admin_security_runtime"
down_revision: str | None = "040_auth_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create admin_security_runtime table (singleton)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_security_runtime (
            id INTEGER PRIMARY KEY DEFAULT 1,
            admin_freeze BOOLEAN NOT NULL DEFAULT false,
            freeze_reason TEXT NULL,
            set_by_user_id UUID NULL REFERENCES users(id),
            set_at TIMESTAMP WITH TIME ZONE NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    
    # Insert default row (singleton)
    op.execute(
        """
        INSERT INTO admin_security_runtime (id, admin_freeze)
        VALUES (1, false)
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS admin_security_runtime")
