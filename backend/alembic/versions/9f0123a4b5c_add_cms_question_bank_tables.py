"""add_cms_question_bank_tables

Revision ID: 9f0123a4b5c
Revises: 8e9f0123a4b
Create Date: 2026-01-17 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "9f0123a4b5c"
down_revision = "8e9f0123a4b"
depends_on = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums (only if they don't exist)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE question_status AS ENUM ('DRAFT', 'IN_REVIEW', 'APPROVED', 'PUBLISHED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE change_kind AS ENUM ('CREATE', 'EDIT', 'STATUS_CHANGE', 'PUBLISH', 'UNPUBLISH', 'IMPORT');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE storage_provider AS ENUM ('LOCAL', 'S3');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE media_role AS ENUM ('STEM', 'EXPLANATION', 'OPTION_A', 'OPTION_B', 'OPTION_C', 'OPTION_D', 'OPTION_E');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Handle existing questions table: rename to questions_legacy if it exists and has Integer id
    # Check if old questions table exists with Integer primary key
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'questions'
        )
    """))
    table_exists = result.scalar()
    
    if table_exists:
        # Check if it's the old table (Integer id) or new table (UUID id)
        result = connection.execute(sa.text("""
            SELECT data_type FROM information_schema.columns 
            WHERE table_name = 'questions' AND column_name = 'id'
        """))
        id_type = result.scalar()
        
        if id_type == 'integer':
            # Rename old table
            op.execute("ALTER TABLE questions RENAME TO questions_legacy")

    # Create questions table (CMS version with UUID)
    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("stem", sa.Text(), nullable=True),
        sa.Column("option_a", sa.Text(), nullable=True),
        sa.Column("option_b", sa.Text(), nullable=True),
        sa.Column("option_c", sa.Text(), nullable=True),
        sa.Column("option_d", sa.Text(), nullable=True),
        sa.Column("option_e", sa.Text(), nullable=True),
        sa.Column("correct_index", sa.SmallInteger(), nullable=True),
        sa.Column("explanation_md", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED", name="question_status"), nullable=False, server_default="DRAFT"),
        sa.Column("year_id", sa.Integer(), nullable=True),
        sa.Column("block_id", sa.Integer(), nullable=True),
        sa.Column("theme_id", sa.Integer(), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("concept_id", sa.Integer(), nullable=True),
        sa.Column("cognitive_level", sa.String(50), nullable=True),
        sa.Column("difficulty", sa.String(50), nullable=True),
        sa.Column("source_book", sa.String(200), nullable=True),
        sa.Column("source_page", sa.String(50), nullable=True),
        sa.Column("source_ref", sa.String(100), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["year_id"], ["years.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], onupdate="CASCADE"),
        sa.CheckConstraint("correct_index >= 0 AND correct_index <= 4", name="ck_question_correct_index"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_questions_status", "questions", ["status"])
    op.create_index("ix_questions_updated_at", "questions", ["updated_at"])
    op.create_index("ix_questions_theme_id", "questions", ["theme_id"])
    op.create_index("ix_questions_block_id", "questions", ["block_id"])
    op.create_index("ix_questions_year_id", "questions", ["year_id"])

    # Create question_versions table
    op.create_table(
        "question_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("change_kind", sa.Enum("CREATE", "EDIT", "STATUS_CHANGE", "PUBLISH", "UNPUBLISH", "IMPORT", name="change_kind"), nullable=False),
        sa.Column("change_reason", sa.String(500), nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "version_no", name="uq_question_version"),
    )
    op.create_index("ix_question_versions_question_id", "question_versions", ["question_id"])
    op.create_index("ix_question_versions_version_no", "question_versions", ["version_no"])

    # Create media_assets table
    op.create_table(
        "media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("storage_provider", sa.Enum("LOCAL", "S3", name="storage_provider"), nullable=False, server_default="LOCAL"),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_assets_sha256", "media_assets", ["sha256"])

    # Create question_media table
    op.create_table(
        "question_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Enum("STEM", "EXPLANATION", "OPTION_A", "OPTION_B", "OPTION_C", "OPTION_D", "OPTION_E", name="media_role"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["media_id"], ["media_assets.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_question_media_question_id", "question_media", ["question_id"])
    op.create_index("ix_question_media_media_id", "question_media", ["media_id"])

    # Create audit_log table
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_entity_type", "audit_log", ["entity_type"])
    op.create_index("ix_audit_log_entity_id", "audit_log", ["entity_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index("ix_audit_log_actor_user_id", "audit_log", ["actor_user_id"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index("ix_audit_log_actor_user_id", table_name="audit_log")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_entity_id", table_name="audit_log")
    op.drop_index("ix_audit_log_entity_type", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_question_media_media_id", table_name="question_media")
    op.drop_index("ix_question_media_question_id", table_name="question_media")
    op.drop_table("question_media")

    op.drop_index("ix_media_assets_sha256", table_name="media_assets")
    op.drop_table("media_assets")

    op.drop_index("ix_question_versions_version_no", table_name="question_versions")
    op.drop_index("ix_question_versions_question_id", table_name="question_versions")
    op.drop_table("question_versions")

    op.drop_index("ix_questions_year_id", table_name="questions")
    op.drop_index("ix_questions_block_id", table_name="questions")
    op.drop_index("ix_questions_theme_id", table_name="questions")
    op.drop_index("ix_questions_updated_at", table_name="questions")
    op.drop_index("ix_questions_status", table_name="questions")
    op.drop_table("questions")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS media_role")
    op.execute("DROP TYPE IF EXISTS storage_provider")
    op.execute("DROP TYPE IF EXISTS change_kind")
    op.execute("DROP TYPE IF EXISTS question_status")
