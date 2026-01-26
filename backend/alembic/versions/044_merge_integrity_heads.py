"""Merge heads before db integrity constraints

Revision ID: 044_merge
Revises: 043, d528775027ef
Create Date: 2026-01-25

"""
from alembic import op

revision = "044_merge"
down_revision = ("043", "d528775027ef")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
