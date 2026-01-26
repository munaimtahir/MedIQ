"""Add refresh_tokens and password_reset_tokens tables.

Revision ID: 037_auth_tokens
Revises: 036_mfa_tables
Create Date: 2026-01-24 19:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "037_auth_tokens"
down_revision: str | None = "036_mfa_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR NOT NULL UNIQUE,
            issued_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            revoked_at TIMESTAMP WITH TIME ZONE NULL,
            replaced_by_token_id UUID NULL REFERENCES refresh_tokens(id),
            user_agent VARCHAR NULL,
            ip_address VARCHAR NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens(user_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens(token_hash)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR NOT NULL UNIQUE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            used_at TIMESTAMP WITH TIME ZONE NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id ON password_reset_tokens(user_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_password_reset_tokens_token_hash ON password_reset_tokens(token_hash)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR NOT NULL UNIQUE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            used_at TIMESTAMP WITH TIME ZONE NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_email_verification_tokens_user_id ON email_verification_tokens(user_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_email_verification_tokens_token_hash ON email_verification_tokens(token_hash)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_email_verification_tokens_token_hash")
    op.execute("DROP INDEX IF EXISTS ix_email_verification_tokens_user_id")
    op.execute("DROP TABLE IF EXISTS email_verification_tokens")
    op.execute("DROP INDEX IF EXISTS ix_password_reset_tokens_token_hash")
    op.execute("DROP INDEX IF EXISTS ix_password_reset_tokens_user_id")
    op.execute("DROP TABLE IF EXISTS password_reset_tokens")
    op.execute("DROP INDEX IF EXISTS ix_refresh_tokens_token_hash")
    op.execute("DROP INDEX IF EXISTS ix_refresh_tokens_user_id")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
