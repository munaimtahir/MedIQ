"""Add test_packages table for offline mobile caching.

Revision ID: 047_test_packages
Revises: 046_csp_reports
Create Date: 2026-01-28

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "047_test_packages"
down_revision = "046_csp_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create test_packages table
    op.create_table(
        "test_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        
        # Package metadata
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.String(50), nullable=False),  # PROGRAM, YEAR, BLOCK, THEME
        
        # Scope identifiers (JSONB for flexibility)
        sa.Column("scope_data", postgresql.JSONB(), nullable=False),
        
        # Versioning
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version_hash", sa.String(64), nullable=False),  # SHA-256 hash
        
        # Content (immutable once published)
        sa.Column("questions_json", postgresql.JSONB(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        
        # Metadata
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        
        # Foreign key
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], onupdate="CASCADE"),
        
        # Unique constraint
        sa.UniqueConstraint("scope", "scope_data", "version", name="uq_package_scope_version"),
    )
    
    # Create indexes
    op.create_index("ix_test_packages_scope", "test_packages", ["scope"])
    op.create_index("ix_test_packages_published", "test_packages", ["is_published", "published_at"])
    op.create_index("ix_test_packages_version_hash", "test_packages", ["version_hash"])
    op.create_index("ix_test_packages_created_by", "test_packages", ["created_by"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_test_packages_created_by", table_name="test_packages")
    op.drop_index("ix_test_packages_version_hash", table_name="test_packages")
    op.drop_index("ix_test_packages_published", table_name="test_packages")
    op.drop_index("ix_test_packages_scope", table_name="test_packages")
    
    # Drop table
    op.drop_table("test_packages")
