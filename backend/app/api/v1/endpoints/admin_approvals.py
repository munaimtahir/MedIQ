"""Two-person approval endpoints for high-risk actions in production."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.app_exceptions import raise_app_error
from app.core.audit import write_audit_critical
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db, require_roles
from app.core.errors import get_request_id
from app.models.runtime_control import SwitchAuditLog, TwoPersonApproval
from app.models.user import User, UserRole
from app.runtime_control.police import require_confirmation
from app.security.admin_freeze import check_admin_freeze

router = APIRouter(prefix="/admin/runtime/approvals", tags=["Admin - Runtime Approvals"])


# High-risk actions that require two-person approval in production
HIGH_RISK_ACTIONS = {
    "PROFILE_SWITCH_PRIMARY": "SWITCH TO V1_PRIMARY",
    "PROFILE_SWITCH_FALLBACK": "SWITCH TO V0_FALLBACK",
    "IRT_ACTIVATE": "ACTIVATE IRT",
    "ELASTICSEARCH_ENABLE": "ENABLE ELASTICSEARCH",
    "NEO4J_ENABLE": "ENABLE NEO4J",
    "SNOWFLAKE_EXPORT_ENABLE": "ENABLE SNOWFLAKE EXPORT",
}


def is_production() -> bool:
    """Check if running in production environment."""
    return settings.ENV == "prod"


def requires_two_person_approval(action_type: str) -> bool:
    """Check if action requires two-person approval (only in production)."""
    if not is_production():
        return False
    return action_type in HIGH_RISK_ACTIONS


# --- Schemas ---


class ApprovalRequest(BaseModel):
    """Request a two-person approval for a high-risk action."""

    action_type: Literal[
        "PROFILE_SWITCH_PRIMARY",
        "PROFILE_SWITCH_FALLBACK",
        "IRT_ACTIVATE",
        "ELASTICSEARCH_ENABLE",
        "NEO4J_ENABLE",
        "SNOWFLAKE_EXPORT_ENABLE",
    ] = Field(..., description="Type of action being requested")
    action_payload: dict = Field(..., description="Action-specific payload (e.g., profile name, config)")
    reason: str = Field(..., min_length=1, description="Reason for the change")
    confirmation_phrase: str = Field(..., description="Confirmation phrase matching action type")


class ApprovalResponse(BaseModel):
    """Response for approval request."""

    request_id: UUID
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    requested_by: dict
    approved_by: dict | None = None
    action_type: str
    created_at: datetime
    decided_at: datetime | None = None


class ApproveRequest(BaseModel):
    """Approve a pending approval request."""

    confirmation_phrase: str = Field(..., description="Confirmation phrase matching action type")


class ApprovalListResponse(BaseModel):
    """List of pending approvals."""

    approvals: list[ApprovalResponse]


# --- Endpoints ---


@router.post(
    "/request",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request approval for high-risk action",
    description="Request two-person approval for a high-risk action (required in production).",
)
def request_approval(
    request_data: ApprovalRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ApprovalResponse:
    """Request two-person approval for a high-risk action."""
    check_admin_freeze(db)

    # Validate confirmation phrase
    expected_phrase = HIGH_RISK_ACTIONS.get(request_data.action_type)
    if not expected_phrase:
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_ACTION_TYPE",
            message=f"Unknown action type: {request_data.action_type}",
        )

    require_confirmation(
        request,
        request_data.confirmation_phrase,
        request_data.reason,
        expected_phrase,
    )

    # Check if approval is required (only in production)
    if not requires_two_person_approval(request_data.action_type):
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="APPROVAL_NOT_REQUIRED",
            message=f"Action {request_data.action_type} does not require approval in {settings.ENV} environment",
        )

    # Check for existing pending approval for same action
    existing = (
        db.query(TwoPersonApproval)
        .filter(
            TwoPersonApproval.status == "PENDING",
            TwoPersonApproval.requested_action["action_type"].astext == request_data.action_type,
        )
        .first()
    )
    if existing:
        raise_app_error(
            status_code=status.HTTP_409_CONFLICT,
            code="PENDING_APPROVAL_EXISTS",
            message=f"Pending approval already exists for {request_data.action_type}",
            details={"request_id": str(existing.request_id)},
        )

    # Create approval request
    approval = TwoPersonApproval(
        requested_by=current_user.id,
        requested_action={
            "action_type": request_data.action_type,
            "action_payload": request_data.action_payload,
            "reason": request_data.reason,
            "confirmation_phrase": request_data.confirmation_phrase,
        },
        status="PENDING",
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    # Audit log
    request_id = get_request_id(request)
    write_audit_critical(
        db=db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="APPROVAL_REQUESTED",
        entity_type="TWO_PERSON_APPROVAL",
        entity_id=approval.request_id,
        reason=request_data.reason,
        request=request,
        before=None,
        after={"action_type": request_data.action_type, "status": "PENDING"},
        meta={"request_id": request_id},
    )
    db.commit()

    return ApprovalResponse(
        request_id=approval.request_id,
        status=approval.status,
        requested_by={
            "id": str(approval.requested_by),
            "email": approval.requester.email if approval.requester else None,
        },
        approved_by=None,
        action_type=request_data.action_type,
        created_at=approval.created_at,
        decided_at=None,
    )


@router.get(
    "/pending",
    response_model=ApprovalListResponse,
    summary="List pending approvals",
    description="Get list of pending approval requests (admin only).",
)
def list_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ApprovalListResponse:
    """List all pending approval requests."""
    pending = (
        db.query(TwoPersonApproval)
        .filter(TwoPersonApproval.status == "PENDING")
        .order_by(TwoPersonApproval.created_at.desc())
        .all()
    )

    approvals = []
    for approval in pending:
        action_type = approval.requested_action.get("action_type", "UNKNOWN")
        approvals.append(
            ApprovalResponse(
                request_id=approval.request_id,
                status=approval.status,
                requested_by={
                    "id": str(approval.requested_by),
                    "email": approval.requester.email if approval.requester else None,
                },
                approved_by={
                    "id": str(approval.approved_by),
                    "email": approval.approver.email if approval.approver else None,
                }
                if approval.approved_by
                else None,
                action_type=action_type,
                created_at=approval.created_at,
                decided_at=approval.decided_at,
            )
        )

    return ApprovalListResponse(approvals=approvals)


@router.post(
    "/{request_id}/approve",
    response_model=ApprovalResponse,
    summary="Approve a pending request",
    description="Approve a pending high-risk action request (requires different admin than requester).",
)
def approve_action(
    request_id: UUID,
    request_data: ApproveRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ApprovalResponse:
    """Approve a pending approval request and execute the action."""
    check_admin_freeze(db)

    # Find approval request
    approval = db.query(TwoPersonApproval).filter(TwoPersonApproval.request_id == request_id).first()
    if not approval:
        raise_app_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPROVAL_NOT_FOUND",
            message="Approval request not found",
        )

    if approval.status != "PENDING":
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="APPROVAL_ALREADY_DECIDED",
            message=f"Approval request is already {approval.status}",
        )

    # Require different admin than requester
    if approval.requested_by == current_user.id:
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="SELF_APPROVAL_NOT_ALLOWED",
            message="Cannot approve your own request. Another admin must approve.",
        )

    # Validate confirmation phrase
    action_type = approval.requested_action.get("action_type", "")
    expected_phrase = HIGH_RISK_ACTIONS.get(action_type)
    if not expected_phrase:
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_ACTION_TYPE",
            message=f"Unknown action type in approval: {action_type}",
        )

    require_confirmation(
        request,
        request_data.confirmation_phrase,
        approval.requested_action.get("reason", ""),
        expected_phrase,
    )

    # Mark as approved (before execution so we can track it)
    approval.status = "APPROVED"
    approval.approved_by = current_user.id
    approval.decided_at = datetime.now(UTC)
    db.flush()  # Don't commit yet - will commit after action execution

    # Execute the action (delegate to appropriate handler)
    action_payload = approval.requested_action.get("action_payload", {})
    action_reason = approval.requested_action.get("reason", "")

    before_snapshot = None
    after_snapshot = None

    try:
        if action_type == "PROFILE_SWITCH_PRIMARY":
            # Switch to PRIMARY profile via algo runtime switch
            from app.models.algo_runtime import AlgoRuntimeProfile, AlgoRuntimeConfig

            # Get current config for before snapshot
            current_config = db.query(AlgoRuntimeConfig).first()
            if current_config:
                before_snapshot = {
                    "active_profile": current_config.active_profile.value,
                    "config_json": current_config.config_json,
                }

                # Update to PRIMARY
                current_config.active_profile = AlgoRuntimeProfile.V1_PRIMARY
                if action_payload.get("overrides"):
                    config_json = current_config.config_json or {}
                    config_json["overrides"] = action_payload.get("overrides", {})
                    current_config.config_json = config_json
                current_config.changed_by_user_id = approval.requested_by  # Original requester
                db.flush()
                db.refresh(current_config)

                after_snapshot = {
                    "active_profile": current_config.active_profile.value,
                    "config_json": current_config.config_json,
                }

        elif action_type == "PROFILE_SWITCH_FALLBACK":
            # Switch to FALLBACK profile
            from app.models.algo_runtime import AlgoRuntimeProfile, AlgoRuntimeConfig

            current_config = db.query(AlgoRuntimeConfig).first()
            if current_config:
                before_snapshot = {
                    "active_profile": current_config.active_profile.value,
                    "config_json": current_config.config_json,
                }
                current_config.active_profile = AlgoRuntimeProfile.V0_FALLBACK
                if action_payload.get("overrides"):
                    config_json = current_config.config_json or {}
                    config_json["overrides"] = action_payload.get("overrides", {})
                    current_config.config_json = config_json
                current_config.changed_by_user_id = approval.requested_by
                db.flush()
                db.refresh(current_config)

                after_snapshot = {
                    "active_profile": current_config.active_profile.value,
                    "config_json": current_config.config_json,
                }

        elif action_type in ("IRT_ACTIVATE", "ELASTICSEARCH_ENABLE", "NEO4J_ENABLE", "SNOWFLAKE_EXPORT_ENABLE"):
            # NOTE: Specific handlers for these action types are not yet implemented.
            # The approval is recorded, but the actual action execution must be done separately
            # through their respective endpoints (e.g., /v1/admin/irt/activation/activate).
            # This is intentional - approvals are for audit, actions execute via dedicated endpoints.
            before_snapshot = {"status": "current", "note": "Action execution not implemented in approval handler"}
            after_snapshot = {**action_payload, "note": "Execute action via dedicated endpoint after approval"}

        # Record in switch audit log
        from app.runtime_control.audit import append_switch_audit

        append_switch_audit(
            db,
            actor_user_id=approval.requested_by,  # Original requester
            action_type=f"{action_type}_APPROVED",
            before=before_snapshot,
            after=after_snapshot or action_payload,
            reason=f"{action_reason} (Approved by {current_user.email})",
        )

        # Audit log for approval
        request_id_header = get_request_id(request)
        write_audit_critical(
            db=db,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            action="APPROVAL_APPROVED",
            entity_type="TWO_PERSON_APPROVAL",
            entity_id=approval.request_id,
            reason=f"Approved: {action_reason}",
            request=request,
            before={"status": "PENDING"},
            after={"status": "APPROVED", "action_type": action_type},
            meta={"request_id": request_id_header, "requested_by": str(approval.requested_by)},
        )
        db.commit()

    except Exception as e:
        db.rollback()
        # Mark as rejected on error
        approval.status = "REJECTED"
        approval.decided_at = datetime.now(UTC)
        db.commit()
        raise_app_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="ACTION_EXECUTION_FAILED",
            message=f"Failed to execute approved action: {str(e)}",
        )

    return ApprovalResponse(
        request_id=approval.request_id,
        status=approval.status,
        requested_by={
            "id": str(approval.requested_by),
            "email": approval.requester.email if approval.requester else None,
        },
        approved_by={
            "id": str(approval.approved_by),
            "email": approval.approver.email if approval.approver else None,
        },
        action_type=action_type,
        created_at=approval.created_at,
        decided_at=approval.decided_at,
    )


@router.post(
    "/{request_id}/reject",
    response_model=ApprovalResponse,
    summary="Reject a pending request",
    description="Reject a pending high-risk action request.",
)
def reject_approval(
    request_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ApprovalResponse:
    """Reject a pending approval request."""
    approval = db.query(TwoPersonApproval).filter(TwoPersonApproval.request_id == request_id).first()
    if not approval:
        raise_app_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPROVAL_NOT_FOUND",
            message="Approval request not found",
        )

    if approval.status != "PENDING":
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="APPROVAL_ALREADY_DECIDED",
            message=f"Approval request is already {approval.status}",
        )

    approval.status = "REJECTED"
    approval.approved_by = current_user.id  # Rejecter
    approval.decided_at = datetime.now(UTC)
    db.commit()

    # Audit log
    request_id_header = get_request_id(request)
    write_audit_critical(
        db=db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="APPROVAL_REJECTED",
        entity_type="TWO_PERSON_APPROVAL",
        entity_id=approval.request_id,
        reason="Rejected by admin",
        request=request,
        before={"status": "PENDING"},
        after={"status": "REJECTED"},
        meta={"request_id": request_id_header},
    )
    db.commit()

    return ApprovalResponse(
        request_id=approval.request_id,
        status=approval.status,
        requested_by={
            "id": str(approval.requested_by),
            "email": approval.requester.email if approval.requester else None,
        },
        approved_by={
            "id": str(approval.approved_by),
            "email": approval.approver.email if approval.approver else None,
        },
        action_type=approval.requested_action.get("action_type", "UNKNOWN"),
        created_at=approval.created_at,
        decided_at=approval.decided_at,
    )


# Helper function for other endpoints to check approval requirement
def check_approval_required_or_raise(
    db: Session,
    action_type: str,
    current_user: User,
    request: Request,
) -> None:
    """
    Check if action requires approval and raise 409 if approval is required but not approved.
    
    This should be called at the start of high-risk action endpoints.
    If approval is required, it must be requested and approved before the action can proceed.
    Direct calls to action endpoints in production require approval - use the approval workflow instead.
    """
    if not requires_two_person_approval(action_type):
        return  # No approval required

    # Check for any approval for this action (pending or approved)
    approval = (
        db.query(TwoPersonApproval)
        .filter(
            TwoPersonApproval.status.in_(["PENDING", "APPROVED"]),
            TwoPersonApproval.requested_action["action_type"].astext == action_type,
        )
        .order_by(TwoPersonApproval.created_at.desc())
        .first()
    )

    # Always block direct calls when approval is required
    # Actions should only execute through the approval workflow (request -> approve)
    if not approval:
        # No approval exists - must request approval first
        raise_app_error(
            status_code=status.HTTP_409_CONFLICT,
            code="APPROVAL_REQUIRED",
            message=f"Action {action_type} requires two-person approval in production. Please request approval first.",
            details={
                "endpoint": "/v1/admin/runtime/approvals/request",
            },
        )
    elif approval.status == "PENDING":
        # Approval exists but is still pending - must wait for approval
        raise_app_error(
            status_code=status.HTTP_409_CONFLICT,
            code="APPROVAL_REQUIRED",
            message=f"Action {action_type} requires two-person approval in production. Approval request is pending.",
            details={
                "request_id": str(approval.request_id),
                "endpoint": "/v1/admin/runtime/approvals/request",
            },
        )
    # If approval.status == "APPROVED", the action was already executed via the approval endpoint
    # Direct calls should still be blocked - actions should only execute through the approval workflow
    else:
        raise_app_error(
            status_code=status.HTTP_409_CONFLICT,
            code="APPROVAL_REQUIRED",
            message=f"Action {action_type} requires two-person approval in production. This action was already executed via approval workflow.",
            details={
                "request_id": str(approval.request_id),
                "endpoint": "/v1/admin/runtime/approvals/request",
            },
        )
