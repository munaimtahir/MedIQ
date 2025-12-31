"""Authentication schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# Request schemas
class SignupRequest(BaseModel):
    """Signup request schema."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()


class RefreshRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request schema."""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""

    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# Response schemas
class UserResponse(BaseModel):
    """User response schema."""

    id: UUID
    name: str
    email: str
    role: str
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class TokensResponse(BaseModel):
    """Tokens response schema."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class SignupResponse(BaseModel):
    """Signup response schema."""

    user: UserResponse
    tokens: TokensResponse


class LoginResponse(BaseModel):
    """Login response schema."""

    user: UserResponse | None = None
    tokens: TokensResponse | None = None
    mfa_required: bool = False
    mfa_token: str | None = None
    method: str | None = None  # "totp"


class RefreshResponse(BaseModel):
    """Refresh response schema."""

    tokens: TokensResponse


class StatusResponse(BaseModel):
    """Generic status response schema."""

    status: Literal["ok"]
    message: str | None = None


class MeResponse(BaseModel):
    """Current user response schema."""

    user: UserResponse

