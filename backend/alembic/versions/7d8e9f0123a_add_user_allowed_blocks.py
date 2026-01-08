"""add_user_allowed_blocks

Revision ID: 7d8e9f0123a
Revises: 6c7d8e9f0123
Create Date: 2026-01-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '7d8e9f0123a'
down_revision = '6c7d8e9f0123'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_allowed_blocks table
    op.create_table(
        'user_allowed_blocks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('year_id', sa.Integer(), nullable=False),
        sa.Column('block_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['year_id'], ['years.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['block_id'], ['blocks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'year_id', 'block_id', name='uq_user_allowed_block')
    )
    op.create_index('ix_user_allowed_blocks_user_year', 'user_allowed_blocks', ['user_id', 'year_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_allowed_blocks_user_year', table_name='user_allowed_blocks')
    op.drop_table('user_allowed_blocks')
