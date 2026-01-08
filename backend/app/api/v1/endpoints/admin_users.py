"""Admin user management endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.core.security import generate_password_reset_token, hash_password
from app.db.session import get_db
from app.models.auth import PasswordResetToken
from app.models.user import User, UserRole
from app.schemas.admin_users import (
    PasswordResetResponse,
    UserCreate,
    UserListItem,
    UserResponse,
    UserUpdate,
    UsersListResponse,
)

router = APIRouter(prefix="/admin/users", tags=["Admin - Users"])


@router.get(
    "",
    response_model=UsersListResponse,
    summary="List users",
    description="Get paginated list of users with optional search and filters.",
)
async def list_users(
    q: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    status: Optional[str] = Query(None, description="Filter by status: active|disabled"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> UsersListResponse:
    """List users with pagination and filters."""
    query = db.query(User)

    # Search filter
    if q:
        search_term = f"%{q.lower()}%"
        query = query.filter(
            or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
            )
        )

    # Role filter
    if role:
        try:
            role_enum = UserRole(role)
            query = query.filter(User.role == role_enum.value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}",
            )

    # Status filter
    if status:
        if status == "active":
            query = query.filter(User.is_active == True)
        elif status == "disabled":
            query = query.filter(User.is_active == False)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Use 'active' or 'disabled'",
            )

    # Get total count
    total = query.count()

    # Pagination
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    items = [UserListItem.model_validate(user) for user in users]

    return UsersListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user account.",
)
async def create_user(
    request: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> UserResponse:
    """Create a new user."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{request.email}' already exists",
        )

    # Validate role
    try:
        role_enum = UserRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request.role}",
        )

    # Create user with temporary unusable password
    # User will need to reset password via email
    temp_password_hash = hash_password("TEMP_PASSWORD_NOT_USABLE_" + str(datetime.now(UTC).timestamp()))

    user = User(
        name=request.name,
        email=request.email,
        password_hash=temp_password_hash,
        role=role_enum.value,
        is_active=request.is_active,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user information.",
)
async def update_user(
    user_id: UUID,
    request: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> UserResponse:
    """Update a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "role":
            try:
                role_enum = UserRole(value)
                setattr(user, field, role_enum.value)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role: {value}",
                )
        else:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/enable",
    response_model=UserResponse,
    summary="Enable user",
    description="Enable a disabled user account.",
)
async def enable_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> UserResponse:
    """Enable a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = True
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/disable",
    response_model=UserResponse,
    summary="Disable user",
    description="Disable a user account (soft lockout).",
)
async def disable_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> UserResponse:
    """Disable a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-disable
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot disable your own account",
        )

    user.is_active = False
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/password-reset",
    response_model=PasswordResetResponse,
    summary="Trigger password reset",
    description="Trigger password reset email for a user.",
)
async def trigger_password_reset(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
) -> PasswordResetResponse:
    """Trigger password reset for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate reset token
    reset_token = generate_password_reset_token()
    token_hash = hash_token(reset_token)

    # Create reset token record
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    reset_token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(reset_token_record)
    db.commit()

    # Send password reset email
    from app.core.config import settings
    from app.core.logging import get_logger
    from app.services.email.service import send_email

    logger = get_logger(__name__)
    email_sent = False
    message = "Password reset token generated."

    try:
        reset_link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={reset_token}"
        email_subject = "Password Reset Request"
        email_body_text = f"""
An administrator has requested a password reset for your account.

Click the link below to reset your password:
{reset_link}

This link will expire in 24 hours.

If you did not request this reset, please contact support.
"""
        email_body_html = f"""
<html>
<body>
<p>An administrator has requested a password reset for your account.</p>
<p><a href="{reset_link}">Click here to reset your password</a></p>
<p>Or copy and paste this link into your browser:</p>
<p>{reset_link}</p>
<p>This link will expire in 24 hours.</p>
<p>If you did not request this reset, please contact support.</p>
</body>
</html>
"""
        send_email(
            to=user.email,
            subject=email_subject,
            body_text=email_body_text.strip(),
            body_html=email_body_html.strip(),
        )
        email_sent = True
        message = "Password reset email sent successfully."
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}", exc_info=True)
        message = f"Password reset token generated, but email sending failed: {str(e)}"

    return PasswordResetResponse(
        message=message,
        email_sent=email_sent,
    )
