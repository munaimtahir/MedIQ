"""Replace rank_prediction_snapshot unique constraint with unique index on expression.

Revision ID: 033_fix_rank_snapshot_unique
Revises: 032_add_mock_ranking_tables
Create Date: 2026-01-24 14:00:00.000000

The original UniqueConstraint used DATE(computed_at) as raw text, which does not
map correctly to SQLAlchemy's UniqueConstraint (expressions not supported).
PostgreSQL enforces uniqueness on expressions via UNIQUE INDEX, not UNIQUE constraint.

This migration:
- Drops the unique constraint uq_rank_snapshot_user_cohort_model_date
- Creates a unique index with the same name on (user_id, cohort_key, model_version, (DATE(computed_at)))
"""

from collections.abc import Sequence

from alembic import op

revision: str = "033_fix_rank_snapshot_unique"
down_revision: str | None = "032_add_mock_ranking_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE rank_prediction_snapshot
        DROP CONSTRAINT IF EXISTS uq_rank_snapshot_user_cohort_model_date
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_rank_snapshot_user_cohort_model_date
        ON rank_prediction_snapshot (user_id, cohort_key, model_version, ((computed_at AT TIME ZONE 'UTC')::date))
        """
    )


def downgrade() -> None:
    op.drop_index(
        "uq_rank_snapshot_user_cohort_model_date",
        table_name="rank_prediction_snapshot",
        if_exists=True,
    )
    op.create_unique_constraint(
        "uq_rank_snapshot_user_cohort_model_date",
        "rank_prediction_snapshot",
        ["user_id", "cohort_key", "model_version"],
    )
