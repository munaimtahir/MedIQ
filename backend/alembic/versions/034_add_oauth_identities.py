"""Add oauth_identities table for OAuth provider linking.

Revision ID: 034_add_oauth_identities
Revises: 033_fix_rank_snapshot_unique
Create Date: 2026-01-24 16:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "034_add_oauth_identities"
down_revision: str | None = "033_fix_rank_snapshot_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_identities (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider VARCHAR NOT NULL,
            provider_subject VARCHAR NOT NULL,
            email_at_link_time VARCHAR NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT uq_oauth_provider_subject UNIQUE (provider, provider_subject)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_oauth_identities_user_id ON oauth_identities(user_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_oauth_identities_user_id")
    op.execute("DROP TABLE IF EXISTS oauth_identities")
