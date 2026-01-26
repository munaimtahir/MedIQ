"""Police-mode validation for critical admin actions."""

from fastapi import Request, status

from app.core.app_exceptions import raise_app_error


def validate_police_confirm(
    request: Request,
    confirmation_phrase: str,
    reason: str | None,
    expected_phrase: str,
) -> str:
    """
    Validate police-mode confirmation and return reason.
    
    This function validates:
    - confirmation_phrase matches expected_phrase exactly
    - reason is non-empty
    - Attaches reason to request.state for audit logging
    
    Args:
        request: FastAPI request object
        confirmation_phrase: Confirmation phrase from request body
        reason: Reason from request body
        expected_phrase: The exact confirmation phrase required
    
    Returns:
        Validated reason string
    
    Raises:
        AppError: If validation fails
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(
            request_data: SomeRequest,  # Must include confirmation_phrase and reason
            request: Request,
            ...
        ):
            reason = validate_police_confirm(
                request,
                request_data.confirmation_phrase,
                request_data.reason,
                "DRAIN EMAIL OUTBOX",
            )
            # reason is now validated and attached to request.state
            ...
    """
    # Validate confirmation phrase matches exactly
    if confirmation_phrase != expected_phrase:
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_CONFIRMATION_PHRASE",
            message=f"Confirmation phrase must be exactly: {expected_phrase}",
        )

    # Validate reason is non-empty
    if not reason or not reason.strip():
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="REASON_REQUIRED",
            message="Reason is required for critical actions",
        )

    validated_reason = reason.strip()
    
    # Attach reason to request state for audit logging
    request.state.police_reason = validated_reason
    request.state.police_confirmation_phrase = confirmation_phrase

    return validated_reason


def get_police_reason(request: Request) -> str | None:
    """Get police-mode reason from request state."""
    return getattr(request.state, "police_reason", None)
