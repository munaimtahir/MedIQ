"""Cohort analytics service with activation gating.

Cohort APIs are enabled only when:
- warehouse_mode == active
- SNOWFLAKE_ENABLED == true
- snowflake_readiness.ready == true
- last successful export_run for required datasets within last 24h
- last transform run success within last 24h (registry stub ok)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.warehouse import WarehouseExportDataset, WarehouseExportRun, WarehouseExportRunStatus
from app.warehouse.snowflake_readiness import SnowflakeReadinessStatus, check_snowflake_readiness

logger = logging.getLogger(__name__)

# Required datasets for cohort analytics
REQUIRED_DATASETS = [
    WarehouseExportDataset.ATTEMPTS,
    WarehouseExportDataset.EVENTS,
    WarehouseExportDataset.MASTERY,
]

# Transform registry stub (future: actual transform run tracking)
TRANSFORM_REGISTRY = {
    "curated_attempts": {"last_success": None, "last_run": None},
    "curated_mastery": {"last_success": None, "last_run": None},
    "mart_percentiles": {"last_success": None, "last_run": None},
    "mart_comparisons": {"last_success": None, "last_run": None},
    "mart_rank_sim": {"last_success": None, "last_run": None},
}


class CohortActivationStatus:
    """Cohort analytics activation status."""

    def __init__(
        self,
        enabled: bool,
        blocking_reasons: list[str] | None = None,
        data_source: str = "disabled",
    ):
        self.enabled = enabled
        self.blocking_reasons = blocking_reasons or []
        self.data_source = data_source


def check_cohort_activation(db: Session) -> CohortActivationStatus:
    """
    Check if cohort analytics are enabled.

    Returns:
        CohortActivationStatus with enabled flag and blocking reasons
    """
    blocking_reasons: list[str] = []

    # Check 1: Warehouse mode must be active
    from app.warehouse.exporter import _get_warehouse_mode

    warehouse_mode, warehouse_freeze = _get_warehouse_mode(db)
    if warehouse_mode != "active":
        blocking_reasons.append(f"warehouse_mode is '{warehouse_mode}', not 'active'")
        return CohortActivationStatus(
            enabled=False,
            blocking_reasons=blocking_reasons,
            data_source="disabled",
        )

    # Check 2: SNOWFLAKE_ENABLED must be true
    if not settings.SNOWFLAKE_ENABLED:
        blocking_reasons.append("SNOWFLAKE_ENABLED is false")
        return CohortActivationStatus(
            enabled=False,
            blocking_reasons=blocking_reasons,
            data_source="disabled",
        )

    # Check 3: Snowflake readiness
    snowflake_status: SnowflakeReadinessStatus = check_snowflake_readiness(db)
    if not snowflake_status.ready:
        blocking_reasons.append(f"snowflake not ready: {snowflake_status.reason}")
        return CohortActivationStatus(
            enabled=False,
            blocking_reasons=blocking_reasons,
            data_source="disabled",
        )

    # Check 4: Last successful export runs within 24h
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
    for dataset in REQUIRED_DATASETS:
        last_successful = (
            db.query(WarehouseExportRun)
            .filter(
                WarehouseExportRun.dataset == dataset,
                WarehouseExportRun.status == WarehouseExportRunStatus.SHADOW_DONE_FILES_ONLY,
                WarehouseExportRun.finished_at >= cutoff_time,
            )
            .order_by(WarehouseExportRun.finished_at.desc())
            .first()
        )

        if not last_successful:
            blocking_reasons.append(
                f"no successful export for {dataset.value} in last 24h"
            )
            return CohortActivationStatus(
                enabled=False,
                blocking_reasons=blocking_reasons,
                data_source="disabled",
            )

    # Check 5: Transform runs (stub - future: actual transform registry)
    # For now, we'll skip this check since transforms aren't tracked yet
    # When transforms are implemented, check:
    # - curated_attempts last_success within 24h
    # - curated_mastery last_success within 24h
    # - mart_percentiles last_success within 24h (for percentiles endpoint)
    # - mart_comparisons last_success within 24h (for comparisons endpoint)
    # - mart_rank_sim last_success within 24h (for rank-sim endpoint)

    # All checks passed
    return CohortActivationStatus(
        enabled=True,
        blocking_reasons=[],
        data_source="snowflake",
    )


def get_percentiles(
    db: Session,
    metric: str,
    scope: str,
    id: int,
    window: str,
) -> dict[str, Any]:
    """
    Get percentile data for a cohort.

    Args:
        db: Database session
        metric: accuracy|time_spent|mastery_prob|score
        scope: theme|block|year
        id: theme_id|block_id|year
        window: 7d|30d|90d

    Returns:
        Response dict with percentiles or disabled status
    """
    # Check activation
    activation = check_cohort_activation(db)
    if not activation.enabled:
        return {
            "error": "feature_disabled",
            "message": "Cohort analytics not enabled yet.",
            "data_source": activation.data_source,
            "blocking_reasons": activation.blocking_reasons,
        }

    # TODO: Query Snowflake MART_THEME_PERCENTILES_DAILY or MART_BLOCK_COMPARISONS_DAILY
    # For now, return 501 not implemented
    return {
        "error": "not_implemented",
        "message": "Snowflake query not implemented yet.",
        "data_source": "snowflake",
        "note": "This endpoint will query MART_THEME_PERCENTILES_DAILY when Snowflake loader is ready",
    }


def get_comparisons(
    db: Session,
    cohort_a: dict[str, Any],
    cohort_b: dict[str, Any],
    metric: str,
    window: str,
) -> dict[str, Any]:
    """
    Get comparison data between two cohorts.

    Args:
        db: Database session
        cohort_a: {scope: "year|block|theme", id: int}
        cohort_b: {scope: "year|block|theme", id: int}
        metric: Metric to compare
        window: Time window

    Returns:
        Response dict with comparison or disabled status
    """
    # Check activation
    activation = check_cohort_activation(db)
    if not activation.enabled:
        return {
            "error": "feature_disabled",
            "message": "Cohort analytics not enabled yet.",
            "data_source": activation.data_source,
            "blocking_reasons": activation.blocking_reasons,
        }

    # TODO: Query Snowflake MART_BLOCK_COMPARISONS_DAILY
    # For now, return 501 not implemented
    return {
        "error": "not_implemented",
        "message": "Snowflake query not implemented yet.",
        "data_source": "snowflake",
        "note": "This endpoint will query MART_BLOCK_COMPARISONS_DAILY when Snowflake loader is ready",
    }


def get_rank_sim(
    db: Session,
    user_id: str,
    scope: str,
    id: int,
    window: str,
) -> dict[str, Any]:
    """
    Get rank simulation baseline for a user.

    Args:
        db: Database session
        user_id: User UUID
        scope: year|block
        id: year|block_id
        window: 30d|90d

    Returns:
        Response dict with rank simulation or disabled status
    """
    # Check activation
    activation = check_cohort_activation(db)
    if not activation.enabled:
        return {
            "error": "feature_disabled",
            "message": "Cohort analytics not enabled yet.",
            "data_source": activation.data_source,
            "blocking_reasons": activation.blocking_reasons,
        }

    # TODO: Query Snowflake MART_RANK_SIM_BASELINE
    # For now, return 501 not implemented
    return {
        "error": "not_implemented",
        "message": "Snowflake query not implemented yet.",
        "data_source": "snowflake",
        "note": "This endpoint will query MART_RANK_SIM_BASELINE when Snowflake loader is ready",
    }
