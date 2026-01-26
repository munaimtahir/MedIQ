"""update_notifications_add_fields_and_preferences

Revision ID: d528775027ef
Revises: c13b59245b38
Create Date: 2026-01-25 01:15:00.761773

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd528775027ef'
down_revision = 'c13b59245b38'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to notifications table
    op.add_column('notifications', sa.Column('action_url', sa.Text(), nullable=True))
    op.add_column('notifications', sa.Column('severity', sa.Text(), nullable=False, server_default='info'))
    op.add_column('notifications', sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'))
    
    # Update existing rows: if read_at is set, mark is_read as true
    op.execute(text("""
        UPDATE notifications 
        SET is_read = true 
        WHERE read_at IS NOT NULL
    """))
    
    # Drop old indexes that will be replaced
    op.drop_index('ix_notifications_user_read', table_name='notifications')
    op.drop_index('ix_notifications_user_created', table_name='notifications')
    
    # Create new composite indexes as specified
    # Note: PostgreSQL doesn't support DESC in CREATE INDEX directly, need to use op.execute
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_notifications_user_created_at
        ON notifications(user_id, created_at DESC)
    """))
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_notifications_user_is_read_created_at
        ON notifications(user_id, is_read, created_at DESC)
    """))
    
    # Create user_notification_preferences table (optional, future-proof)
    op.create_table(
        'user_notification_preferences',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email_opt_in', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_opt_in', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('digest_frequency', sa.Text(), nullable=False, server_default='off'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )


def downgrade() -> None:
    op.drop_table('user_notification_preferences')
    op.drop_index('ix_notifications_user_is_read_created_at', table_name='notifications')
    op.drop_index('ix_notifications_user_created_at', table_name='notifications')
    op.create_index('ix_notifications_user_created', 'notifications', ['user_id', 'created_at'])
    op.create_index('ix_notifications_user_read', 'notifications', ['user_id', 'read_at'])
    op.drop_column('notifications', 'is_read')
    op.drop_column('notifications', 'severity')
    op.drop_column('notifications', 'action_url')

