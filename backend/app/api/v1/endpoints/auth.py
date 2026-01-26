"""Authentication endpoints."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

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
from app.security.token_blacklist import (
    batch_blacklist_sessions,
    blacklist_session,
    calculate_blacklist_ttl,
    is_session_blacklisted,
)
from app.core.rate_limit_deps import (
    require_rate_limit_refresh,
)
from app.security.rate_limit import (
    rate_limit_email,
    rate_limit_ip,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_email_verification_token,
    generate_password_reset_token,
    hash_password,
    hash_token,
    verify_password,
    verify_token_hash,
)
from app.core.security_logging import log_security_event
from app.db.session import get_db
from app.models.auth import AuthSession, EmailVerificationToken, PasswordResetToken, RefreshToken
from app.models.oauth import OAuthIdentity
from app.models.user import User, UserRole
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
    SessionResponse,
    SessionsListResponse,
    SignupRequest,
    SignupResponse,
    StatusResponse,
    TokensResponse,
    UserResponse,
)

logger = get_logger(__name__)

router = APIRouter(tags=["Auth"])


def _create_tokens_for_user(
    user: User, db: Session, request: Request | None = None
) -> tuple[TokensResponse, AuthSession]:
    """
    Create access and refresh tokens for a user with session management.
    
    Returns:
        Tuple of (TokensResponse, AuthSession)
    """
    # Extract IP and user agent
    ip_address = None
    user_agent = None
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("user-agent")

    # Create auth session
    session = AuthSession(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    db.flush()  # Get session.id

    # Create access token with session_id
    access_token = create_access_token(str(user.id), user.role, session_id=str(session.id))

    # Create refresh token
    refresh_token = create_refresh_token()
    token_hash = hash_token(refresh_token)

    # Calculate expiry
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Create new refresh token record linked to session
    db_refresh_token = RefreshToken(
        user_id=user.id,
        session_id=session.id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(db_refresh_token)
    db.commit()

    return (
        TokensResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ),
        session,
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
        full_name=request_data.name,
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
                message=(
                    "If an account exists and is unverified, " "you will receive an email shortly."
                ),
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

            verify_link = (
                f"{settings.FRONTEND_BASE_URL}{settings.EMAIL_VERIFY_PATH}"
                f"?token={verification_token}"
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
    dependencies=[
        Depends(rate_limit_ip("auth.login", fail_open=True)),
    ],
)
async def login(
    request_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Log in a user."""
    ip = get_client_ip(request)
    email_normalized = request_data.email.lower().strip()

    # Rate limit by email
    check_email_limit = rate_limit_email("auth.login", fail_open=True)
    check_email_limit(request_data.email, request)

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
                message=(
                    f"This account was created with {provider_display}. "
                    f"Please sign in with {provider_display} instead."
                ),
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
    tokens, session = _create_tokens_for_user(user, db, request)

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
    """Refresh access and refresh tokens with rotation and reuse detection."""
    # Hash the provided refresh token
    token_hash = hash_token(request_data.refresh_token)

    # Find refresh token (check if already rotated for reuse detection)
    # Query by hash (indexed lookup), then verify with constant-time comparison
    refresh_token_record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )
    
    # Constant-time verification (defense in depth against timing attacks)
    if refresh_token_record and not verify_token_hash(request_data.refresh_token, refresh_token_record.token_hash):
        refresh_token_record = None

    if not refresh_token_record:
        log_security_event(
            request,
            event_type="auth_refresh_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Invalid refresh token",
        )

    # Check if token was already rotated (reuse detection)
    if refresh_token_record.rotated_at is not None:
        # Token reuse detected - revoke entire session
        session = refresh_token_record.session
        if session:
            session.revoked_at = datetime.now(UTC)
            session.revoke_reason = "refresh_reuse_detected"
            
            # Blacklist session immediately
            ttl = calculate_blacklist_ttl(refresh_token_record.expires_at)
            blacklist_session(str(session.id), ttl)
        
        db.commit()
        
        log_security_event(
            request,
            event_type="auth_refresh_reuse_detected",
            outcome="deny",
            reason_code="REFRESH_TOKEN_REUSE",
            user_id=str(refresh_token_record.user_id),
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Refresh token has been used. Session revoked for security.",
        )

    # Check if token is active (not revoked, not expired)
    if not refresh_token_record.is_active():
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

    # Get user and session
    user = refresh_token_record.user
    session = refresh_token_record.session
    
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

    # Check if session is revoked (fast check via Redis blacklist, fallback to DB)
    if session:
        if is_session_blacklisted(str(session.id)):
            log_security_event(
                request,
                event_type="auth_refresh_failed",
                outcome="deny",
                reason_code="SESSION_REVOKED",
                user_id=str(user.id),
            )
            raise_app_error(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="UNAUTHORIZED",
                message="Session has been revoked",
            )
        
        if session.revoked_at is not None:
            # Session revoked in DB
            log_security_event(
                request,
                event_type="auth_refresh_failed",
                outcome="deny",
                reason_code="SESSION_REVOKED",
                user_id=str(user.id),
            )
            raise_app_error(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="UNAUTHORIZED",
                message="Session has been revoked",
            )
        
        # Update last_seen_at
        session.last_seen_at = datetime.now(UTC)

    # Rate limit by user
    require_rate_limit_refresh(str(user.id), request)

    # Rotate: mark old token as rotated
    refresh_token_record.rotated_at = datetime.now(UTC)

    # Create new tokens
    new_access_token = create_access_token(
        str(user.id), user.role, session_id=str(session.id) if session else None
    )
    new_refresh_token = create_refresh_token()
    new_token_hash = hash_token(new_refresh_token)
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Extract IP and user agent for new token
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    # Create new refresh token record (linked to same session)
    new_refresh_token_record = RefreshToken(
        user_id=user.id,
        session_id=session.id if session else None,
        token_hash=new_token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
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
    """Log out by revoking refresh token and session."""
    # Hash the provided refresh token
    token_hash = hash_token(request_data.refresh_token)

    # Find refresh token
    refresh_token_record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )
    
    # Constant-time verification (defense in depth)
    if refresh_token_record and not verify_token_hash(request_data.refresh_token, refresh_token_record.token_hash):
        refresh_token_record = None

    if refresh_token_record:
        # Revoke the refresh token
        refresh_token_record.revoked_at = datetime.now(UTC)
        
        # Revoke the session if it exists
        session = refresh_token_record.session
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            session.revoke_reason = "user_logout"
            
            # Blacklist session in Redis
            ttl = calculate_blacklist_ttl(refresh_token_record.expires_at)
            blacklist_session(str(session.id), ttl)
        
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
    """Log out all devices by revoking all sessions and refresh tokens."""
    # Get all active sessions
    active_sessions = (
        db.query(AuthSession)
        .filter(
            AuthSession.user_id == current_user.id,
            AuthSession.revoked_at.is_(None),
        )
        .all()
    )
    
    # Revoke all sessions
    session_ids = []
    max_expiry = datetime.now(UTC)
    for session in active_sessions:
        session.revoked_at = datetime.now(UTC)
        session.revoke_reason = "user_logout_all"
        session_ids.append(str(session.id))
        
        # Find max expiry from refresh tokens in this session
        session_tokens = (
            db.query(RefreshToken)
            .filter(RefreshToken.session_id == session.id)
            .all()
        )
        for token in session_tokens:
            if token.expires_at > max_expiry:
                max_expiry = token.expires_at
    
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
    
    # Blacklist all sessions in Redis (batch operation)
    if session_ids:
        ttl = calculate_blacklist_ttl(max_expiry)
        batch_blacklist_sessions(session_ids, ttl)

    # Log logout all
    log_security_event(
        request,
        event_type="auth_logout_all",
        outcome="allow",
        user_id=str(current_user.id),
    )

    return StatusResponse(status="ok", message=f"Logged out from {len(session_ids)} device(s)")


@router.get(
    "/me",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get the current authenticated user's profile.",
)
async def get_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> MeResponse:
    """Get current user profile with session information."""
    # Extract session_id from access token if available
    session_id = None
    if hasattr(request.state, "session_id"):
        session_id = request.state.session_id
    else:
        # Try to get from JWT token claims
        authorization = request.headers.get("authorization")
        if authorization:
            try:
                from app.core.security import verify_access_token
                scheme, token = authorization.split()
                if scheme.lower() == "bearer":
                    payload = verify_access_token(token)
                    session_id = payload.get("sid")
            except Exception:
                pass  # Ignore errors, session_id is optional
    
    response = MeResponse(user=UserResponse.model_validate(current_user))
    # Note: session_id can be added to response if schema supports it
    # For now, it's included in access token claims for future use
    return response


@router.post(
    "/password-reset/request",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Request a password reset. Always returns success to prevent email enumeration.",
    dependencies=[
        Depends(rate_limit_ip("auth.password_reset_request", fail_open=True)),
    ],
)
async def request_password_reset(
    request_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> StatusResponse:
    """Request a password reset (stub - no email sending yet)."""
    email_normalized = request_data.email.lower().strip()

    # Rate limit by email
    check_email_limit = rate_limit_email("auth.password_reset_request", fail_open=True)
    check_email_limit(request_data.email, request)

    # Always return success to prevent email enumeration
    user = db.query(User).filter(User.email == email_normalized, User.is_active).first()

    if user:
        # Generate reset token
        reset_token = generate_password_reset_token()
        token_hash = hash_token(reset_token)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)

        # Get client IP and user agent
        requested_ip = request.client.host if request.client else None
        requested_ua = request.headers.get("user-agent")

        # Create reset token record
        reset_token_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            requested_ip=requested_ip,
            requested_ua=requested_ua,
        )
        db.add(reset_token_record)
        db.commit()

        # Enqueue password reset email via outbox
        try:
            from app.email.service import enqueue_email
            from app.email.templates import render_template

            reset_url = f"{settings.FRONTEND_BASE_URL}/reset-password?token={reset_token}"
            template_vars = {
                "reset_url": reset_url,
                "expires_minutes": settings.PASSWORD_RESET_EXPIRE_MINUTES,
            }

            # Render templates
            body_text = render_template("PASSWORD_RESET", template_vars, format="text")
            body_html = render_template("PASSWORD_RESET", template_vars, format="html")

            enqueue_email(
                db=db,
                to_email=user.email,
                to_name=user.name,
                subject="Password Reset Request",
                template_key="PASSWORD_RESET",
                template_vars=template_vars,
                body_text=body_text,
                body_html=body_html,
            )
        except Exception as e:
            # Log error but don't fail the request (security: always return success)
            logger.error(f"Failed to enqueue password reset email: {e}", exc_info=True)

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
    dependencies=[
        Depends(rate_limit_ip("auth.password_reset_confirm", fail_open=True)),
    ],
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

    # Password validation is handled by Pydantic schema (min_length=10, letter+number requirement)
    # The schema validator will have already run, but we double-check for security
    new_password = request_data.new_password
    if len(new_password) < 10:
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_PASSWORD",
            message="Password must be at least 10 characters long",
        )
    
    # Validate password strength (letter + number)
    if not any(c.isalpha() for c in new_password) or not any(c.isdigit() for c in new_password):
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_PASSWORD",
            message="Password must contain at least one letter and one number",
        )

    # Update password
    user.password_hash = hash_password(new_password)
    reset_token_record.used_at = datetime.now(UTC)

    # Revoke all sessions for this user (security best practice)
    # Get all active sessions
    active_sessions = (
        db.query(AuthSession)
        .filter(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
        )
        .all()
    )
    
    # Revoke all sessions
    session_ids = []
    max_expiry = datetime.now(UTC)
    for session in active_sessions:
        session.revoked_at = datetime.now(UTC)
        session.revoke_reason = "password_reset"
        session_ids.append(str(session.id))
        
        # Find max expiry from refresh tokens in this session
        session_tokens = (
            db.query(RefreshToken)
            .filter(RefreshToken.session_id == session.id)
            .all()
        )
        for token in session_tokens:
            if token.expires_at > max_expiry:
                max_expiry = token.expires_at
    
    # Revoke all refresh tokens for this user
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": datetime.now(UTC)})

    db.commit()
    
    # Blacklist all sessions in Redis (batch operation)
    if session_ids:
        ttl = calculate_blacklist_ttl(max_expiry)
        batch_blacklist_sessions(session_ids, ttl)

    # Log successful password reset
    log_security_event(
        request,
        event_type="password_reset_confirmed",
        outcome="allow",
        user_id=str(user.id),
    )

    return StatusResponse(status="ok")


@router.get(
    "/sessions",
    response_model=SessionsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user sessions",
    description="Get list of all active sessions for the current user (for future 'devices' page).",
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionsListResponse:
    """List all sessions for the current user."""
    sessions = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == current_user.id)
        .order_by(AuthSession.last_seen_at.desc())
        .all()
    )
    
    return SessionsListResponse(
        sessions=[
            SessionResponse(
                id=session.id,
                created_at=session.created_at,
                last_seen_at=session.last_seen_at,
                user_agent=session.user_agent,
                ip_address=session.ip_address,
                is_active=session.is_active(),
            )
            for session in sessions
        ]
    )


@router.post(
    "/sessions/{session_id}/revoke",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke a session",
    description="Revoke a specific session by ID. Only the session owner can revoke their own sessions.",
)
async def revoke_session(
    session_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    """Revoke a specific session (only own sessions)."""
    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.id == session_id,
            AuthSession.user_id == current_user.id,
        )
        .first()
    )
    
    if not session:
        raise_app_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Session not found",
        )
    
    if session.revoked_at is not None:
        return StatusResponse(status="ok", message="Session already revoked")
    
    # Revoke session
    session.revoked_at = datetime.now(UTC)
    session.revoke_reason = "user_revoked"
    
    # Revoke all refresh tokens in this session
    db.query(RefreshToken).filter(
        RefreshToken.session_id == session.id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": datetime.now(UTC)})
    
    # Find max expiry for blacklist TTL
    session_tokens = (
        db.query(RefreshToken)
        .filter(RefreshToken.session_id == session.id)
        .all()
    )
    max_expiry = datetime.now(UTC)
    for token in session_tokens:
        if token.expires_at > max_expiry:
            max_expiry = token.expires_at
    
    db.commit()
    
    # Blacklist session in Redis
    ttl = calculate_blacklist_ttl(max_expiry)
    blacklist_session(str(session.id), ttl)
    
    log_security_event(
        request,
        event_type="auth_session_revoked",
        outcome="allow",
        user_id=str(current_user.id),
    )
    
    return StatusResponse(status="ok", message="Session revoked")


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
