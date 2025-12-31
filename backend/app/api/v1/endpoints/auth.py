"""Authentication endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.abuse_protection import (
    check_email_locked,
    check_ip_locked,
    clear_login_failures,
    record_login_failure,
)
from app.core.app_exceptions import raise_app_error
from app.core.config import settings
from app.core.rate_limit_deps import (
    require_rate_limit_login_email,
    require_rate_limit_login_ip,
    require_rate_limit_refresh,
    require_rate_limit_reset_email,
    require_rate_limit_reset_ip,
    require_rate_limit_signup_ip,
)
from app.core.rate_limit import get_client_ip
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_password_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.security_logging import log_security_event
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.auth import PasswordResetToken, RefreshToken
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MeResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    SignupResponse,
    StatusResponse,
    TokensResponse,
    UserResponse,
)

router = APIRouter(tags=["Auth"])


def _create_tokens_for_user(user: User, db: Session) -> TokensResponse:
    """Create access and refresh tokens for a user."""
    # Create access token
    access_token = create_access_token(str(user.id), user.role)

    # Create refresh token
    refresh_token = create_refresh_token()
    token_hash = hash_token(refresh_token)

    # Calculate expiry
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Revoke old refresh tokens for this user (single session per user)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": datetime.now(timezone.utc)})

    # Create new refresh token record
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(db_refresh_token)
    db.commit()

    return TokensResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up",
    description="Create a new user account. Returns user data and authentication tokens.",
)
async def signup(
    request_data: SignupRequest,
    request: Request,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(require_rate_limit_signup_ip),
) -> SignupResponse:
    """Sign up a new user."""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request_data.email).first()
    if existing_user:
        log_security_event(
            request,
            event_type="auth_signup",
            outcome="deny",
            reason_code="CONFLICT",
        )
        raise_app_error(
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            message="Email already registered",
        )

    # Create user
    user = User(
        name=request_data.name,
        email=request_data.email,
        password_hash=hash_password(request_data.password),
        role=UserRole.STUDENT.value,
        onboarding_completed=False,
        is_active=True,
        email_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Log successful signup
    log_security_event(
        request,
        event_type="auth_signup",
        outcome="allow",
        user_id=str(user.id),
    )

    # Create tokens
    tokens = _create_tokens_for_user(user, db)

    return SignupResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in",
    description="Authenticate with email and password. Returns user data and authentication tokens.",
)
async def login(
    request_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _rate_limit_ip: None = Depends(require_rate_limit_login_ip),
) -> LoginResponse:
    """Log in a user."""
    ip = get_client_ip(request)
    email_normalized = request_data.email.lower().strip()

    # Rate limit by email
    require_rate_limit_login_email(email_normalized, request)

    # Check IP and email lockouts before processing
    check_ip_locked(ip, request)
    check_email_locked(email_normalized, request)

    # Find user by email
    user = db.query(User).filter(User.email == email_normalized).first()

    # Timing protection: always verify password to prevent timing leaks
    # Use a dummy hash if user doesn't exist or has no password (OAuth-only)
    dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$dummy$dummy"
    password_hash = user.password_hash if (user and user.password_hash) else dummy_hash

    # Verify password (this takes similar time whether user exists or not)
    password_valid = verify_password(request_data.password, password_hash) if password_hash != dummy_hash else False

    # Generic error for invalid credentials (don't reveal if email exists)
    if not user or not password_valid:
        # Record failure
        record_login_failure(email_normalized, ip)

        # Log security event
        log_security_event(
            request,
            event_type="auth_login_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
        )

        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Invalid email or password",
        )

    # Check if user is active
    if not user.is_active:
        log_security_event(
            request,
            event_type="auth_login_failed",
            outcome="deny",
            reason_code="FORBIDDEN",
            user_id=str(user.id),
        )
        raise_app_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="User account is inactive",
        )

    # Clear failure counters on successful login
    clear_login_failures(email_normalized, ip)

    # Check if MFA is enabled
    from app.models.mfa import MFATOTP
    from app.core.mfa import create_mfa_token

    mfa_totp = db.query(MFATOTP).filter(MFATOTP.user_id == user.id, MFATOTP.enabled == True).first()

    if mfa_totp:
        # MFA required - return step-up token
        mfa_token = create_mfa_token(str(user.id))

        log_security_event(
            request,
            event_type="mfa_challenge_issued",
            outcome="allow",
            user_id=str(user.id),
        )

        return LoginResponse(
            mfa_required=True,
            mfa_token=mfa_token,
            method="totp",
        )

    # No MFA - proceed with normal login
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Log successful login
    log_security_event(
        request,
        event_type="auth_login_success",
        outcome="allow",
        user_id=str(user.id),
    )

    # Create tokens
    tokens = _create_tokens_for_user(user, db)

    return LoginResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh tokens",
    description="Refresh access and refresh tokens. Implements token rotation.",
)
async def refresh(
    request_data: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RefreshResponse:
    """Refresh access and refresh tokens with rotation."""
    # Hash the provided refresh token
    token_hash = hash_token(request_data.refresh_token)

    # Rate limit by user (will be applied after we get user_id)

    # Find active refresh token
    refresh_token_record = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
        .first()
    )

    if not refresh_token_record or not refresh_token_record.is_active():
        log_security_event(
            request,
            event_type="auth_refresh_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Invalid or expired refresh token",
        )

    # Get user
    user = refresh_token_record.user
    if not user or not user.is_active:
        log_security_event(
            request,
            event_type="auth_refresh_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="User not found or inactive",
        )

    # Rate limit by user
    require_rate_limit_refresh(str(user.id), request)

    # Rotate: revoke old token
    refresh_token_record.revoked_at = datetime.now(timezone.utc)

    # Create new tokens
    new_access_token = create_access_token(str(user.id), user.role)
    new_refresh_token = create_refresh_token()
    new_token_hash = hash_token(new_refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Create new refresh token record
    new_refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=expires_at,
    )
    new_refresh_token_record.replaced_by_token_id = refresh_token_record.id
    db.add(new_refresh_token_record)

    # Link old token to new one
    refresh_token_record.replaced_by_token_id = new_refresh_token_record.id

    db.commit()

    # Log successful refresh
    log_security_event(
        request,
        event_type="auth_refresh_success",
        outcome="allow",
        user_id=str(user.id),
    )

    return RefreshResponse(
        tokens=TokensResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )
    )


@router.post(
    "/logout",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out",
    description="Revoke a refresh token. Access tokens remain valid until expiry.",
)
async def logout(
    request_data: LogoutRequest,
    db: Session = Depends(get_db),
) -> StatusResponse:
    """Log out by revoking refresh token."""
    # Hash the provided refresh token
    token_hash = hash_token(request_data.refresh_token)

    # Find and revoke the token (idempotent)
    refresh_token_record = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
        .first()
    )

    if refresh_token_record:
        refresh_token_record.revoked_at = datetime.now(timezone.utc)
        db.commit()
        log_security_event(
            request,
            event_type="auth_logout",
            outcome="allow",
            user_id=str(refresh_token_record.user_id),
        )

    return StatusResponse(status="ok")


@router.post(
    "/logout-all",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out all devices",
    description="Revoke all refresh tokens for the current user (logs out all devices).",
)
async def logout_all(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    """Log out all devices by revoking all refresh tokens."""
    # Revoke all refresh tokens for this user
    revoked_count = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .update({"revoked_at": datetime.now(timezone.utc)})
    )
    db.commit()

    # Log logout all
    log_security_event(
        request,
        event_type="auth_logout_all",
        outcome="allow",
        user_id=str(current_user.id),
    )

    return StatusResponse(status="ok", message=f"Logged out from {revoked_count} device(s)")


@router.get(
    "/me",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get the current authenticated user's profile.",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> MeResponse:
    """Get current user profile."""
    return MeResponse(user=UserResponse.model_validate(current_user))


@router.post(
    "/password-reset/request",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Request a password reset. Always returns success to prevent email enumeration.",
)
async def request_password_reset(
    request_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    _rate_limit_ip: None = Depends(require_rate_limit_reset_ip),
) -> StatusResponse:
    """Request a password reset (stub - no email sending yet)."""
    email_normalized = request_data.email.lower().strip()

    # Rate limit by email
    require_rate_limit_reset_email(email_normalized, request)

    # Always return success to prevent email enumeration
    user = db.query(User).filter(User.email == email_normalized, User.is_active == True).first()

    if user:
        # Generate reset token
        reset_token = generate_password_reset_token()
        token_hash = hash_token(reset_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )

        # Create reset token record
        reset_token_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token_record)
        db.commit()

        # Log security event (never log the token itself)
        log_security_event(
            request,
            event_type="password_reset_requested",
            outcome="allow",
            user_id=str(user.id),
        )

    # Always return generic success message
    return StatusResponse(
        status="ok",
        message="If the email exists, a reset link will be sent.",
    )


@router.post(
    "/password-reset/confirm",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm password reset",
    description="Reset password using a reset token.",
)
async def confirm_password_reset(
    request_data: PasswordResetConfirm,
    db: Session = Depends(get_db),
) -> StatusResponse:
    """Confirm password reset with token."""
    # Hash the provided token
    token_hash = hash_token(request_data.token)

    # Find valid reset token
    reset_token_record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )

    if not reset_token_record or not reset_token_record.is_valid():
        log_security_event(
            request,
            event_type="password_reset_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Invalid or expired reset token",
        )

    # Get user
    user = reset_token_record.user
    if not user or not user.is_active:
        log_security_event(
            request,
            event_type="password_reset_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="User not found or inactive",
        )

    # Update password
    user.password_hash = hash_password(request_data.new_password)
    reset_token_record.used_at = datetime.now(timezone.utc)

    # Revoke all refresh tokens for this user (security best practice)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": datetime.now(timezone.utc)})

    db.commit()

    # Log successful password reset
    log_security_event(
        request,
        event_type="password_reset_confirmed",
        outcome="allow",
        user_id=str(user.id),
    )

    return StatusResponse(status="ok")

