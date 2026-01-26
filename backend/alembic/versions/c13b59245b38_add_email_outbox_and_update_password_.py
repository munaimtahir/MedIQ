"""add_email_outbox_and_update_password_reset

Revision ID: c13b59245b38
Revises: bcf3b79b26b2
Create Date: 2026-01-25 01:04:41.568578

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c13b59245b38'
down_revision = 'bcf3b79b26b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create email_outbox table
    op.create_table(
        'email_outbox',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('to_email', sa.Text(), nullable=False),
        sa.Column('to_name', sa.Text(), nullable=True),
        sa.Column('subject', sa.Text(), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('template_key', sa.Text(), nullable=False),
        sa.Column('template_vars', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('status', sa.Text(), nullable=False),  # queued|sending|sent|failed|blocked_disabled|blocked_frozen|shadow_logged
        sa.Column('provider', sa.Text(), nullable=True),  # smtp|sendgrid|ses|none|console
        sa.Column('provider_message_id', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes for email_outbox
    op.create_index('ix_email_outbox_status_created_at', 'email_outbox', ['status', 'created_at'])
    op.create_index('ix_email_outbox_to_email_created_at', 'email_outbox', ['to_email', sa.text('created_at DESC')])
    
    # Add requested_ip and requested_ua to password_reset_tokens
    op.add_column('password_reset_tokens', sa.Column('requested_ip', sa.Text(), nullable=True))
    op.add_column('password_reset_tokens', sa.Column('requested_ua', sa.Text(), nullable=True))
    
    # Create index on expires_at for password_reset_tokens
    op.create_index('ix_password_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'])
    
    # Create email_runtime_config table (singleton, similar to algo_runtime_config)
    op.create_table(
        'email_runtime_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('requested_mode', sa.Text(), nullable=False, server_default='disabled'),  # disabled|shadow|active
        sa.Column('email_freeze', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('changed_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('config_json', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], onupdate='CASCADE'),
    )
    
    # Create singleton row for email_runtime_config
    op.execute(
        """
        INSERT INTO email_runtime_config (id, requested_mode, config_json)
        SELECT gen_random_uuid(), 'disabled'::text,
               '{"requested_mode": "disabled", "email_freeze": false}'::jsonb
        WHERE NOT EXISTS (SELECT 1 FROM email_runtime_config LIMIT 1)
        """
    )
    
    # Create email_switch_event table for audit trail
    op.create_table(
        'email_switch_event',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('previous_config', postgresql.JSONB(), nullable=False),
        sa.Column('new_config', postgresql.JSONB(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], onupdate='CASCADE'),
    )
    op.create_index('ix_email_switch_event_created_at', 'email_switch_event', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_email_switch_event_created_at', table_name='email_switch_event')
    op.drop_table('email_switch_event')
    op.drop_table('email_runtime_config')
    op.drop_index('ix_password_reset_tokens_expires_at', table_name='password_reset_tokens')
    op.drop_column('password_reset_tokens', 'requested_ua')
    op.drop_column('password_reset_tokens', 'requested_ip')
    op.drop_index('ix_email_outbox_to_email_created_at', table_name='email_outbox')
    op.drop_index('ix_email_outbox_status_created_at', table_name='email_outbox')
    op.drop_table('email_outbox')

