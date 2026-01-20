"""Add learning engine tables

Revision ID: 009_learning_engine
Revises: 008_add_bookmarks
Create Date: 2026-01-21 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = "009_learning_engine"
down_revision: Union[str, None] = "008_add_bookmarks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create algo_versions table
    op.create_table(
        "algo_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("algo_key", sa.String(50), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("algo_key", "version", name="uq_algo_key_version"),
    )

    # Create indexes for algo_versions
    op.create_index("ix_algo_versions_algo_key_status", "algo_versions", ["algo_key", "status"])

    # Create algo_params table
    op.create_table(
        "algo_params",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("algo_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("params_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["algo_version_id"], ["algo_versions.id"], ondelete="CASCADE", onupdate="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE"),
    )

    # Create indexes for algo_params
    op.create_index(
        "ix_algo_params_algo_version_id_is_active", "algo_params", ["algo_version_id", "is_active"]
    )

    # Create algo_runs table
    op.create_table(
        "algo_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("algo_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("params_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_summary_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("output_summary_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["algo_version_id"], ["algo_versions.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["params_id"], ["algo_params.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["test_sessions.id"], onupdate="CASCADE"),
    )

    # Create indexes for algo_runs
    op.create_index("ix_algo_runs_user_id_started_at", "algo_runs", ["user_id", "started_at"])
    op.create_index(
        "ix_algo_runs_algo_version_id_started_at", "algo_runs", ["algo_version_id", "started_at"]
    )
    op.create_index("ix_algo_runs_session_id", "algo_runs", ["session_id"])

    # Seed algorithm versions (v0 for all 5 algorithms)
    algorithms = [
        {
            "id": str(uuid.uuid4()),
            "algo_key": "mastery",
            "version": "v0",
            "status": "ACTIVE",
            "description": "Mastery tracking algorithm v0 - tracks student understanding levels",
        },
        {
            "id": str(uuid.uuid4()),
            "algo_key": "revision",
            "version": "v0",
            "status": "ACTIVE",
            "description": "Revision scheduling algorithm v0 - spaced repetition scheduling",
        },
        {
            "id": str(uuid.uuid4()),
            "algo_key": "difficulty",
            "version": "v0",
            "status": "ACTIVE",
            "description": "Difficulty assessment algorithm v0 - estimates question difficulty",
        },
        {
            "id": str(uuid.uuid4()),
            "algo_key": "adaptive",
            "version": "v0",
            "status": "ACTIVE",
            "description": "Adaptive selection algorithm v0 - selects optimal questions for learning",
        },
        {
            "id": str(uuid.uuid4()),
            "algo_key": "mistakes",
            "version": "v0",
            "status": "ACTIVE",
            "description": "Common mistakes algorithm v0 - identifies common error patterns",
        },
    ]

    # Insert algorithm versions
    for algo in algorithms:
        op.execute(
            f"""
            INSERT INTO algo_versions (id, algo_key, version, status, description, created_at, updated_at)
            VALUES (
                '{algo['id']}',
                '{algo['algo_key']}',
                '{algo['version']}',
                '{algo['status']}',
                '{algo['description']}',
                now(),
                now()
            )
            """
        )

    # Seed default parameters for each algorithm
    default_params = {
        "mastery": {"threshold": 0.7, "decay_factor": 0.95, "min_attempts": 5},
        "revision": {"intervals": [1, 3, 7, 14, 30], "ease_factor": 2.5},
        "difficulty": {"window_size": 100, "min_attempts": 10},
        "adaptive": {"exploration_rate": 0.2, "target_accuracy": 0.75},
        "mistakes": {"min_frequency": 3, "lookback_days": 90},
    }

    # Insert default params for each algorithm
    for algo in algorithms:
        params_json = default_params.get(algo["algo_key"], {})
        params_json_str = str(params_json).replace("'", '"')  # Convert to JSON format

        op.execute(
            f"""
            INSERT INTO algo_params (id, algo_version_id, params_json, is_active, created_at, updated_at)
            VALUES (
                '{str(uuid.uuid4())}',
                '{algo['id']}',
                '{params_json_str}'::jsonb,
                true,
                now(),
                now()
            )
            """
        )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index("ix_algo_runs_session_id")
    op.drop_index("ix_algo_runs_algo_version_id_started_at")
    op.drop_index("ix_algo_runs_user_id_started_at")
    op.drop_table("algo_runs")

    op.drop_index("ix_algo_params_algo_version_id_is_active")
    op.drop_table("algo_params")

    op.drop_index("ix_algo_versions_algo_key_status")
    op.drop_table("algo_versions")
