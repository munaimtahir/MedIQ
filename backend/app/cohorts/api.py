"""Cohort analytics API endpoints (Admin only)."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user, get_db
from app.cohorts.service import get_comparisons, get_percentiles, get_rank_sim
from app.models.user import User, UserRole
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()


class PercentilesResponse(BaseModel):
    """Response for percentiles endpoint."""

    data_source: str = Field(description="Data source: 'snowflake' or 'disabled'")
    metric: str | None = Field(default=None, description="Metric name")
    scope: str | None = Field(default=None, description="Scope: theme|block|year")
    id: int | None = Field(default=None, description="Scope ID")
    window: str | None = Field(default=None, description="Time window")
    percentiles: dict[str, float] | None = Field(
        default=None, description="Percentile values: p10, p25, p50, p75, p90"
    )
    cohort_definition_version: str | None = Field(default=None, description="Cohort definition version")
    algo_profiles_included: list[str] | None = Field(default=None, description="Algorithm profiles included")
    error: str | None = Field(default=None, description="Error code if disabled/not implemented")
    message: str | None = Field(default=None, description="Error message")
    blocking_reasons: list[str] | None = Field(default=None, description="Blocking reasons if disabled")
    note: str | None = Field(default=None, description="Additional note")


class CohortDefinition(BaseModel):
    """Cohort definition for comparisons."""

    scope: str = Field(description="Scope: year|block|theme")
    id: int = Field(description="Scope ID")


class ComparisonsResponse(BaseModel):
    """Response for comparisons endpoint."""

    data_source: str = Field(description="Data source: 'snowflake' or 'disabled'")
    metric: str | None = Field(default=None, description="Metric name")
    window: str | None = Field(default=None, description="Time window")
    cohort_a: CohortDefinition | None = Field(default=None, description="Cohort A definition")
    cohort_b: CohortDefinition | None = Field(default=None, description="Cohort B definition")
    comparison: dict[str, float] | None = Field(
        default=None, description="Comparison metrics: delta, a_value, b_value"
    )
    error: str | None = Field(default=None, description="Error code if disabled/not implemented")
    message: str | None = Field(default=None, description="Error message")
    blocking_reasons: list[str] | None = Field(default=None, description="Blocking reasons if disabled")
    note: str | None = Field(default=None, description="Additional note")


class RankSimResponse(BaseModel):
    """Response for rank simulation endpoint."""

    data_source: str = Field(description="Data source: 'snowflake' or 'disabled'")
    user_id: str | None = Field(default=None, description="User UUID")
    scope: str | None = Field(default=None, description="Scope: year|block")
    id: int | None = Field(default=None, description="Scope ID")
    window: str | None = Field(default=None, description="Time window")
    rank_sim: dict[str, Any] | None = Field(
        default=None, description="Rank simulation: quantile, percentile, notes"
    )
    error: str | None = Field(default=None, description="Error code if disabled/not implemented")
    message: str | None = Field(default=None, description="Error message")
    blocking_reasons: list[str] | None = Field(default=None, description="Blocking reasons if disabled")
    note: str | None = Field(default=None, description="Additional note")


@router.get("/admin/cohorts/percentiles", response_model=PercentilesResponse)
async def get_cohort_percentiles(
    metric: Annotated[
        str,
        Query(description="Metric: accuracy|time_spent|mastery_prob|score"),
    ],
    scope: Annotated[
        str,
        Query(description="Scope: theme|block|year"),
    ],
    id: Annotated[
        int,
        Query(description="Scope ID (theme_id|block_id|year)"),
    ],
    window: Annotated[
        str,
        Query(description="Time window: 7d|30d|90d"),
    ] = "30d",
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get percentile distributions for a cohort.

    Returns percentiles (p10, p25, p50, p75, p90) for the specified metric,
    scope, and time window.
    """
    if not current_user or current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate inputs
    if metric not in ["accuracy", "time_spent", "mastery_prob", "score"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric: {metric}. Must be one of: accuracy, time_spent, mastery_prob, score",
        )

    if scope not in ["theme", "block", "year"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scope: {scope}. Must be one of: theme, block, year",
        )

    if window not in ["7d", "30d", "90d"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window: {window}. Must be one of: 7d, 30d, 90d",
        )

    # Call service
    result = get_percentiles(db, metric, scope, id, window)

    # Handle disabled/not implemented responses
    if "error" in result:
        if result["error"] == "feature_disabled":
            raise HTTPException(
                status_code=403,
                detail={
                    "error": result["error"],
                    "message": result["message"],
                    "data_source": result["data_source"],
                    "blocking_reasons": result["blocking_reasons"],
                },
            )
        elif result["error"] == "not_implemented":
            raise HTTPException(
                status_code=501,
                detail={
                    "error": result["error"],
                    "message": result["message"],
                    "data_source": result["data_source"],
                    "note": result.get("note"),
                },
            )

    # Return success response (when implemented)
    return PercentilesResponse(
        data_source=result.get("data_source", "snowflake"),
        metric=metric,
        scope=scope,
        id=id,
        window=window,
        percentiles=result.get("percentiles"),
        cohort_definition_version=result.get("cohort_definition_version", "v1"),
        algo_profiles_included=result.get("algo_profiles_included", []),
    )


@router.get("/admin/cohorts/comparisons", response_model=ComparisonsResponse)
async def get_cohort_comparisons(
    cohort_a_scope: Annotated[
        str,
        Query(alias="cohort_a_scope", description="Cohort A scope: year|block|theme"),
    ],
    cohort_a_id: Annotated[
        int,
        Query(alias="cohort_a_id", description="Cohort A ID"),
    ],
    cohort_b_scope: Annotated[
        str,
        Query(alias="cohort_b_scope", description="Cohort B scope: year|block|theme"),
    ],
    cohort_b_id: Annotated[
        int,
        Query(alias="cohort_b_id", description="Cohort B ID"),
    ],
    metric: Annotated[
        str,
        Query(description="Metric to compare"),
    ],
    window: Annotated[
        str,
        Query(description="Time window: 7d|30d|90d"),
    ] = "30d",
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get comparison data between two cohorts.

    Compares metrics between two cohorts (e.g., different years, blocks, or themes).
    """
    if not current_user or current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate inputs
    for scope in [cohort_a_scope, cohort_b_scope]:
        if scope not in ["year", "block", "theme"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scope: {scope}. Must be one of: year, block, theme",
            )

    if window not in ["7d", "30d", "90d"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window: {window}. Must be one of: 7d, 30d, 90d",
        )

    cohort_a = {"scope": cohort_a_scope, "id": cohort_a_id}
    cohort_b = {"scope": cohort_b_scope, "id": cohort_b_id}

    # Call service
    result = get_comparisons(db, cohort_a, cohort_b, metric, window)

    # Handle disabled/not implemented responses
    if "error" in result:
        if result["error"] == "feature_disabled":
            raise HTTPException(
                status_code=403,
                detail={
                    "error": result["error"],
                    "message": result["message"],
                    "data_source": result["data_source"],
                    "blocking_reasons": result["blocking_reasons"],
                },
            )
        elif result["error"] == "not_implemented":
            raise HTTPException(
                status_code=501,
                detail={
                    "error": result["error"],
                    "message": result["message"],
                    "data_source": result["data_source"],
                    "note": result.get("note"),
                },
            )

    # Return success response (when implemented)
    return ComparisonsResponse(
        data_source=result.get("data_source", "snowflake"),
        metric=metric,
        window=window,
        cohort_a=CohortDefinition(scope=cohort_a_scope, id=cohort_a_id),
        cohort_b=CohortDefinition(scope=cohort_b_scope, id=cohort_b_id),
        comparison=result.get("comparison"),
    )


@router.get("/admin/cohorts/rank-sim", response_model=RankSimResponse)
async def get_cohort_rank_sim(
    user_id: Annotated[
        str,
        Query(description="User UUID"),
    ],
    scope: Annotated[
        str,
        Query(description="Scope: year|block"),
    ],
    id: Annotated[
        int,
        Query(description="Scope ID (year|block_id)"),
    ],
    window: Annotated[
        str,
        Query(description="Time window: 30d|90d"),
    ] = "30d",
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get rank simulation baseline for a user within a cohort.

    Returns the user's rank/percentile position within the specified cohort.
    """
    if not current_user or current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate inputs
    if scope not in ["year", "block"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scope: {scope}. Must be one of: year, block",
        )

    if window not in ["30d", "90d"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window: {window}. Must be one of: 30d, 90d",
        )

    # Call service
    result = get_rank_sim(db, user_id, scope, id, window)

    # Handle disabled/not implemented responses
    if "error" in result:
        if result["error"] == "feature_disabled":
            raise HTTPException(
                status_code=403,
                detail={
                    "error": result["error"],
                    "message": result["message"],
                    "data_source": result["data_source"],
                    "blocking_reasons": result["blocking_reasons"],
                },
            )
        elif result["error"] == "not_implemented":
            raise HTTPException(
                status_code=501,
                detail={
                    "error": result["error"],
                    "message": result["message"],
                    "data_source": result["data_source"],
                    "note": result.get("note"),
                },
            )

    # Return success response (when implemented)
    return RankSimResponse(
        data_source=result.get("data_source", "snowflake"),
        user_id=user_id,
        scope=scope,
        id=id,
        window=window,
        rank_sim=result.get("rank_sim"),
    )
