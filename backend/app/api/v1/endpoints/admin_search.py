"""Admin endpoints for Elasticsearch search health and management."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.config import settings
from app.models.algo_runtime import AlgoRuntimeConfig, AlgoSwitchEvent
from app.security.exam_mode_gate import require_not_exam_mode
from app.models.search_indexing import (
    SearchOutbox,
    SearchOutboxStatus,
    SearchSyncRun,
)
from app.models.user import User
from app.search.health import get_health_info
from app.search.index_bootstrap import ensure_questions_aliases_exist
from app.search.nightly_reindex import run_nightly_reindex
from app.search.outbox_worker import process_outbox_batch
from app.search.readiness import evaluate_elasticsearch_readiness
from app.api.v1.endpoints.admin_algorithms_validation import validate_confirmation_phrase

logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(user: User) -> None:
    """Require user to be ADMIN."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


def require_admin_or_reviewer(user: User) -> None:
    """Require user to be ADMIN or REVIEWER."""
    if user.role not in ("ADMIN", "REVIEWER"):
        raise HTTPException(status_code=403, detail="Admin or Reviewer access required")


@router.get("/admin/search/health")
async def get_search_health(
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Get Elasticsearch health status (admin/reviewer only).

    Returns health information including:
    - enabled: Whether Elasticsearch is enabled
    - reachable: Whether Elasticsearch is reachable
    - indices: List of indices with doc counts and health
    - aliases: Read/write aliases
    - last_sync_run: Last sync run information
    - pending_outbox: Count of pending outbox items

    Fails open: If Elasticsearch is down, returns reachable=false without crashing.
    """
    require_admin_or_reviewer(current_user)

    try:
        health_info = get_health_info()
        logger.debug(f"Elasticsearch health check: enabled={health_info['enabled']}, reachable={health_info['reachable']}")
        return health_info
    except Exception as e:
        logger.error(f"Unexpected error in search health endpoint: {e}", exc_info=True)
        # Fail open - return safe response
        return {
            "enabled": False,
            "reachable": False,
            "url": "",
            "index_prefix": "",
            "indices": [],
            "aliases": None,
            "last_sync_run": None,
            "pending_outbox": None,
            "error": "Health check failed",
        }


@router.post("/admin/search/bootstrap")
async def bootstrap_search_indices(
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Bootstrap search indices and aliases (admin only).

    Creates questions index and aliases if they don't exist.
    Returns current alias targets.

    Fails open: Returns safe response if Elasticsearch is disabled.
    """
    require_admin(current_user)

    try:
        result = ensure_questions_aliases_exist()
        return {
            "success": True,
            "created": result["created"],
            "index_name": result["index_name"],
            "read_alias": result["read_alias"],
            "write_alias": result["write_alias"],
        }
    except ValueError as e:
        # Elasticsearch disabled
        return {
            "success": False,
            "error": str(e),
            "created": False,
            "index_name": None,
            "read_alias": None,
            "write_alias": None,
        }
    except Exception as e:
        logger.error(f"Unexpected error in bootstrap endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bootstrap failed: {str(e)}")


@router.get("/admin/search/runs")
async def get_search_runs(
    days: int = Query(30, ge=1, le=365),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get search sync run history (admin/reviewer only).

    Args:
        days: Number of days to look back (default 30, max 365)
    """
    require_admin_or_reviewer(current_user)

    cutoff = datetime.utcnow() - timedelta(days=days)
    runs = (
        db.query(SearchSyncRun)
        .filter(SearchSyncRun.created_at >= cutoff)
        .order_by(desc(SearchSyncRun.created_at))
        .limit(100)
        .all()
    )

    return {
        "runs": [
            {
                "id": str(run.id),
                "run_type": run.run_type.value,
                "status": run.status.value,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "indexed_count": run.indexed_count,
                "deleted_count": run.deleted_count,
                "failed_count": run.failed_count,
                "details": run.details,
                "created_at": run.created_at.isoformat(),
            }
            for run in runs
        ]
    }


@router.get("/admin/search/outbox")
async def get_search_outbox(
    status: str | None = Query(None, description="Filter by status (pending, processing, done, failed)"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get search outbox events (admin/reviewer only).

    Args:
        status: Optional status filter
        limit: Maximum number of events to return
    """
    require_admin_or_reviewer(current_user)

    query = db.query(SearchOutbox)
    if status:
        try:
            status_enum = SearchOutboxStatus(status)
            query = query.filter(SearchOutbox.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    events = query.order_by(SearchOutbox.created_at.desc()).limit(limit).all()

    return {
        "events": [
            {
                "id": str(event.id),
                "event_type": event.event_type.value,
                "payload": event.payload,
                "status": event.status.value,
                "retry_count": event.retry_count,
                "last_error": event.last_error,
                "next_attempt_at": event.next_attempt_at.isoformat() if event.next_attempt_at else None,
                "created_at": event.created_at.isoformat(),
                "updated_at": event.updated_at.isoformat(),
            }
            for event in events
        ]
    }


@router.post("/admin/search/outbox/process")
async def process_outbox_manual(
    limit: int = Query(100, ge=1, le=1000),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Manually trigger outbox processing (admin only, for debugging).

    Args:
        limit: Maximum number of events to process
    """
    require_admin(current_user)

    try:
        result = process_outbox_batch(db, limit=limit)
        return {
            "success": True,
            "processed": result["processed"],
            "done": result["done"],
            "failed": result["failed"],
            "frozen": result.get("frozen", False),
        }
    except Exception as e:
        logger.error(f"Error processing outbox: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post(
    "/admin/search/reindex/nightly",
    dependencies=[Depends(require_not_exam_mode("search_reindex"))],
)
async def trigger_nightly_reindex(
    confirmation_phrase: str | None = Query(None, description="Confirmation phrase: 'RUN NIGHTLY REINDEX'"),
    reason: str | None = Query(None, description="Reason for manual reindex"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Manually trigger nightly reindex (admin only, requires police mode).

    Args:
        confirmation_phrase: Must be "RUN NIGHTLY REINDEX"
        reason: Reason for manual reindex (required)
    """
    require_admin(current_user)

    # Police mode check
    if confirmation_phrase != "RUN NIGHTLY REINDEX":
        raise HTTPException(
            status_code=400,
            detail="Invalid confirmation phrase. Must be exactly 'RUN NIGHTLY REINDEX'",
        )

    if not reason or len(reason.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Reason is required and must be at least 10 characters",
        )

    logger.warning(f"Manual nightly reindex triggered by {current_user.email}. Reason: {reason}")

    try:
        run = run_nightly_reindex(db)
        return {
            "success": run.status.value in ("done", "blocked_frozen", "disabled"),
            "run_id": str(run.id),
            "status": run.status.value,
            "indexed_count": run.indexed_count,
            "failed_count": run.failed_count,
            "details": run.details,
        }
    except Exception as e:
        logger.error(f"Error running nightly reindex: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reindex failed: {str(e)}")


# ============================================================================
# Search Runtime Configuration
# ============================================================================


class ReadinessCheckDetails(BaseModel):
    """Details for a single readiness check."""

    ok: bool
    details: dict[str, Any]


class ReadinessStatus(BaseModel):
    """Elasticsearch readiness status."""

    ready: bool
    blocking_reasons: list[str]
    checks: dict[str, ReadinessCheckDetails]


class SearchRuntimeStatus(BaseModel):
    """Search runtime status response."""

    requested_mode: str  # "postgres" | "elasticsearch" (what admin requested)
    effective_engine: str  # "postgres" | "elasticsearch" (what's actually used)
    enabled: bool
    es_reachable: bool
    last_switch: dict | None = None
    readiness: ReadinessStatus | None = None  # Only present if requested_mode == "elasticsearch"


class SearchSwitchRequest(BaseModel):
    """Request to switch search engine mode."""

    mode: str  # "postgres" | "elasticsearch"
    reason: str
    confirmation_phrase: str


def get_search_runtime_mode(db: Session) -> str:
    """
    Get current search engine mode from runtime config.

    Returns:
        "postgres" or "elasticsearch" (defaults to "postgres")
    """
    config = db.query(AlgoRuntimeConfig).first()

    if not config:
        return "postgres"

    config_json = config.config_json or {}
    return config_json.get("search_engine_mode", "postgres")


@router.get("/admin/search/runtime", response_model=SearchRuntimeStatus)
async def get_search_runtime(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get search runtime configuration (admin/reviewer only).

    Returns requested mode, effective engine, ES reachability, readiness, and last switch info.
    """
    require_admin_or_reviewer(current_user)

    # Get requested mode (what admin configured)
    requested_mode = get_search_runtime_mode(db)

    # Check ES reachability
    es_enabled = settings.ELASTICSEARCH_ENABLED
    es_reachable = False
    if es_enabled:
        try:
            from app.search.es_client import ping
            es_reachable = ping()
        except Exception:
            pass

    # Evaluate readiness if ES is requested
    readiness = None
    effective_engine = requested_mode
    
    if requested_mode == "elasticsearch":
        readiness_result = evaluate_elasticsearch_readiness(db)
        # Effective engine is ES only if readiness passes
        if readiness_result.ready:
            effective_engine = "elasticsearch"
        else:
            effective_engine = "postgres"
        
        # Convert to API response format
        readiness = ReadinessStatus(
            ready=readiness_result.ready,
            blocking_reasons=readiness_result.blocking_reasons,
            checks={
                name: ReadinessCheckDetails(ok=check.ok, details=check.details)
                for name, check in readiness_result.checks.items()
            },
        )
    elif requested_mode == "postgres":
        # Postgres mode - no readiness needed
        effective_engine = "postgres"

    # Get last switch info from algo_runtime_config
    config = db.query(AlgoRuntimeConfig).first()

    last_switch = None
    if config and config.changed_by_user_id and config.updated_at:
        # Check if search_engine_mode was changed (we'll infer from updated_at if config_json has it)
        config_json = config.config_json or {}
        if "search_engine_mode" in config_json:
            changed_by = db.query(User).filter(User.id == config.changed_by_user_id).first()
            last_switch = {
                "at": config.updated_at.isoformat(),
                "by": changed_by.email if changed_by else "unknown",
                "reason": config.reason or "",
            }

    return SearchRuntimeStatus(
        requested_mode=requested_mode,
        effective_engine=effective_engine,
        enabled=es_enabled,
        es_reachable=es_reachable,
        last_switch=last_switch,
        readiness=readiness,
    )


@router.post("/admin/search/runtime/switch")
async def switch_search_runtime(
    request: SearchSwitchRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Switch search engine mode (admin only, requires police mode).

    Args:
        request: Switch request with mode, reason, and confirmation phrase

    Returns:
        Success message with previous and new mode
    """
    require_admin(current_user)

    # Validate mode
    if request.mode not in ("postgres", "elasticsearch"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be 'postgres' or 'elasticsearch', got: {request.mode}",
        )

    # Check two-person approval requirement for enabling Elasticsearch in production
    if request.mode == "elasticsearch":
        from app.api.v1.endpoints.admin_approvals import (
            check_approval_required_or_raise,
            requires_two_person_approval,
        )
        
        if requires_two_person_approval("ELASTICSEARCH_ENABLE"):
            check_approval_required_or_raise(db, "ELASTICSEARCH_ENABLE", current_user, http_request)

    # Validate reason
    if not request.reason or len(request.reason.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Reason is required and must be at least 10 characters",
        )

    # Validate confirmation phrase
    is_valid, error_msg = validate_confirmation_phrase(
        action_type="SEARCH_ENGINE_SWITCH",
        phrase=request.confirmation_phrase,
        target_mode=request.mode,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg or "Invalid confirmation phrase")

    # Get current config
    stmt = select(AlgoRuntimeConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=500, detail="Runtime config not found")

    # Get current mode
    config_json = config.config_json or {}
    previous_mode = config_json.get("search_engine_mode", "postgres")

    # Check ES reachability if switching to elasticsearch
    warnings = []
    if request.mode == "elasticsearch":
        es_enabled = settings.ELASTICSEARCH_ENABLED
        if not es_enabled:
            warnings.append("es_unreachable_will_fallback")
        else:
            try:
                from app.search.es_client import ping
                if not ping():
                    warnings.append("es_unreachable_will_fallback")
            except Exception:
                warnings.append("es_unreachable_will_fallback")

    # Update config_json with new search_engine_mode
    config_json["search_engine_mode"] = request.mode
    config.config_json = config_json
    config.reason = request.reason
    config.changed_by_user_id = current_user.id
    config.updated_at = datetime.now(UTC)

    # Prepare audit event
    previous_config = {
        "search_engine_mode": previous_mode,
        "config_json": config.config_json,
    }
    new_config = {
        "search_engine_mode": request.mode,
        "config_json": config_json,
        "details": {
            "confirmation_phrase_provided": bool(request.confirmation_phrase),
            "warnings": warnings,
        },
    }

    # Create audit event
    switch_event = AlgoSwitchEvent(
        previous_config=previous_config,
        new_config=new_config,
        reason=request.reason,
        created_by_user_id=current_user.id,
    )
    db.add(switch_event)

    db.commit()
    db.refresh(config)

    logger.info(
        f"Search engine mode switched from {previous_mode} to {request.mode} "
        f"by {current_user.email}. Reason: {request.reason}"
    )

    response = {
        "message": "Search engine mode switched successfully",
        "previous_mode": previous_mode,
        "new_mode": request.mode,
    }
    if warnings:
        response["warnings"] = warnings

    return response


@router.get("/admin/search/readiness")
async def get_search_readiness(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Get Elasticsearch readiness evaluation (admin only).

    Returns readiness checks and blocking reasons.
    """
    require_admin(current_user)

    readiness_result = evaluate_elasticsearch_readiness(db)
    
    return ReadinessStatus(
        ready=readiness_result.ready,
        blocking_reasons=readiness_result.blocking_reasons,
        checks={
            name: ReadinessCheckDetails(ok=check.ok, details=check.details)
            for name, check in readiness_result.checks.items()
        },
    )
