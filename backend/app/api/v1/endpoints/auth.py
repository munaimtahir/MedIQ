"""Authentication endpoints."""

from datetime import UTC, datetime, timedelta

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
from app.core.dependencies import get_current_user, require_roles
from app.core.logging import get_logger
from app.core.rate_limit import get_client_ip
from app.core.rate_limit_deps import (
    require_rate_limit_login_email,
    require_rate_limit_login_ip,
    require_rate_limit_refresh,
    require_rate_limit_reset_email,
    require_rate_limit_reset_ip,
    require_rate_limit_signup_ip,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_email_verification_token,
    generate_password_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.security_logging import log_security_event
from app.db.session import get_db
from app.models.auth import EmailVerificationToken, PasswordResetToken, RefreshToken
from app.models.oauth import OAuthIdentity
from app.models.user import User, UserRole

logger = get_logger(__name__)
from app.schemas.auth import (
    EmailVerificationRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MeResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RefreshResponse,
    ResendVerificationRequest,
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
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Revoke old refresh tokens for this user (single session per user)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": datetime.now(UTC)})

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
            message="An account with this email already exists. Please log in instead.",
        )

    # Validate password strength
    if not any(c.isalpha() for c in request_data.password):
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_PASSWORD",
            message="Password must contain at least one letter",
        )
    if not any(c.isdigit() for c in request_data.password):
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_PASSWORD",
            message="Password must contain at least one number",
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
        email_verification_sent_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate verification token
    verification_token = generate_email_verification_token()
    token_hash = hash_token(verification_token)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES)

    # Create verification token record
    verification_token_record = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(verification_token_record)
    db.commit()

    # Send verification email
    try:
        from app.services.email.service import send_email

        verify_link = (
            f"{settings.FRONTEND_BASE_URL}{settings.EMAIL_VERIFY_PATH}?token={verification_token}"
        )
        email_subject = "Verify your email"
        email_body_text = f"""
Welcome! Please verify your email address to complete your account setup.

Click the link below to verify your email:
{verify_link}

This link will expire in {settings.EMAIL_VERIFICATION_EXPIRE_MINUTES // 60} hours.

If you did not create this account, please ignore this email.
"""
        email_body_html = f"""
<html>
<body>
<p>Welcome! Please verify your email address to complete your account setup.</p>
<p><a href="{verify_link}">Click here to verify your email</a></p>
<p>Or copy and paste this link into your browser:</p>
<p>{verify_link}</p>
<p>This link will expire in {settings.EMAIL_VERIFICATION_EXPIRE_MINUTES // 60} hours.</p>
<p>If you did not create this account, please ignore this email.</p>
</body>
</html>
"""
        send_email(
            to=user.email,
            subject=email_subject,
            body_text=email_body_text.strip(),
            body_html=email_body_html.strip(),
        )
    except Exception as e:
        # Log error but don't fail signup
        logger.error(f"Failed to send verification email: {e}", exc_info=True)

    # Log successful signup
    log_security_event(
        request,
        event_type="auth_signup",
        outcome="allow",
        user_id=str(user.id),
    )

    # Do NOT create tokens - user must verify email first
    return SignupResponse(
        user=UserResponse.model_validate(user),
        message="Account created. Please verify your email.",
    )


@router.post(
    "/verify-email",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify email",
    description="Verify email address using a verification token.",
)
async def verify_email(
    request_data: EmailVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> StatusResponse:
    """Verify email address with token."""
    # Hash the provided token
    token_hash = hash_token(request_data.token)

    # Find valid verification token
    verification_token_record = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token_hash == token_hash)
        .first()
    )

    if not verification_token_record or not verification_token_record.is_valid():
        log_security_event(
            request,
            event_type="email_verification_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
        )
        if verification_token_record and verification_token_record.is_expired():
            raise_app_error(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="TOKEN_EXPIRED",
                message="This verification link has expired. Please request a new one.",
            )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_INVALID",
            message="This verification link is invalid. Please request a new one.",
        )

    # Get user
    user = verification_token_record.user
    if not user or not user.is_active:
        log_security_event(
            request,
            event_type="email_verification_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="User not found or inactive",
        )

    # Mark email as verified
    user.email_verified = True
    user.email_verified_at = datetime.now(UTC)
    verification_token_record.used_at = datetime.now(UTC)

    db.commit()

    # Log successful verification
    log_security_event(
        request,
        event_type="email_verification_success",
        outcome="allow",
        user_id=str(user.id),
    )

    return StatusResponse(status="ok", message="Email verified successfully")


@router.post(
    "/resend-verification",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend verification email",
    description="Resend verification email. Always returns success to prevent email enumeration.",
)
async def resend_verification(
    request_data: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> StatusResponse:
    """Resend verification email."""
    email_normalized = request_data.email.lower().strip()

    # Always return success to prevent email enumeration
    user = db.query(User).filter(User.email == email_normalized, User.is_active).first()

    if user:
        # Check if already verified
        if user.email_verified:
            # Still return success (security: don't reveal if email exists)
            return StatusResponse(
                status="ok",
                message="If an account exists and is unverified, you will receive an email shortly.",
            )

        # Generate new verification token
        verification_token = generate_email_verification_token()
        token_hash = hash_token(verification_token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES
        )

        # Revoke old unused tokens for this user
        db.query(EmailVerificationToken).filter(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),
        ).update({"used_at": datetime.now(UTC)})

        # Create new verification token record
        verification_token_record = EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(verification_token_record)
        user.email_verification_sent_at = datetime.now(UTC)
        db.commit()

        # Send verification email
        try:
            from app.services.email.service import send_email

            verify_link = f"{settings.FRONTEND_BASE_URL}{settings.EMAIL_VERIFY_PATH}?token={verification_token}"
            email_subject = "Verify your email"
            email_body_text = f"""
Welcome! Please verify your email address to complete your account setup.

Click the link below to verify your email:
{verify_link}

This link will expire in {settings.EMAIL_VERIFICATION_EXPIRE_MINUTES // 60} hours.

If you did not create this account, please ignore this email.
"""
            email_body_html = f"""
<html>
<body>
<p>Welcome! Please verify your email address to complete your account setup.</p>
<p><a href="{verify_link}">Click here to verify your email</a></p>
<p>Or copy and paste this link into your browser:</p>
<p>{verify_link}</p>
<p>This link will expire in {settings.EMAIL_VERIFICATION_EXPIRE_MINUTES // 60} hours.</p>
<p>If you did not create this account, please ignore this email.</p>
</body>
</html>
"""
            send_email(
                to=user.email,
                subject=email_subject,
                body_text=email_body_text.strip(),
                body_html=email_body_html.strip(),
            )
        except Exception as e:
            # Log error but don't fail the request (security: always return success)
            logger.error(f"Failed to send verification email: {e}", exc_info=True)

        # Log security event
        log_security_event(
            request,
            event_type="email_verification_resent",
            outcome="allow",
            user_id=str(user.id),
        )

    # Always return generic success message
    return StatusResponse(
        status="ok",
        message="If an account exists and is unverified, you will receive an email shortly.",
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in",
    description=(
        "Authenticate with email and password. Returns user data and authentication tokens."
    ),
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
    password_valid = (
        verify_password(request_data.password, password_hash)
        if password_hash != dummy_hash
        else False
    )

    # Check for OAuth-only accounts before generic error
    # This check happens after password verification to maintain timing protection
    if user and not password_valid and not user.password_hash:
        # Check if user has OAuth identities
        oauth_identities = db.query(OAuthIdentity).filter(OAuthIdentity.user_id == user.id).all()
        if oauth_identities:
            # User is OAuth-only - get the provider
            provider = oauth_identities[0].provider
            provider_display = (
                provider.replace("_", " ").title() if "_" in provider else provider.title()
            )

            # Record failure
            record_login_failure(email_normalized, ip)

            # Log security event
            log_security_event(
                request,
                event_type="auth_login_failed",
                outcome="deny",
                reason_code="OAUTH_ONLY_ACCOUNT",
                user_id=str(user.id),
            )

            raise_app_error(
                status_code=status.HTTP_403_FORBIDDEN,
                code="OAUTH_ONLY_ACCOUNT",
                message=f"This account was created with {provider_display}. Please sign in with {provider_display} instead.",
                details={"provider": provider},
            )

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

    # Check if email is verified
    if not user.email_verified:
        log_security_event(
            request,
            event_type="auth_login_failed",
            outcome="deny",
            reason_code="EMAIL_NOT_VERIFIED",
            user_id=str(user.id),
        )
        raise_app_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="EMAIL_NOT_VERIFIED",
            message="Please verify your email before logging in.",
        )

    # Clear failure counters on successful login
    clear_login_failures(email_normalized, ip)

    # Check if MFA is enabled
    from app.core.mfa import create_mfa_token
    from app.models.mfa import MFATOTP

    mfa_totp = db.query(MFATOTP).filter(MFATOTP.user_id == user.id, MFATOTP.enabled).first()

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
    user.last_login_at = datetime.now(UTC)
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
    refresh_token_record.revoked_at = datetime.now(UTC)

    # Create new tokens
    new_access_token = create_access_token(str(user.id), user.role)
    new_refresh_token = create_refresh_token()
    new_token_hash = hash_token(new_refresh_token)
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

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
    request: Request,
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
        refresh_token_record.revoked_at = datetime.now(UTC)
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
        .update({"revoked_at": datetime.now(UTC)})
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
    user = db.query(User).filter(User.email == email_normalized, User.is_active).first()

    if user:
        # Generate reset token
        reset_token = generate_password_reset_token()
        token_hash = hash_token(reset_token)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)

        # Create reset token record
        reset_token_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token_record)
        db.commit()

        # Send password reset email
        try:
            from app.services.email.service import send_email

            reset_link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={reset_token}"
            email_subject = "Password Reset Request"
            email_body_text = f"""
You requested a password reset for your account.

Click the link below to reset your password:
{reset_link}

This link will expire in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes.

If you did not request this reset, please ignore this email.
"""
            email_body_html = f"""
<html>
<body>
<p>You requested a password reset for your account.</p>
<p><a href="{reset_link}">Click here to reset your password</a></p>
<p>Or copy and paste this link into your browser:</p>
<p>{reset_link}</p>
<p>This link will expire in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes.</p>
<p>If you did not request this reset, please ignore this email.</p>
</body>
</html>
"""
            send_email(
                to=user.email,
                subject=email_subject,
                body_text=email_body_text.strip(),
                body_html=email_body_html.strip(),
            )
        except Exception as e:
            # Log error but don't fail the request (security: always return success)
            logger.error(f"Failed to send password reset email: {e}", exc_info=True)

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
        message="If an account exists, you will receive an email shortly.",
    )


@router.post(
    "/reset-password",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password",
    description="Reset password using a reset token.",
)
async def reset_password(
    request_data: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
) -> StatusResponse:
    """Confirm password reset with token."""
    # Hash the provided token
    token_hash = hash_token(request_data.token)

    # Find valid reset token
    reset_token_record = (
        db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
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
    reset_token_record.used_at = datetime.now(UTC)

    # Revoke all refresh tokens for this user (security best practice)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": datetime.now(UTC)})

    db.commit()

    # Log successful password reset
    log_security_event(
        request,
        event_type="password_reset_confirmed",
        outcome="allow",
        user_id=str(user.id),
    )

    return StatusResponse(status="ok")


@router.get(
    "/admin/_rbac_smoke",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="RBAC smoke test",
    description="Test endpoint to verify RBAC dependency. Requires ADMIN role.",
)
async def rbac_smoke_test(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> StatusResponse:
    """RBAC smoke test endpoint - ADMIN only."""
    return StatusResponse(status="ok", message="RBAC check passed - ADMIN access confirmed")
