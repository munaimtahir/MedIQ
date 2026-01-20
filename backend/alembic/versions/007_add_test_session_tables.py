"""Add test session tables

Revision ID: 007
Revises: 006
Create Date: 2026-01-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    op.execute("CREATE TYPE session_mode AS ENUM ('TUTOR', 'EXAM')")
    op.execute("CREATE TYPE session_status AS ENUM ('ACTIVE', 'SUBMITTED', 'EXPIRED')")

    # Create test_sessions table
    op.create_table(
        'test_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', onupdate='CASCADE'), nullable=False),
        sa.Column('mode', sa.Enum('TUTOR', 'EXAM', name='session_mode', create_type=False), nullable=False, server_default='TUTOR'),
        sa.Column('status', sa.Enum('ACTIVE', 'SUBMITTED', 'EXPIRED', name='session_status', create_type=False), nullable=False, server_default='ACTIVE'),
        sa.Column('year', sa.Integer, nullable=False),
        sa.Column('blocks_json', postgresql.JSONB, nullable=False),
        sa.Column('themes_json', postgresql.JSONB, nullable=True),
        sa.Column('total_questions', sa.Integer, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('score_correct', sa.Integer, nullable=True),
        sa.Column('score_total', sa.Integer, nullable=True),
        sa.Column('score_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_test_sessions_user_created', 'test_sessions', ['user_id', 'created_at'])
    op.create_index('ix_test_sessions_status', 'test_sessions', ['status'])
    op.create_index('ix_test_sessions_expires_at', 'test_sessions', ['expires_at'])

    # Create session_questions table
    op.create_table(
        'session_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_sessions.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('position', sa.Integer, nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('questions.id', onupdate='CASCADE'), nullable=False),
        sa.Column('question_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('question_versions.id', onupdate='CASCADE'), nullable=True),
        sa.Column('snapshot_json', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('session_id', 'position', name='uq_session_question_position'),
        sa.UniqueConstraint('session_id', 'question_id', name='uq_session_question_id'),
    )
    op.create_index('ix_session_questions_session_id', 'session_questions', ['session_id'])

    # Create session_answers table
    op.create_table(
        'session_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_sessions.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('questions.id', onupdate='CASCADE'), nullable=False),
        sa.Column('selected_index', sa.SmallInteger, nullable=True),
        sa.Column('is_correct', sa.Boolean, nullable=True),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('changed_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('marked_for_review', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
        sa.UniqueConstraint('session_id', 'question_id', name='uq_session_answer'),
    )
    op.create_index('ix_session_answers_session_id', 'session_answers', ['session_id'])

    # Create attempt_events table
    op.create_table(
        'attempt_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_sessions.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', onupdate='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_ts', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('payload_json', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_attempt_events_session_ts', 'attempt_events', ['session_id', 'event_ts'])


def downgrade() -> None:
    # Drop tables
    op.drop_index('ix_attempt_events_session_ts', table_name='attempt_events')
    op.drop_table('attempt_events')

    op.drop_index('ix_session_answers_session_id', table_name='session_answers')
    op.drop_table('session_answers')

    op.drop_index('ix_session_questions_session_id', table_name='session_questions')
    op.drop_table('session_questions')

    op.drop_index('ix_test_sessions_expires_at', table_name='test_sessions')
    op.drop_index('ix_test_sessions_status', table_name='test_sessions')
    op.drop_index('ix_test_sessions_user_created', table_name='test_sessions')
    op.drop_table('test_sessions')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS session_status')
    op.execute('DROP TYPE IF EXISTS session_mode')
