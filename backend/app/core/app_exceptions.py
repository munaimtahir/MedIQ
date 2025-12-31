"""Application-specific exceptions for consistent error handling."""

from typing import Any

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Application error with standardized error code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | list[Any] | None = None,
    ):
        """Initialize application error."""
        super().__init__(
            status_code=status_code,
            detail={
                "code": code,
                "message": message,
                "details": details,
            },
        )
        self.code = code
        self.message = message
        self.details = details


def raise_app_error(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
) -> None:
    """Raise an application error with standardized format."""
    raise AppError(status_code=status_code, code=code, message=message, details=details)

