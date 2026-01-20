"""Add revision_queue table

Revision ID: 011_revision_queue
Revises: 010_user_theme_mastery
Create Date: 2026-01-21 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011_revision_queue'
down_revision: Union[str, None] = '010_user_theme_mastery'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create revision_queue table
    op.create_table(
        'revision_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('block_id', sa.Integer(), nullable=False),
        sa.Column('theme_id', sa.Integer(), nullable=False),
        
        # Scheduling
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('priority_score', sa.Numeric(5, 2), nullable=False),
        sa.Column('recommended_count', sa.Integer(), nullable=False),
        
        # State
        sa.Column('status', sa.String(20), nullable=False, server_default='DUE'),
        
        # Explainability
        sa.Column('reason_json', postgresql.JSONB, nullable=False, server_default='{}'),
        
        # Audit / provenance
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('algo_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('params_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['block_id'], ['blocks.id'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['algo_version_id'], ['algo_versions.id'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['params_id'], ['algo_params.id'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['algo_runs.id'], onupdate='CASCADE'),
        
        # Unique constraint
        sa.UniqueConstraint('user_id', 'theme_id', 'due_date', name='uq_revision_queue_user_theme_date'),
    )
    
    # Create indexes
    op.create_index('ix_revision_queue_user_id', 'revision_queue', ['user_id'])
    op.create_index('ix_revision_queue_user_id_due_date_status', 'revision_queue', ['user_id', 'due_date', 'status'])
    op.create_index('ix_revision_queue_user_id_priority_score', 'revision_queue', ['user_id', 'priority_score'], postgresql_using='btree')
    op.create_index('ix_revision_queue_algo_version_id', 'revision_queue', ['algo_version_id'])
    op.create_index('ix_revision_queue_params_id', 'revision_queue', ['params_id'])
    op.create_index('ix_revision_queue_run_id', 'revision_queue', ['run_id'])
    
    # Update revision v0 parameters to new spec
    op.execute("""
        UPDATE algo_params
        SET params_json = '{
            "horizon_days": 7,
            "min_attempts": 5,
            "mastery_bands": [
                {"name": "weak", "max": 0.39},
                {"name": "medium", "max": 0.69},
                {"name": "strong", "max": 0.84},
                {"name": "mastered", "max": 1.00}
            ],
            "spacing_days": {
                "weak": 1,
                "medium": 2,
                "strong": 5,
                "mastered": 12
            },
            "question_counts": {
                "weak": [15, 20],
                "medium": [10, 15],
                "strong": [5, 10],
                "mastered": [5, 5]
            },
            "priority_weights": {
                "mastery_inverse": 70,
                "recency": 2,
                "low_data_bonus": 10
            }
        }'::jsonb,
        updated_at = now()
        WHERE algo_version_id IN (
            SELECT id FROM algo_versions WHERE algo_key = 'revision' AND version = 'v0'
        )
        AND is_active = true
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_revision_queue_run_id')
    op.drop_index('ix_revision_queue_params_id')
    op.drop_index('ix_revision_queue_algo_version_id')
    op.drop_index('ix_revision_queue_user_id_priority_score')
    op.drop_index('ix_revision_queue_user_id_due_date_status')
    op.drop_index('ix_revision_queue_user_id')
    
    # Drop table
    op.drop_table('revision_queue')
