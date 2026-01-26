"""Add auth_sessions table and update refresh_tokens for rotation.

Revision ID: 040_auth_sessions
Revises: 039_add_high_roi_perf_indexes
Create Date: 2026-01-25 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "040_auth_sessions"
down_revision: str | None = "039_high_roi_perf_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create auth_sessions table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            user_agent TEXT NULL,
            ip_address TEXT NULL,
            revoked_at TIMESTAMP WITH TIME ZONE NULL,
            revoke_reason TEXT NULL
        )
        """
    )
    
    # Create indexes for auth_sessions
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id_created_at ON auth_sessions(user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_auth_sessions_revoked_at ON auth_sessions(revoked_at)"
    )
    
    # Add session_id and rotated_at to refresh_tokens
    op.execute(
        "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS session_id UUID NULL REFERENCES auth_sessions(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS rotated_at TIMESTAMP WITH TIME ZONE NULL"
    )
    
    # Create indexes for refresh_tokens
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_session_id_issued_at ON refresh_tokens(session_id, issued_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_expires_at ON refresh_tokens(expires_at)"
    )


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_refresh_tokens_expires_at")
    op.execute("DROP INDEX IF EXISTS ix_refresh_tokens_session_id_issued_at")
    op.execute("DROP INDEX IF EXISTS ix_auth_sessions_revoked_at")
    op.execute("DROP INDEX IF EXISTS ix_auth_sessions_user_id_created_at")
    
    # Drop columns from refresh_tokens
    op.execute("ALTER TABLE refresh_tokens DROP COLUMN IF EXISTS rotated_at")
    op.execute("ALTER TABLE refresh_tokens DROP COLUMN IF EXISTS session_id")
    
    # Drop auth_sessions table
    op.execute("DROP TABLE IF EXISTS auth_sessions")
