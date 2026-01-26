"""Evaluation harness API endpoints (admin only)."""

import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.learning_engine.eval.dataset import DatasetSpec
from app.learning_engine.eval.registry import get_eval_run, list_eval_runs
from app.learning_engine.eval.runner import run_evaluation
from app.learning_engine.eval.replay import EvalSuite
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


# ============================================================================
# Request/Response Schemas
# ============================================================================


class EvalRunCreate(BaseModel):
    """Request to create an evaluation run."""

    suite_name: str
    suite_versions: dict[str, str]
    dataset_spec: dict[str, Any]
    config: dict[str, Any]
    random_seed: int | None = None
    notes: str | None = None


class EvalRunResponse(BaseModel):
    """Evaluation run response."""

    id: UUID
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    status: str
    suite_name: str
    suite_versions: dict[str, str]
    dataset_spec: dict[str, Any]
    config: dict[str, Any]
    git_sha: str | None
    random_seed: int | None
    notes: str | None
    error: str | None

    class Config:
        """Pydantic config."""

        from_attributes = True


class EvalMetricResponse(BaseModel):
    """Evaluation metric response."""

    id: UUID
    metric_name: str
    scope_type: str
    scope_id: str | None
    value: float
    n: int
    extra: dict[str, Any] | None

    class Config:
        """Pydantic config."""

        from_attributes = True


# ============================================================================
# POST /v1/admin/eval/runs
# ============================================================================


@router.post("/admin/eval/runs", response_model=EvalRunResponse)
async def create_eval_run_endpoint(
    request: EvalRunCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create and start an evaluation run (admin only).

    Currently runs synchronously. Structure allows for background jobs later.
    """
    require_admin(current_user)

    # Parse dataset spec
    try:
        dataset_spec = DatasetSpec(**request.dataset_spec)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid dataset_spec: {e}")

    # Get git SHA
    import subprocess

    git_sha = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        git_sha = result.stdout.strip()
    except Exception:
        pass

    # Create placeholder suite (would load actual suite based on suite_name)
    from app.learning_engine.eval.replay import EvalSuite, ReplayPrediction, ReplayState

    class PlaceholderSuite(EvalSuite):
        def predict(self, state, event_context):
            return ReplayPrediction(event_id=event_context.event_id, p_correct=0.5)

        def update(self, state, outcome, event_context):
            return state

        def init_state(self, user_id):
            return ReplayState(user_id=user_id)

    suite = PlaceholderSuite()

    try:
        run_id = await run_evaluation(
            db,
            suite=suite,
            suite_name=request.suite_name,
            suite_versions=request.suite_versions,
            dataset_spec=dataset_spec,
            config=request.config,
            git_sha=git_sha,
            random_seed=request.random_seed,
            notes=request.notes,
        )

        eval_run = await get_eval_run(db, run_id)
        if not eval_run:
            raise HTTPException(status_code=404, detail="Run not found after creation")

        return EvalRunResponse.model_validate(eval_run)

    except Exception as e:
        logger.error(f"Evaluation run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


# ============================================================================
# GET /v1/admin/eval/runs
# ============================================================================


@router.get("/admin/eval/runs", response_model=list[EvalRunResponse])
async def list_eval_runs_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    suite_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
):
    """List evaluation runs (admin only)."""
    require_admin(current_user)

    runs = await list_eval_runs(db, suite_name=suite_name, status=status, limit=limit)
    return [EvalRunResponse.model_validate(run) for run in runs]


# ============================================================================
# GET /v1/admin/eval/runs/{id}
# ============================================================================


@router.get("/admin/eval/runs/{run_id}", response_model=dict[str, Any])
async def get_eval_run_endpoint(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get evaluation run details including metrics (admin only)."""
    require_admin(current_user)

    eval_run = await get_eval_run(db, run_id)
    if not eval_run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get metrics
    from app.models.eval import EvalMetric
    from sqlalchemy import select

    stmt = select(EvalMetric).where(EvalMetric.run_id == run_id)
    result = await db.execute(stmt)
    metrics = result.scalars().all()

    # Get artifacts
    from app.models.eval import EvalArtifact

    stmt = select(EvalArtifact).where(EvalArtifact.run_id == run_id)
    result = await db.execute(stmt)
    artifacts = result.scalars().all()

    return {
        "run": EvalRunResponse.model_validate(eval_run).model_dump(),
        "metrics": [EvalMetricResponse.model_validate(m).model_dump() for m in metrics],
        "artifacts": [
            {
                "id": str(a.id),
                "type": a.artifact_type,
                "path": a.path,
                "created_at": a.created_at.isoformat(),
            }
            for a in artifacts
        ],
    }
