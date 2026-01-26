"""Add high-ROI indexes for hot paths.

Revision ID: 039_high_roi_perf_indexes
Revises: 038_perf_request_log
Create Date: 2026-01-24 21:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "039_high_roi_perf_indexes"
down_revision: str | None = "038_perf_request_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NOTE: For large tables, CONCURRENTLY reduces lock impact.
    # Alembic must run CONCURRENTLY outside a transaction.
    ctx = op.get_context()
    with ctx.autocommit_block():
        # Legacy attempt tables (older practice flow) - only if tables exist
        # Check if attempt_sessions exists before creating index
        conn = op.get_bind()
        result = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'attempt_sessions'
            )
            """)
        )
        if result.scalar():
            op.execute(
                text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attempt_sessions_user_started_at
                ON attempt_sessions(user_id, started_at DESC)
                """)
            )
        
        result = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'attempt_answers'
            )
            """)
        )
        if result.scalar():
            op.execute(
                text("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attempt_answers_session_id ON attempt_answers(session_id)")
            )
            op.execute(
                text("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attempt_answers_question_id ON attempt_answers(question_id)")
            )

        # Revision queue hot filters
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_revision_queue_user_due_date ON revision_queue(user_id, due_date)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_revision_queue_user_status ON revision_queue(user_id, status)"
        )

        # CMS questions list filters
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_questions_theme_id_status ON questions(theme_id, status)"
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_questions_theme_id_status")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_revision_queue_user_status")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_revision_queue_user_due_date")
        # Only drop if indexes exist (tables may not exist)
        conn = op.get_bind()
        result = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE indexname = 'ix_attempt_answers_question_id'
            )
            """)
        )
        if result.scalar():
            op.execute(text("DROP INDEX CONCURRENTLY IF EXISTS ix_attempt_answers_question_id"))
        result = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE indexname = 'ix_attempt_answers_session_id'
            )
            """)
        )
        if result.scalar():
            op.execute(text("DROP INDEX CONCURRENTLY IF EXISTS ix_attempt_answers_session_id"))
        result = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE indexname = 'ix_attempt_sessions_user_started_at'
            )
            """)
        )
        if result.scalar():
            op.execute(text("DROP INDEX CONCURRENTLY IF EXISTS ix_attempt_sessions_user_started_at"))

