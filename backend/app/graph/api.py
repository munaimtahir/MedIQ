"""Admin Graph API endpoints for Neo4j concept graph queries."""

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.dependencies import get_current_user, get_db
from app.core.config import settings
from app.graph.neo4j_client import ping
from app.graph.service import (
    get_neighbors,
    get_path,
    get_prereqs,
    get_suggestions,
    MAX_NEIGHBORS_DEPTH,
    MAX_PATH_COUNT,
    MAX_PATH_DEPTH,
    MAX_PREREQS_DEPTH,
    MAX_SUGGESTIONS_KNOWN_IDS,
    MAX_SUGGESTIONS_LIMIT,
)
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


def _check_neo4j_and_raise() -> None:
    """Check Neo4j availability and raise 503 if unavailable."""
    if not settings.NEO4J_ENABLED:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "neo4j_disabled",
                "message": "Graph is disabled in this environment.",
            },
        )

    is_reachable, _, ping_details = ping()
    if not is_reachable:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "neo4j_unreachable",
                "message": "Neo4j is unreachable",
                "details": ping_details,
            },
        )


@router.get("/neighbors")
async def get_neighbors_endpoint(
    concept_id: str = Query(..., description="Concept ID to query"),
    depth: int = Query(1, ge=1, le=MAX_NEIGHBORS_DEPTH, description="Depth of expansion (1 or 2)"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Get neighbors (prerequisites and dependents) of a concept.

    Returns prerequisites (incoming edges) and dependents (outgoing edges).
    """
    require_admin(current_user)
    _check_neo4j_and_raise()

    start_time = time.time()
    try:
        result = get_neighbors(concept_id, depth)
        duration_ms = int((time.time() - start_time) * 1000)

        node_count = len(result.get("prereqs", [])) + len(result.get("dependents", []))
        logger.info(
            f"Graph neighbors query: concept_id={concept_id}, depth={depth}, "
            f"nodes={node_count}, duration_ms={duration_ms}, warnings={len(result.get('warnings', []))}"
        )

        return result
    except ValueError as e:
        # Service layer error (shouldn't happen after _check_neo4j_and_raise, but handle gracefully)
        logger.error(f"Error in neighbors query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in neighbors query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/prerequisites")
async def get_prereqs_endpoint(
    concept_id: str = Query(..., description="Concept ID to query"),
    max_depth: int = Query(5, ge=1, le=MAX_PREREQS_DEPTH, description="Maximum depth to expand"),
    include_edges: bool = Query(True, description="Whether to include edge details"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Get all prerequisites of a concept up to max_depth.

    Returns all prerequisite nodes (and optionally edges) in the prerequisite chain.
    """
    require_admin(current_user)
    _check_neo4j_and_raise()

    start_time = time.time()
    try:
        result = get_prereqs(concept_id, max_depth, include_edges)
        duration_ms = int((time.time() - start_time) * 1000)

        node_count = len(result.get("nodes", []))
        edge_count = len(result.get("edges", [])) if include_edges else 0
        logger.info(
            f"Graph prerequisites query: concept_id={concept_id}, max_depth={max_depth}, "
            f"nodes={node_count}, edges={edge_count}, duration_ms={duration_ms}, "
            f"warnings={len(result.get('warnings', []))}"
        )

        return result
    except ValueError as e:
        logger.error(f"Error in prerequisites query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in prerequisites query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/path")
async def get_path_endpoint(
    from_id: str = Query(..., alias="from", description="Source concept ID"),
    to_id: str = Query(..., alias="to", description="Target concept ID"),
    max_paths: int = Query(3, ge=1, le=MAX_PATH_COUNT, description="Maximum number of paths to return"),
    max_depth: int = Query(8, ge=1, le=MAX_PATH_DEPTH, description="Maximum path depth"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Find paths between two concepts.

    Returns one or more paths (shortest first) connecting the source to target.
    """
    require_admin(current_user)
    _check_neo4j_and_raise()

    start_time = time.time()
    try:
        result = get_path(from_id, to_id, max_paths, max_depth)
        duration_ms = int((time.time() - start_time) * 1000)

        path_count = len(result.get("paths", []))
        total_nodes = sum(len(p.get("nodes", [])) for p in result.get("paths", []))
        logger.info(
            f"Graph path query: from={from_id}, to={to_id}, paths={path_count}, "
            f"total_nodes={total_nodes}, duration_ms={duration_ms}, "
            f"warnings={len(result.get('warnings', []))}"
        )

        return result
    except ValueError as e:
        logger.error(f"Error in path query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in path query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/suggestions")
async def get_suggestions_endpoint(
    target_concept_id: str = Query(..., description="Target concept ID"),
    known_concept_ids: str = Query(
        "",
        description="Comma-separated list of known concept IDs (max 200)",
    ),
    max_depth: int = Query(6, ge=1, le=MAX_PREREQS_DEPTH, description="Maximum depth to expand"),
    limit: int = Query(20, ge=1, le=MAX_SUGGESTIONS_LIMIT, description="Maximum number of suggestions"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Suggest missing prerequisites for a target concept.

    Given a target concept and a list of known concepts, returns ranked suggestions
    for missing prerequisites.
    """
    require_admin(current_user)
    _check_neo4j_and_raise()

    # Parse known_concept_ids
    if known_concept_ids:
        known_ids = [id.strip() for id in known_concept_ids.split(",") if id.strip()]
    else:
        known_ids = []

    # Enforce cap
    if len(known_ids) > MAX_SUGGESTIONS_KNOWN_IDS:
        known_ids = known_ids[:MAX_SUGGESTIONS_KNOWN_IDS]

    start_time = time.time()
    try:
        result = get_suggestions(target_concept_id, known_ids, max_depth, limit)
        duration_ms = int((time.time() - start_time) * 1000)

        suggestion_count = len(result.get("missing_prereqs", []))
        logger.info(
            f"Graph suggestions query: target={target_concept_id}, known_count={len(known_ids)}, "
            f"suggestions={suggestion_count}, duration_ms={duration_ms}, "
            f"warnings={len(result.get('warnings', []))}"
        )

        return result
    except ValueError as e:
        logger.error(f"Error in suggestions query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in suggestions query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
