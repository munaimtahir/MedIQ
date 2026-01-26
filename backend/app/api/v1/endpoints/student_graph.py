"""Student graph exploration endpoints (feature-flagged, optional)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.graph.service import get_neighbors, get_prereqs, get_suggestions
from app.graph.readiness import evaluate_graph_readiness
from app.api.v1.endpoints.admin_graph import (
    get_effective_graph_mode,
    get_graph_runtime_mode,
)
from app.models.user import User
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

# Student-specific hard caps (stricter than admin)
STUDENT_MAX_DEPTH = 1
STUDENT_MAX_PREREQ_DEPTH = 4
STUDENT_MAX_SUGGESTIONS_LIMIT = 10
STUDENT_MAX_NODES_DISPLAY = 100


def require_student(user: User) -> None:
    """Require user to be STUDENT."""
    if user.role != "STUDENT":
        raise HTTPException(status_code=403, detail="Student access required")


def check_feature_enabled() -> None:
    """Check if student concept explorer feature is enabled."""
    if not settings.FEATURE_STUDENT_CONCEPT_EXPLORER:
        raise HTTPException(
            status_code=404,
            detail={"error": "feature_disabled", "message": "Concept exploration is not available"},
        )


def check_graph_available(db: Session) -> None:
    """
    Check if graph is available for student use.

    Raises 503 if:
    - Graph effective_mode is disabled
    - Graph is not ready
    """
    requested_mode = get_graph_runtime_mode(db)
    effective_mode = get_effective_graph_mode(db, requested_mode)

    if effective_mode == "disabled":
        raise HTTPException(
            status_code=503,
            detail={
                "error": "graph_unavailable",
                "message": "Concept map is not available right now",
            },
        )

    # Check readiness if in shadow/active mode
    if effective_mode in ("shadow", "active"):
        readiness = evaluate_graph_readiness(db)
        if not readiness.ready:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "graph_unavailable",
                    "message": "Concept map is not available right now",
                    "blocking_reasons": readiness.blocking_reasons,
                },
            )


class ConceptNodeResponse(BaseModel):
    """Concept node response."""

    concept_id: str
    name: str
    level: str


class NeighborsResponse(BaseModel):
    """Neighbors response."""

    concept_id: str
    depth: int
    prereqs: list[ConceptNodeResponse]
    dependents: list[ConceptNodeResponse]
    warnings: list[str]
    truncated: bool = False


class PrerequisitesResponse(BaseModel):
    """Prerequisites response."""

    concept_id: str
    max_depth: int
    nodes: list[ConceptNodeResponse]
    warnings: list[str]
    truncated: bool = False


class MissingPrereqResponse(BaseModel):
    """Missing prerequisite suggestion."""

    concept_id: str
    name: str
    distance: int
    score: float


class SuggestionsResponse(BaseModel):
    """Suggestions response."""

    target: str
    missing_prereqs: list[MissingPrereqResponse]
    warnings: list[str]
    truncated: bool = False


@router.get("/student/graph/neighbors", response_model=NeighborsResponse)
async def get_student_neighbors(
    concept_id: str = Query(..., description="Concept ID to query"),
    depth: int = Query(1, ge=1, le=STUDENT_MAX_DEPTH, description="Depth of expansion (max 1)"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get neighbors (prerequisites and dependents) of a concept (student only).

    Returns prerequisites and dependents with strict depth limit (max 1).
    """
    require_student(current_user)
    check_feature_enabled()
    check_graph_available(db)

    try:
        result = get_neighbors(concept_id, depth)
        
        # Cap total nodes to STUDENT_MAX_NODES_DISPLAY
        total_nodes = len(result.get("prereqs", [])) + len(result.get("dependents", []))
        truncated = total_nodes > STUDENT_MAX_NODES_DISPLAY
        
        prereqs = result.get("prereqs", [])[:STUDENT_MAX_NODES_DISPLAY // 2]
        dependents = result.get("dependents", [])[:STUDENT_MAX_NODES_DISPLAY // 2]
        
        warnings = result.get("warnings", [])
        if truncated:
            warnings.append("Results truncated (max 100 nodes)")

        return NeighborsResponse(
            concept_id=result["concept_id"],
            depth=result["depth"],
            prereqs=[ConceptNodeResponse(**n) for n in prereqs],
            dependents=[ConceptNodeResponse(**n) for n in dependents],
            warnings=warnings,
            truncated=truncated,
        )
    except ValueError as e:
        logger.error(f"Error in student neighbors query: {e}")
        raise HTTPException(status_code=503, detail={"error": "graph_unavailable", "message": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error in student neighbors query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/student/graph/prerequisites", response_model=PrerequisitesResponse)
async def get_student_prereqs(
    concept_id: str = Query(..., description="Concept ID to query"),
    max_depth: int = Query(
        4, ge=1, le=STUDENT_MAX_PREREQ_DEPTH, description="Maximum depth to expand (max 4)"
    ),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get all prerequisites of a concept (student only).

    Returns prerequisite nodes with strict depth limit (max 4).
    """
    require_student(current_user)
    check_feature_enabled()
    check_graph_available(db)

    try:
        result = get_prereqs(concept_id, max_depth, include_edges=False)
        
        # Cap nodes to STUDENT_MAX_NODES_DISPLAY
        nodes = result.get("nodes", [])[:STUDENT_MAX_NODES_DISPLAY]
        truncated = len(result.get("nodes", [])) > STUDENT_MAX_NODES_DISPLAY
        
        warnings = result.get("warnings", [])
        if truncated:
            warnings.append("Results truncated (max 100 nodes)")

        return PrerequisitesResponse(
            concept_id=result["concept_id"],
            max_depth=result["max_depth"],
            nodes=[ConceptNodeResponse(**n) for n in nodes],
            warnings=warnings,
            truncated=truncated,
        )
    except ValueError as e:
        logger.error(f"Error in student prerequisites query: {e}")
        raise HTTPException(status_code=503, detail={"error": "graph_unavailable", "message": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error in student prerequisites query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/student/graph/suggestions", response_model=SuggestionsResponse)
async def get_student_suggestions(
    target_concept_id: str = Query(..., description="Target concept ID"),
    limit: int = Query(10, ge=1, le=STUDENT_MAX_SUGGESTIONS_LIMIT, description="Maximum suggestions (max 10)"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get suggestions for missing prerequisites (student only).

    Returns ranked suggestions with strict limit (max 10).
    """
    require_student(current_user)
    check_feature_enabled()
    check_graph_available(db)

    # For students, we don't accept known_concept_ids as input (use empty list)
    # This keeps the API simple and avoids exposing too much complexity
    known_ids: list[str] = []

    try:
        result = get_suggestions(target_concept_id, known_ids, max_depth=STUDENT_MAX_PREREQ_DEPTH, limit=limit)
        
        missing_prereqs = result.get("missing_prereqs", [])
        warnings = result.get("warnings", [])

        return SuggestionsResponse(
            target=result["target"],
            missing_prereqs=[
                MissingPrereqResponse(**prereq) for prereq in missing_prereqs
            ],
            warnings=warnings,
            truncated=False,  # Already capped by limit parameter
        )
    except ValueError as e:
        logger.error(f"Error in student suggestions query: {e}")
        raise HTTPException(status_code=503, detail={"error": "graph_unavailable", "message": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error in student suggestions query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
