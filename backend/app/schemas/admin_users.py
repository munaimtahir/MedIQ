"""Schemas for admin user management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserListItem(BaseModel):
    """User list item response."""

    id: UUID
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsersListResponse(BaseModel):
    """Paginated users list response."""

    items: list[UserListItem]
    page: int
    page_size: int
    total: int


class UserCreate(BaseModel):
    """Schema for creating a user."""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: str = Field(..., pattern="^(STUDENT|ADMIN|REVIEWER)$")
    is_active: bool = Field(default=True)


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, pattern="^(STUDENT|ADMIN|REVIEWER)$")
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response schema."""

    id: UUID
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PasswordResetResponse(BaseModel):
    """Password reset response."""

    message: str
    email_sent: bool = False
