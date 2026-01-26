"""Add perf_request_log table for lightweight performance observability.

Revision ID: 038_perf_request_log
Revises: 037_auth_tokens
Create Date: 2026-01-24 20:30:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "038_perf_request_log"
down_revision: str | None = "037_auth_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS perf_request_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            method VARCHAR(10) NOT NULL,
            path VARCHAR(300) NOT NULL,
            status_code INTEGER NOT NULL,
            total_ms INTEGER NOT NULL,
            db_total_ms INTEGER NOT NULL DEFAULT 0,
            db_query_count INTEGER NOT NULL DEFAULT 0,
            user_role VARCHAR(20) NULL,
            request_id VARCHAR(64) NULL,
            sampled BOOLEAN NOT NULL DEFAULT false
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_perf_request_log_request_at ON perf_request_log(request_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_perf_request_log_path_request_at ON perf_request_log(path, request_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_perf_request_log_total_ms ON perf_request_log(total_ms)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_perf_request_log_total_ms")
    op.execute("DROP INDEX IF EXISTS ix_perf_request_log_path_request_at")
    op.execute("DROP INDEX IF EXISTS ix_perf_request_log_request_at")
    op.execute("DROP TABLE IF EXISTS perf_request_log")

