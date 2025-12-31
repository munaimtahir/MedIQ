"""MFA schemas."""

from pydantic import BaseModel


class MFASetupResponse(BaseModel):
    """MFA TOTP setup response."""

    provisioning_uri: str
    secret: str  # Return once for QR code generation


class MFAVerifyRequest(BaseModel):
    """MFA verification request."""

    code: str | None = None  # TOTP code
    password: str | None = None  # Password (for disable/regenerate)


class MFAVerifyResponse(BaseModel):
    """MFA verification response."""

    status: str = "ok"
    backup_codes: list[str] | None = None  # Return once


class MFACompleteRequest(BaseModel):
    """MFA completion request (step-up login)."""

    mfa_token: str
    code: str | None = None  # TOTP code
    backup_code: str | None = None  # Backup code (alternative)


class MFACompleteResponse(BaseModel):
    """MFA completion response."""

    user: dict
    tokens: dict


class MFADisableRequest(BaseModel):
    """MFA disable request."""

    password: str | None = None  # Password confirmation
    code: str | None = None  # TOTP code confirmation


class MFADisableResponse(BaseModel):
    """MFA disable response."""

    status: str = "ok"
    message: str = "MFA disabled successfully"
