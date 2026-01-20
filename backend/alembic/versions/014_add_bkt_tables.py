"""Add BKT (Bayesian Knowledge Tracing) tables

Revision ID: 014_add_bkt_tables
Revises: 013_add_mistake_log
Create Date: 2026-01-21

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "014_add_bkt_tables"
down_revision = "013_add_mistake_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Table 1: bkt_skill_params - Stores BKT parameters per concept (skill)
    op.create_table(
        "bkt_skill_params",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("algo_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        # BKT 4-parameter model
        sa.Column("p_L0", sa.Float, nullable=False, comment="Prior probability of mastery"),
        sa.Column("p_T", sa.Float, nullable=False, comment="Probability of learning (transition)"),
        sa.Column(
            "p_S", sa.Float, nullable=False, comment="Probability of slip (learned but wrong)"
        ),
        sa.Column(
            "p_G", sa.Float, nullable=False, comment="Probability of guess (unlearned but correct)"
        ),
        # Metadata
        sa.Column("constraints_applied", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "fitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("fitted_on_data_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fitted_on_data_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metrics",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
            comment="AUC, RMSE, logloss, CV metrics",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["algo_version_id"],
            ["algo_versions.id"],
            name="fk_bkt_skill_params_algo_version",
            ondelete="CASCADE",
        ),
    )

    # Indexes for bkt_skill_params
    op.create_index(
        "idx_bkt_skill_params_concept_active", "bkt_skill_params", ["concept_id", "is_active"]
    )
    op.create_index("idx_bkt_skill_params_algo_version", "bkt_skill_params", ["algo_version_id"])
    op.create_index("idx_bkt_skill_params_fitted_at", "bkt_skill_params", ["fitted_at"])

    # Table 2: bkt_user_skill_state - Tracks per-user per-concept mastery state
    op.create_table(
        "bkt_user_skill_state",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "p_mastery",
            sa.Float,
            nullable=False,
            server_default="0.0",
            comment="Current mastery probability",
        ),
        sa.Column("n_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "algo_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Version used for last update",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
        # Primary key
        sa.PrimaryKeyConstraint("user_id", "concept_id", name="pk_bkt_user_skill_state"),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_bkt_user_skill_state_user", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["algo_version_id"],
            ["algo_versions.id"],
            name="fk_bkt_user_skill_state_algo_version",
            ondelete="SET NULL",
        ),
    )

    # Indexes for bkt_user_skill_state
    op.create_index("idx_bkt_user_skill_state_user", "bkt_user_skill_state", ["user_id"])
    op.create_index("idx_bkt_user_skill_state_concept", "bkt_user_skill_state", ["concept_id"])
    op.create_index("idx_bkt_user_skill_state_mastery", "bkt_user_skill_state", ["p_mastery"])
    op.create_index(
        "idx_bkt_user_skill_state_last_attempt", "bkt_user_skill_state", ["last_attempt_at"]
    )

    # Table 3: mastery_snapshot - Historical snapshots for analytics
    op.create_table(
        "mastery_snapshot",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("p_mastery", sa.Float, nullable=False),
        sa.Column("n_attempts", sa.Integer, nullable=False),
        sa.Column("algo_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_mastery_snapshot_user", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["algo_version_id"],
            ["algo_versions.id"],
            name="fk_mastery_snapshot_algo_version",
            ondelete="SET NULL",
        ),
    )

    # Indexes for mastery_snapshot
    op.create_index(
        "idx_mastery_snapshot_user_concept", "mastery_snapshot", ["user_id", "concept_id"]
    )
    op.create_index("idx_mastery_snapshot_created_at", "mastery_snapshot", ["created_at"])
    op.create_index("idx_mastery_snapshot_concept", "mastery_snapshot", ["concept_id"])

    # Seed default BKT parameters (global fallback)
    # These will be used when no concept-specific parameters are available
    op.execute(
        """
        INSERT INTO algo_versions (algo_key, version, status, description, created_at, updated_at)
        VALUES ('bkt', 'v1', 'ACTIVE', 'Bayesian Knowledge Tracing v1 - Standard 4-parameter model', now(), now())
        ON CONFLICT (algo_key, version) DO NOTHING;
    """
    )

    # Insert default parameters for BKT v1
    op.execute(
        """
        INSERT INTO algo_params (algo_version_id, params_json, is_active, created_at, updated_at)
        SELECT 
            av.id,
            '{
                "default_L0": 0.1,
                "default_T": 0.1,
                "default_S": 0.1,
                "default_G": 0.25,
                "mastery_threshold": 0.95,
                "min_attempts_for_fit": 10,
                "constraints": {
                    "L0_min": 0.001,
                    "L0_max": 0.5,
                    "T_min": 0.001,
                    "T_max": 0.5,
                    "S_min": 0.001,
                    "S_max": 0.4,
                    "G_min": 0.001,
                    "G_max": 0.4
                },
                "degeneracy_checks": {
                    "require_learned_better_than_unlearned": true,
                    "min_learning_gain": 0.05
                }
            }'::jsonb,
            true,
            now(),
            now()
        FROM algo_versions av
        WHERE av.algo_key = 'bkt' AND av.version = 'v1'
        ON CONFLICT DO NOTHING;
    """
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("mastery_snapshot")
    op.drop_table("bkt_user_skill_state")
    op.drop_table("bkt_skill_params")

    # Remove BKT algo version and params
    op.execute(
        "DELETE FROM algo_params WHERE algo_version_id IN (SELECT id FROM algo_versions WHERE algo_key = 'bkt')"
    )
    op.execute("DELETE FROM algo_versions WHERE algo_key = 'bkt'")
