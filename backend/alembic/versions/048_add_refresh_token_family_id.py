"""Add family_id column to refresh_tokens for mobile-safe token refresh.

Revision ID: 048_family_id
Revises: 047_test_packages
Create Date: 2026-01-28

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "048_family_id"
down_revision = "047_test_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add family_id column to refresh_tokens
    op.add_column(
        "refresh_tokens",
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Create index for family lookups
    op.create_index(
        "ix_refresh_tokens_family_id",
        "refresh_tokens",
        ["family_id"]
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    
    # Drop column
    op.drop_column("refresh_tokens", "family_id")
