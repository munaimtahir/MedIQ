"""add_session_performance_indexes

Revision ID: bcf3b79b26b2
Revises: 039_high_roi_perf_indexes
Create Date: 2026-01-25 00:35:24.351902

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "bcf3b79b26b2"
down_revision = "039_high_roi_perf_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes for session player hot paths."""
    # NOTE: CONCURRENTLY reduces lock impact on large tables
    ctx = op.get_context()
    with ctx.autocommit_block():
        # Composite index for session_questions: (session_id, position)
        # Used by GET /question?index=X and prefetch queries
        # Note: UniqueConstraint already creates an index, but explicit composite helps query planner
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_session_questions_session_position
            ON session_questions(session_id, position)
            """
        )

        # Composite index for session_answers: (session_id, question_id)
        # Used by answer lookup in question endpoint
        # Note: UniqueConstraint already creates an index, but explicit composite helps
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_session_answers_session_question
            ON session_answers(session_id, question_id)
            """
        )

        # Index on session_answers.question_id for reverse lookups (if needed)
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_session_answers_question_id
            ON session_answers(question_id)
            """
        )


def downgrade() -> None:
    """Remove session performance indexes."""
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_session_questions_session_position")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_session_answers_session_question")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_session_answers_question_id")

