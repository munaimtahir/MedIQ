"""Add import schema tables and questions.external_id

Revision ID: 006
Revises: 005
Create Date: 2026-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'  # Update this to match your latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    op.execute("CREATE TYPE import_file_type AS ENUM ('csv', 'json')")
    op.execute("CREATE TYPE import_job_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')")

    # Create import_schemas table
    op.create_table(
        'import_schemas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('file_type', sa.Enum('csv', 'json', name='import_file_type', create_type=False), nullable=False, server_default='csv'),
        sa.Column('delimiter', sa.String(5), nullable=False, server_default=','),
        sa.Column('quote_char', sa.String(5), nullable=False, server_default='"'),
        sa.Column('has_header', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('encoding', sa.String(20), nullable=False, server_default='utf-8'),
        sa.Column('mapping_json', postgresql.JSONB, nullable=False),
        sa.Column('rules_json', postgresql.JSONB, nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', onupdate='CASCADE'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
        sa.UniqueConstraint('name', 'version', name='uq_import_schema_name_version'),
    )
    op.create_index('ix_import_schemas_is_active', 'import_schemas', ['is_active'])
    op.create_index('ix_import_schemas_name', 'import_schemas', ['name'])

    # Create import_jobs table
    op.create_table(
        'import_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('schema_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('import_schemas.id', onupdate='CASCADE', ondelete='SET NULL'), nullable=True),
        sa.Column('schema_name', sa.String(200), nullable=False),
        sa.Column('schema_version', sa.Integer, nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', onupdate='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_type', sa.Enum('csv', 'json', name='import_file_type', create_type=False), nullable=False),
        sa.Column('dry_run', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', name='import_job_status', create_type=False), nullable=False, server_default='PENDING'),
        sa.Column('total_rows', sa.Integer, nullable=False, server_default='0'),
        sa.Column('accepted_rows', sa.Integer, nullable=False, server_default='0'),
        sa.Column('rejected_rows', sa.Integer, nullable=False, server_default='0'),
        sa.Column('summary_json', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_import_jobs_status', 'import_jobs', ['status'])
    op.create_index('ix_import_jobs_created_by', 'import_jobs', ['created_by'])
    op.create_index('ix_import_jobs_created_at', 'import_jobs', ['created_at'])

    # Create import_job_rows table
    op.create_table(
        'import_job_rows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('import_jobs.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('row_number', sa.Integer, nullable=False),
        sa.Column('external_id', sa.String(200), nullable=True),
        sa.Column('raw_row_json', postgresql.JSONB, nullable=False),
        sa.Column('errors_json', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_import_job_rows_job_id', 'import_job_rows', ['job_id'])
    op.create_index('ix_import_job_rows_row_number', 'import_job_rows', ['row_number'])

    # Add external_id column to questions table
    op.add_column('questions', sa.Column('external_id', sa.String(200), nullable=True))
    op.create_index('ix_questions_external_id', 'questions', ['external_id'])

    # Insert default CSV schema
    default_schema_id = str(uuid.uuid4())
    op.execute(f"""
        INSERT INTO import_schemas (
            id, name, version, is_active, file_type, delimiter, quote_char, has_header, encoding,
            mapping_json, rules_json, created_at
        ) VALUES (
            '{default_schema_id}',
            'Default MCQ CSV v1',
            1,
            true,
            'csv',
            ',',
            '"',
            true,
            'utf-8',
            '{{"external_id": {{"column": "external_id"}},
              "year": {{"column": "year"}},
              "block": {{"column": "block"}},
              "theme": {{"column": "theme"}},
              "cognitive": {{"column": "cognitive"}},
              "difficulty": {{"column": "difficulty"}},
              "stem": {{"column": "stem"}},
              "option_a": {{"column": "option_a"}},
              "option_b": {{"column": "option_b"}},
              "option_c": {{"column": "option_c"}},
              "option_d": {{"column": "option_d"}},
              "option_e": {{"column": "option_e"}},
              "correct": {{"column": "correct", "format": "letter"}},
              "explanation_md": {{"column": "explanation"}},
              "source_book": {{"column": "source_book"}},
              "source_page": {{"column": "source_page"}}}}',
            '{{"required": ["year", "block", "theme", "stem", "option_a", "option_b", "option_c", "option_d", "option_e", "correct"],
              "correct_format": "letter",
              "default_status": "DRAFT",
              "strict_tag_resolution": true}}',
            NOW()
        )
    """)


def downgrade() -> None:
    # Remove external_id from questions
    op.drop_index('ix_questions_external_id', table_name='questions')
    op.drop_column('questions', 'external_id')

    # Drop tables
    op.drop_index('ix_import_job_rows_row_number', table_name='import_job_rows')
    op.drop_index('ix_import_job_rows_job_id', table_name='import_job_rows')
    op.drop_table('import_job_rows')

    op.drop_index('ix_import_jobs_created_at', table_name='import_jobs')
    op.drop_index('ix_import_jobs_created_by', table_name='import_jobs')
    op.drop_index('ix_import_jobs_status', table_name='import_jobs')
    op.drop_table('import_jobs')

    op.drop_index('ix_import_schemas_name', table_name='import_schemas')
    op.drop_index('ix_import_schemas_is_active', table_name='import_schemas')
    op.drop_table('import_schemas')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS import_job_status')
    op.execute('DROP TYPE IF EXISTS import_file_type')
