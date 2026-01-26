"""Add DB-level integrity constraints

Revision ID: 045_integrity
Revises: 044_merge
Create Date: 2026-01-25

- test_sessions: CHECK (status='SUBMITTED' => submitted_at IS NOT NULL)
- session_answers: UNIQUE(session_id, question_id) already; CHECK selected_index 0..4 or NULL
- attempt_events: append-only triggers (no UPDATE/DELETE)
- difficulty_update_log: UNIQUE(attempt_id) already
- mistake_log: UNIQUE(session_id, question_id) already
"""

from alembic import op
from sqlalchemy import text

revision = "045_integrity"
down_revision = "044_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) test_sessions: (status = 'SUBMITTED') => submitted_at IS NOT NULL
    op.execute(
        text("""
        ALTER TABLE test_sessions
        ADD CONSTRAINT chk_test_sessions_submitted_at
        CHECK (status::text <> 'SUBMITTED' OR submitted_at IS NOT NULL)
        """)
    )

    # 2) session_answers: selected_index IS NULL OR 0..4
    op.execute(
        text("""
        ALTER TABLE session_answers
        ADD CONSTRAINT chk_session_answers_selected_index
        CHECK (selected_index IS NULL OR (selected_index >= 0 AND selected_index <= 4))
        """)
    )

    # 3) attempt_events: append-only (no UPDATE/DELETE)
    op.execute(
        text("""
        CREATE OR REPLACE FUNCTION raise_on_attempt_events_mutate()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'attempt_events is append-only: UPDATE/DELETE not allowed'
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$ LANGUAGE plpgsql;
        """)
    )
    op.execute(
        text("""
        DROP TRIGGER IF EXISTS trg_attempt_events_no_update ON attempt_events;
        CREATE TRIGGER trg_attempt_events_no_update
            BEFORE UPDATE ON attempt_events
            FOR EACH ROW EXECUTE FUNCTION raise_on_attempt_events_mutate();
        """)
    )
    op.execute(
        text("""
        DROP TRIGGER IF EXISTS trg_attempt_events_no_delete ON attempt_events;
        CREATE TRIGGER trg_attempt_events_no_delete
            BEFORE DELETE ON attempt_events
            FOR EACH ROW EXECUTE FUNCTION raise_on_attempt_events_mutate();
        """)
    )


def downgrade() -> None:
    op.execute(text("ALTER TABLE test_sessions DROP CONSTRAINT IF EXISTS chk_test_sessions_submitted_at"))
    op.execute(text("ALTER TABLE session_answers DROP CONSTRAINT IF EXISTS chk_session_answers_selected_index"))
    op.execute(text("DROP TRIGGER IF EXISTS trg_attempt_events_no_update ON attempt_events"))
    op.execute(text("DROP TRIGGER IF EXISTS trg_attempt_events_no_delete ON attempt_events"))
    op.execute(text("DROP FUNCTION IF EXISTS raise_on_attempt_events_mutate()"))