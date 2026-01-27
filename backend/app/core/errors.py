"""Error handling and consistent error response format."""

import uuid
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Mobile-safe error response envelope.
    
    Format: {error_code, message, details}
    Compatible with mobile clients requiring stable error codes.
    """

    error_code: str
    message: str
    details: Any | None = None
    request_id: str | None = None


def get_request_id(request: Request) -> str:
    """Get request ID from request state or generate new one."""
    if hasattr(request.state, "request_id"):
        return request.state.request_id
    return str(uuid.uuid4())


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors (422)."""
    request_id = get_request_id(request)
    errors = exc.errors()

    details: list[dict[str, Any]] = []
    use_limit_code = False
    for error in errors:
        ctx = error.get("ctx") or {}
        lim = ctx.get("max_length") or ctx.get("max_inclusive") or ctx.get("ge")
        t = error.get("type", "")
        if "too_long" in t or "too_short" in t or "greater_than" in t:
            use_limit_code = True
        d: dict[str, Any] = {
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "issue": error.get("msg", "Validation error"),
            "type": error.get("type", "validation_error"),
        }
        if lim is not None:
            d["limit"] = int(lim) if isinstance(lim, (int, float)) else lim
        details.append(d)

    code = "VALIDATION_LIMIT_EXCEEDED" if use_limit_code else "VALIDATION_ERROR"
    message = "Validation limit exceeded" if use_limit_code else "Invalid request data"

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error_code=code,
            message=message,
            details=details,
            request_id=request_id,
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    from app.core.app_exceptions import AppError

    request_id = get_request_id(request)

    # Handle AppError (has structured detail with code)
    if isinstance(exc, AppError):
        response = JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=request_id,
            ).model_dump(),
        )
        # Add Retry-After header for rate limiting
        if (
            exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            and exc.details
            and isinstance(exc.details, dict)
        ):
            retry_after = exc.details.get("retry_after_seconds")
            if retry_after:
                response.headers["Retry-After"] = str(retry_after)
        return response

    # Handle standard HTTPException
    # Extract details if provided
    details = None
    code = "HTTP_ERROR"
    if isinstance(exc.detail, dict):
        # Check if it's already in our format
        if "code" in exc.detail:
            code = exc.detail["code"]
            message = exc.detail.get("message", "An error occurred")
            details = exc.detail.get("details")
        else:
            details = exc.detail.copy()
            message = details.pop("message", exc.detail.get("detail", "An error occurred"))
    elif isinstance(exc.detail, str):
        message = exc.detail
    else:
        message = str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=code,
            message=message,
            details=details,
            request_id=request_id,
        ).model_dump(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions (500)."""
    request_id = get_request_id(request)

    # In production, don't expose internal error details
    from app.core.config import settings

    if settings.ENV == "prod":
        message = "An internal server error occurred"
        details = None
    else:
        message = str(exc)
        details = {"type": type(exc).__name__}

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message=message,
            details=details,
            request_id=request_id,
        ).model_dump(),
    )
