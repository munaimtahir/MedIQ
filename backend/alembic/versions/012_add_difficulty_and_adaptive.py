"""Add difficulty and adaptive tables

Revision ID: 012_difficulty_adaptive
Revises: 011_revision_queue
Create Date: 2026-01-21 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '012_difficulty_adaptive'
down_revision: Union[str, None] = '011_revision_queue'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create question_difficulty table
    op.create_table(
        'question_difficulty',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        
        # Difficulty metrics
        sa.Column('rating', sa.Numeric(8, 2), nullable=False, server_default='1000'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('p_correct', sa.Numeric(5, 4), nullable=True),
        
        # Audit
        sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Provenance
        sa.Column('algo_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('params_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('breakdown_json', postgresql.JSONB, nullable=False, server_default='{}'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['algo_version_id'], ['algo_versions.id'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['params_id'], ['algo_params.id'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['algo_runs.id'], onupdate='CASCADE'),
    )
    
    # Create indexes
    op.create_index('ix_question_difficulty_question_id', 'question_difficulty', ['question_id'])
    op.create_index('ix_question_difficulty_rating', 'question_difficulty', ['rating'])
    op.create_index('ix_question_difficulty_attempts', 'question_difficulty', ['attempts'])
    op.create_index('ix_question_difficulty_algo_version_id', 'question_difficulty', ['algo_version_id'])
    op.create_index('ix_question_difficulty_params_id', 'question_difficulty', ['params_id'])
    op.create_index('ix_question_difficulty_run_id', 'question_difficulty', ['run_id'])
    
    # Update difficulty v0 parameters
    op.execute("""
        UPDATE algo_params
        SET params_json = '{
            "baseline_rating": 1000,
            "k_factor": 16,
            "rating_scale": 400,
            "student_rating_strategy": "mastery_mapped",
            "mastery_rating_map": {
                "min": 800,
                "max": 1200
            }
        }'::jsonb,
        updated_at = now()
        WHERE algo_version_id IN (
            SELECT id FROM algo_versions WHERE algo_key = 'difficulty' AND version = 'v0'
        )
        AND is_active = true
    """)
    
    # Update adaptive v0 parameters
    op.execute("""
        UPDATE algo_params
        SET params_json = '{
            "anti_repeat_days": 14,
            "theme_mix": {
                "weak": 0.5,
                "medium": 0.3,
                "mixed": 0.2
            },
            "difficulty_targets": {
                "weak": [900, 1050],
                "medium": [1000, 1150],
                "strong": [1050, 1250]
            },
            "difficulty_bucket_limits": {
                "easy": [0, 950],
                "medium": [950, 1100],
                "hard": [1100, 9999]
            },
            "difficulty_mix": {
                "easy": 0.2,
                "medium": 0.6,
                "hard": 0.2
            },
            "fit_weights": {
                "mastery_inverse": 0.6,
                "difficulty_distance": 0.3,
                "freshness": 0.1
            }
        }'::jsonb,
        updated_at = now()
        WHERE algo_version_id IN (
            SELECT id FROM algo_versions WHERE algo_key = 'adaptive' AND version = 'v0'
        )
        AND is_active = true
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_question_difficulty_run_id')
    op.drop_index('ix_question_difficulty_params_id')
    op.drop_index('ix_question_difficulty_algo_version_id')
    op.drop_index('ix_question_difficulty_attempts')
    op.drop_index('ix_question_difficulty_rating')
    op.drop_index('ix_question_difficulty_question_id')
    
    # Drop table
    op.drop_table('question_difficulty')
