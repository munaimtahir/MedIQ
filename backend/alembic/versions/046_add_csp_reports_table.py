"""Add csp_reports table for Content-Security-Policy violation reports.

Revision ID: 046_csp_reports
Revises: 045_integrity
Create Date: 2026-01-25

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "046_csp_reports"
down_revision = "045_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create csp_reports table
    op.create_table(
        "csp_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Report metadata
        sa.Column("document_uri", sa.Text(), nullable=True),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("blocked_uri", sa.Text(), nullable=True),
        sa.Column("violated_directive", sa.String(100), nullable=True),
        sa.Column("effective_directive", sa.String(100), nullable=True),
        sa.Column("original_policy", sa.Text(), nullable=True),
        sa.Column("source_file", sa.Text(), nullable=True),
        sa.Column("line_number", sa.String(20), nullable=True),
        sa.Column("column_number", sa.String(20), nullable=True),
        # Request metadata
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),  # IPv4 or IPv6
        # Sampling flag
        sa.Column("sampled", sa.String(10), nullable=False, server_default="true"),
    )
    
    # Create indexes
    op.create_index("ix_csp_reports_created_at", "csp_reports", ["created_at"])
    op.create_index("ix_csp_reports_violated_directive", "csp_reports", ["violated_directive"])
    op.create_index(
        "ix_csp_reports_blocked_uri",
        "csp_reports",
        ["blocked_uri"],
        postgresql_ops={"blocked_uri": "varchar_pattern_ops"},
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_csp_reports_blocked_uri", table_name="csp_reports")
    op.drop_index("ix_csp_reports_violated_directive", table_name="csp_reports")
    op.drop_index("ix_csp_reports_created_at", table_name="csp_reports")
    
    # Drop table
    op.drop_table("csp_reports")
