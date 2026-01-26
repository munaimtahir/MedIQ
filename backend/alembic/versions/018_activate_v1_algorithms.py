"""Activate v1 for all algorithms

Revision ID: 018
Revises: 017
Create Date: 2026-01-21

Seeds v1 versions for all learning algorithms with proper parameters:
- mastery:v1 (BKT-based concept mastery, existing implementation)
- revision:v1 (FSRS-based spaced repetition, existing implementation)
- difficulty:v1 (Elo rating system, implemented in Task 121)
- adaptive:v0 (rule-based selection, remains as fallback)
- adaptive_selection:v1 (Thompson Sampling bandit, implemented in Task 122)
- mistakes:v1 (pattern analysis, unchanged from v0 for now)
- bkt:v1 (Bayesian Knowledge Tracing, existing implementation)

Also deprecates v0 versions where v1 is available.
"""

import json
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Define v1 algorithms with their parameters
    v1_algorithms = [
        {
            "id": str(uuid.uuid4()),
            "algo_key": "mastery",
            "version": "v1",
            "status": "ACTIVE",
            "description": "Mastery tracking v1 - BKT-based concept mastery with theme aggregation",
            "params": {
                "mastery_threshold": 0.95,
                "lookback_days": 90,
                "min_attempts": 3,
                "difficulty_weights": {"easy": 0.90, "medium": 1.00, "hard": 1.10},
                "recency_buckets_days": [0, 7, 30, 90],
            },
        },
        {
            "id": str(uuid.uuid4()),
            "algo_key": "revision",
            "version": "v1",
            "status": "ACTIVE",
            "description": "Revision scheduling v1 - FSRS-6 based spaced repetition",
            "params": {
                "weights": [
                    0.4072, 1.1829, 3.1262, 15.4722, 7.2102, 0.5316, 1.0651, 0.0234,
                    1.616, 0.1544, 1.0824, 1.9813, 0.0953, 0.2975, 2.2042, 0.2407,
                    2.9466, 0.5034, 0.6567,
                ],
                "desired_retention": 0.90,
                "retention_min": 0.70,
                "retention_max": 0.95,
            },
        },
        {
            "id": str(uuid.uuid4()),
            "algo_key": "difficulty",
            "version": "v1",
            "status": "ACTIVE",
            "description": "Difficulty calibration v1 - Elo rating with uncertainty and hierarchical scopes",
            "params": {
                "guess_floor": 0.20,
                "scale": 400.0,
                "k_base_user": 32.0,
                "k_base_question": 24.0,
                "k_min": 8.0,
                "k_max": 64.0,
                "unc_init_user": 350.0,
                "unc_init_question": 250.0,
                "unc_floor": 50.0,
                "unc_decay_per_attempt": 0.9,
                "unc_age_increase_per_day": 1.0,
                "min_attempts_theme_user": 5,
                "min_attempts_theme_question": 3,
                "theme_update_weight": 0.5,
                "recenter_enabled": True,
                "recenter_every_n_updates": 10000,
                "rating_init": 0.0,
            },
        },
        {
            "id": str(uuid.uuid4()),
            "algo_key": "adaptive_selection",
            "version": "v1",
            "status": "ACTIVE",
            "description": "Adaptive selection v1 - Constrained Thompson Sampling over themes with BKT/FSRS/Elo integration",
            "params": {
                # Beta prior
                "beta_prior_a": 1.0,
                "beta_prior_b": 1.0,
                "epsilon_floor": 0.10,
                # Theme selection
                "max_candidate_themes": 30,
                "min_theme_count": 2,
                "max_theme_count": 5,
                "min_per_theme": 3,
                "max_per_theme": 20,
                # Repeat exclusion
                "exclude_seen_within_days": 14,
                "exclude_seen_within_sessions": 3,
                "max_repeats_in_session": 0,
                "allow_repeat_if_supply_low": True,
                # Revision mode
                "revision_due_ratio_min": 0.60,
                "revision_due_ratio_max": 0.85,
                "due_concept_fallback_to_weak": True,
                # Elo challenge band
                "p_low": 0.55,
                "p_high": 0.80,
                "explore_new_question_rate": 0.10,
                "explore_high_uncertainty_rate": 0.05,
                # Feature weights
                "w_weakness": 0.45,
                "w_due": 0.35,
                "w_uncertainty": 0.10,
                "w_recency_penalty": 0.10,
                "supply_min_questions": 10,
                # Reward
                "reward_window": "session",
                "reward_type": "bkt_delta",
                "reward_min_attempts_per_theme": 3,
            },
        },
        {
            "id": str(uuid.uuid4()),
            "algo_key": "mistakes",
            "version": "v1",
            "status": "ACTIVE",
            "description": "Common mistakes v1 - Pattern analysis for frequent errors",
            "params": {
                "min_frequency": 3,
                "lookback_days": 90,
                "min_theme_mistakes": 2,
                "cluster_threshold": 0.7,
            },
        },
        {
            "id": str(uuid.uuid4()),
            "algo_key": "bkt",
            "version": "v1",
            "status": "ACTIVE",
            "description": "BKT v1 - Bayesian Knowledge Tracing for concept-level mastery",
            "params": {
                "p_L0": 0.1,
                "p_T": 0.2,
                "p_S": 0.1,
                "p_G": 0.2,
                "mastery_threshold": 0.95,
                "min_attempts_per_concept": 10,
                "min_users_per_concept": 3,
            },
        },
    ]

    # Insert v1 versions and their params
    for algo in v1_algorithms:
        params_json = json.dumps(algo["params"])

        # Insert algo version
        op.execute(
            f"""
            INSERT INTO algo_versions (id, algo_key, version, status, description, created_at, updated_at)
            VALUES (
                '{algo["id"]}',
                '{algo["algo_key"]}',
                '{algo["version"]}',
                '{algo["status"]}',
                '{algo["description"]}',
                now(),
                now()
            )
            ON CONFLICT (algo_key, version) DO UPDATE
            SET status = '{algo["status"]}',
                description = '{algo["description"]}',
                updated_at = now()
            """
        )

        # Insert algo params
        params_id = str(uuid.uuid4())
        op.execute(
            f"""
            INSERT INTO algo_params (id, algo_version_id, params_json, is_active, created_at, updated_at)
            SELECT '{params_id}', id, '{params_json}'::jsonb, true, now(), now()
            FROM algo_versions
            WHERE algo_key = '{algo["algo_key"]}' AND version = '{algo["version"]}'
            ON CONFLICT DO NOTHING
            """
        )

    # Deprecate v0 versions (except adaptive:v0 which remains as fallback)
    v0_deprecate_keys = ["mastery", "revision", "difficulty", "mistakes", "bkt"]
    for key in v0_deprecate_keys:
        op.execute(
            f"""
            UPDATE algo_versions
            SET status = 'DEPRECATED', updated_at = now()
            WHERE algo_key = '{key}' AND version = 'v0'
            """
        )

    # Keep adaptive:v0 active as fallback for adaptive_selection:v1
    # (no change needed, it's already ACTIVE)


def downgrade() -> None:
    # Restore v0 to ACTIVE
    v0_restore_keys = ["mastery", "revision", "difficulty", "mistakes", "bkt"]
    for key in v0_restore_keys:
        op.execute(
            f"""
            UPDATE algo_versions
            SET status = 'ACTIVE', updated_at = now()
            WHERE algo_key = '{key}' AND version = 'v0'
            """
        )

    # Set v1 to DEPRECATED (or delete)
    v1_keys = ["mastery", "revision", "difficulty", "adaptive_selection", "mistakes", "bkt"]
    for key in v1_keys:
        op.execute(
            f"""
            UPDATE algo_versions
            SET status = 'DEPRECATED', updated_at = now()
            WHERE algo_key = '{key}' AND version = 'v1'
            """
        )
