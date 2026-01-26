"""Add onboarding_completed, email_verified, last_login_at to users.

Revision ID: 035_users_onboarding_email_verified
Revises: 034_add_oauth_identities
Create Date: 2026-01-24 18:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "035_users_extras"
down_revision: str | None = "034_add_oauth_identities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'onboarding_completed'
            ) THEN
                ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT false;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'email_verified'
            ) THEN
                ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT false;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'last_login_at'
            ) THEN
                ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE users DROP COLUMN IF EXISTS onboarding_completed;
        ALTER TABLE users DROP COLUMN IF EXISTS email_verified;
        ALTER TABLE users DROP COLUMN IF EXISTS last_login_at;
        """
    )
