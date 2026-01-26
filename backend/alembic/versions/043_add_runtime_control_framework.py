"""Add runtime control framework tables

Revision ID: 043
Revises: 042
Create Date: 2026-01-25 14:00:00.000000

- runtime_profiles: primary/fallback/shadow profiles with module defaults
- module_overrides: per-module version overrides
- switch_audit_log: append-only audit for flag/profile/override changes
- session_runtime_snapshot: session-level runtime snapshot (no mid-session change)
- two_person_approvals: scaffold for optional 2-person approval
- FREEZE_UPDATES seed in system_flags
- freeze_updates_at_start on test_sessions
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # runtime_profiles
    # -------------------------------------------------------------------------
    op.create_table(
        "runtime_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(80), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_runtime_profiles_name", "runtime_profiles", ["name"], unique=True)
    op.create_index("ix_runtime_profiles_is_active", "runtime_profiles", ["is_active"])

    # Seed profiles: primary (v1), fallback (v0), shadow (eval-only)
    op.execute(
        """
        INSERT INTO runtime_profiles (id, name, is_active, config, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'primary', true, '{"mastery":"v1","revision":"v1","adaptive":"v1","difficulty":"v1","mistakes":"v1","search":"v0","graph":"v0","warehouse":"v0","irt":"v0"}'::jsonb, now(), now()),
            (gen_random_uuid(), 'fallback', false, '{"mastery":"v0","revision":"v0","adaptive":"v0","difficulty":"v0","mistakes":"v0","search":"v0","graph":"v0","warehouse":"v0","irt":"v0"}'::jsonb, now(), now()),
            (gen_random_uuid(), 'shadow', false, '{"mastery":"v1","revision":"v1","adaptive":"v1","difficulty":"v1","mistakes":"v1","search":"v0","graph":"v0","warehouse":"v0","irt":"v0-shadow"}'::jsonb, now(), now())
        ON CONFLICT (name) DO NOTHING
        """
    )
    # Ensure only one active; primary wins
    op.execute(
        """
        UPDATE runtime_profiles SET is_active = false WHERE name IN ('fallback','shadow')
        """
    )

    # -------------------------------------------------------------------------
    # module_overrides
    # -------------------------------------------------------------------------
    op.create_table(
        "module_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("module_key", sa.String(80), nullable=False),
        sa.Column("version_key", sa.String(40), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_module_overrides_module_key", "module_overrides", ["module_key"], unique=True)

    # -------------------------------------------------------------------------
    # switch_audit_log (append-only)
    # -------------------------------------------------------------------------
    op.create_table(
        "switch_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action_type", sa.String(80), nullable=False),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_switch_audit_log_created_at", "switch_audit_log", ["created_at"])
    op.create_index("ix_switch_audit_log_action_type", "switch_audit_log", ["action_type"])

    # -------------------------------------------------------------------------
    # session_runtime_snapshot (session_id -> profile + resolved modules + flags)
    # -------------------------------------------------------------------------
    op.create_table(
        "session_runtime_snapshot",
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("test_sessions.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("profile_name", sa.String(80), nullable=False),
        sa.Column("resolved_modules", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("flags", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -------------------------------------------------------------------------
    # two_person_approvals (scaffold)
    # -------------------------------------------------------------------------
    op.create_table(
        "two_person_approvals",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "requested_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("requested_action", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_two_person_approvals_status", "two_person_approvals", ["status"])
    op.create_index("ix_two_person_approvals_requested_by", "two_person_approvals", ["requested_by"])

    # -------------------------------------------------------------------------
    # FREEZE_UPDATES seed in system_flags
    # -------------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO system_flags (key, value, updated_at, updated_by, reason)
        VALUES ('FREEZE_UPDATES', false, now(), NULL, 'Initial seed')
        ON CONFLICT (key) DO NOTHING
        """
    )

    # -------------------------------------------------------------------------
    # freeze_updates_at_start on test_sessions
    # -------------------------------------------------------------------------
    op.add_column(
        "test_sessions",
        sa.Column(
            "freeze_updates_at_start",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("test_sessions", "freeze_updates_at_start")
    op.execute("DELETE FROM system_flags WHERE key = 'FREEZE_UPDATES'")

    op.drop_index("ix_two_person_approvals_requested_by", table_name="two_person_approvals")
    op.drop_index("ix_two_person_approvals_status", table_name="two_person_approvals")
    op.drop_table("two_person_approvals")

    op.drop_table("session_runtime_snapshot")

    op.drop_index("ix_switch_audit_log_action_type", table_name="switch_audit_log")
    op.drop_index("ix_switch_audit_log_created_at", table_name="switch_audit_log")
    op.drop_table("switch_audit_log")

    op.drop_index("ix_module_overrides_module_key", table_name="module_overrides")
    op.drop_table("module_overrides")

    op.drop_index("ix_runtime_profiles_is_active", table_name="runtime_profiles")
    op.drop_index("ix_runtime_profiles_name", table_name="runtime_profiles")
    op.drop_table("runtime_profiles")
