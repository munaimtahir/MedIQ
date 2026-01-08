"""add_syllabus_years_blocks_themes

Revision ID: 6c7d8e9f0123
Revises: 5b8663bb123c
Create Date: 2026-01-15 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6c7d8e9f0123"
down_revision = "5b8663bb123c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create years table
    op.create_table(
        "years",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_year_name"),
    )
    op.create_index("ix_years_order_no", "years", ["order_no"], unique=False)

    # Drop old blocks and themes tables if they exist (they have different structure)
    # Note: This will lose existing data. In production, you'd want a data migration.
    op.execute("DROP TABLE IF EXISTS themes CASCADE")
    op.execute("DROP TABLE IF EXISTS blocks CASCADE")

    # Create new blocks table
    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("year_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["year_id"], ["years.id"], onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year_id", "code", name="uq_block_year_code"),
    )
    op.create_index("ix_blocks_year_order", "blocks", ["year_id", "order_no"], unique=False)

    # Create new themes table
    op.create_table(
        "themes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("block_id", "title", name="uq_theme_block_title"),
    )
    op.create_index("ix_themes_block_order", "themes", ["block_id", "order_no"], unique=False)

    # Update questions table to reference new themes table
    # Note: This assumes questions.theme_id already exists and is Integer
    # If the old themes table had different structure, you may need to handle migration differently


def downgrade() -> None:
    # Drop new tables
    op.drop_index("ix_themes_block_order", table_name="themes")
    op.drop_table("themes")
    op.drop_index("ix_blocks_year_order", table_name="blocks")
    op.drop_table("blocks")
    op.drop_index("ix_years_order_no", table_name="years")
    op.drop_table("years")

    # Note: Old blocks/themes tables would need to be recreated if needed
