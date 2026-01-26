"""Add mfa_totp and mfa_backup_codes tables.

Revision ID: 036_mfa_tables
Revises: 035_users_extras
Create Date: 2026-01-24 19:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "036_mfa_tables"
down_revision: str | None = "035_users_extras"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mfa_totp (
            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            secret_encrypted VARCHAR NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            verified_at TIMESTAMP WITH TIME ZONE NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mfa_backup_codes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            code_hash VARCHAR NOT NULL,
            used_at TIMESTAMP WITH TIME ZONE NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mfa_backup_codes_user_id ON mfa_backup_codes(user_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_mfa_backup_codes_user_id")
    op.execute("DROP TABLE IF EXISTS mfa_backup_codes")
    op.execute("DROP TABLE IF EXISTS mfa_totp")
