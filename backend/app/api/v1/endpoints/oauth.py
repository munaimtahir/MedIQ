"""OAuth/OIDC endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.app_exceptions import raise_app_error
from app.core.config import settings
from app.core.oauth import (
    create_oauth_link_token,
    generate_oauth_nonce,
    generate_oauth_state,
    get_oauth_link_token,
    get_oauth_state,
    get_oauth_tokens,
    get_provider_adapter,
    store_oauth_state,
    store_oauth_tokens,
)
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.core.security_logging import log_security_event
from app.db.session import get_db
from app.models.auth import RefreshToken
from app.models.oauth import OAuthIdentity, OAuthProvider
from app.models.user import User, UserRole
from app.schemas.auth import TokensResponse, UserResponse
from app.schemas.oauth import (
    OAuthExchangeRequest,
    OAuthExchangeResponse,
    OAuthLinkConfirmRequest,
    OAuthLinkConfirmResponse,
)

router = APIRouter(tags=["OAuth"])


def _build_frontend_redirect(
    path: str = "/api/auth/oauth/callback",
    code: str | None = None,
    error: str | None = None,
    provider: str | None = None,
    link_required: bool = False,
    link_token: str | None = None,
    email: str | None = None,
) -> str:
    """Build a redirect URL to the frontend."""
    from urllib.parse import urlencode

    base_url = settings.FRONTEND_URL.rstrip("/")
    params = {}

    if code:
        params["code"] = code
    if error:
        params["error"] = error
        path = "/login"  # Errors redirect to login page
    if provider:
        params["provider"] = provider
    if link_required:
        params["link_required"] = "true"
        path = "/login"
    if link_token:
        params["link_token"] = link_token
    if email:
        params["email"] = email

    url = f"{base_url}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    return url


def _create_tokens_for_user(user: User, db: Session) -> TokensResponse:
    """Create access and refresh tokens for a user (same as auth.py)."""
    from datetime import timedelta

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


@router.get(
    "/{provider}/start",
    summary="Start OAuth flow",
    description="Initiate OAuth/OIDC login flow with the specified provider.",
)
async def oauth_start(
    provider: str,
    request: Request,
    redirect_uri: str | None = Query(None),
) -> RedirectResponse:
    """Start OAuth flow - redirect to provider."""
    try:
        adapter = get_provider_adapter(provider)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Generate state and nonce
    state = generate_oauth_state()
    nonce = generate_oauth_nonce()

    # Store in Redis
    store_oauth_state(state, nonce, provider.upper())

    # Get authorization URL
    auth_url = adapter.get_authorize_url(state, nonce, redirect_uri)

    # Log OAuth start
    log_security_event(
        request,
        event_type="oauth_start",
        outcome="allow",
        provider=provider,
    )

    return RedirectResponse(url=auth_url)


@router.get(
    "/{provider}/callback",
    summary="OAuth callback",
    description="Handle OAuth callback - validates tokens and redirects to frontend with exchange code.",
)
async def oauth_callback(
    provider: str,
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle OAuth callback - redirects to frontend with an exchange code."""
    # Verify state
    state_data = get_oauth_state(state)
    if not state_data:
        log_security_event(
            request,
            event_type="oauth_callback_failed",
            outcome="deny",
            reason_code="OAUTH_STATE_INVALID",
            provider=provider,
        )
        return RedirectResponse(
            url=_build_frontend_redirect(error="OAUTH_STATE_INVALID", provider=provider)
        )

    stored_provider = state_data["provider"]
    nonce = state_data["nonce"]

    if stored_provider != provider.upper():
        log_security_event(
            request,
            event_type="oauth_callback_failed",
            outcome="deny",
            reason_code="OAUTH_STATE_INVALID",
            provider=provider,
        )
        return RedirectResponse(
            url=_build_frontend_redirect(error="OAUTH_STATE_INVALID", provider=provider)
        )

    try:
        adapter = get_provider_adapter(provider)
    except ValueError:
        log_security_event(
            request,
            event_type="oauth_callback_failed",
            outcome="deny",
            reason_code="VALIDATION_ERROR",
            provider=provider,
        )
        return RedirectResponse(
            url=_build_frontend_redirect(error="VALIDATION_ERROR", provider=provider)
        )

    # Exchange code for tokens
    try:
        token_response = await adapter.exchange_code_for_tokens(code, None)
        id_token = token_response.get("id_token")
        if not id_token:
            raise ValueError("No id_token in response")
    except Exception:
        log_security_event(
            request,
            event_type="oauth_callback_failed",
            outcome="deny",
            reason_code="OAUTH_TOKEN_EXCHANGE_FAILED",
            provider=provider,
        )
        return RedirectResponse(
            url=_build_frontend_redirect(error="OAUTH_TOKEN_EXCHANGE_FAILED", provider=provider)
        )

    # Validate id_token
    try:
        client_id = adapter.client_id if hasattr(adapter, "client_id") else None
        if not client_id:
            raise ValueError("Client ID not configured")
        access_token = token_response.get("access_token")
        id_token_payload = await adapter.validate_id_token(id_token, nonce, client_id, access_token)
    except Exception:
        log_security_event(
            request,
            event_type="oauth_callback_failed",
            outcome="deny",
            reason_code="OAUTH_ID_TOKEN_INVALID",
            provider=provider,
        )
        return RedirectResponse(
            url=_build_frontend_redirect(error="OAUTH_ID_TOKEN_INVALID", provider=provider)
        )

    # Extract identity
    provider_subject = id_token_payload.get("sub")
    email = id_token_payload.get("email")
    email_verified = id_token_payload.get("email_verified", False)
    name = id_token_payload.get("name") or email or "User"

    if not provider_subject:
        log_security_event(
            request,
            event_type="oauth_callback_failed",
            outcome="deny",
            reason_code="OAUTH_ID_TOKEN_INVALID",
            provider=provider,
        )
        return RedirectResponse(
            url=_build_frontend_redirect(error="OAUTH_ID_TOKEN_INVALID", provider=provider)
        )

    provider_enum = OAuthProvider(provider.upper())

    # Check if identity already exists
    oauth_identity = (
        db.query(OAuthIdentity)
        .filter(
            OAuthIdentity.provider == provider_enum.value,
            OAuthIdentity.provider_subject == provider_subject,
        )
        .first()
    )

    if oauth_identity:
        # Existing identity - sign in
        user = oauth_identity.user
        if not user or not user.is_active:
            log_security_event(
                request,
                event_type="oauth_callback_failed",
                outcome="deny",
                reason_code="FORBIDDEN",
                provider=provider,
                user_id=str(user.id) if user else None,
            )
            return RedirectResponse(
                url=_build_frontend_redirect(error="ACCOUNT_INACTIVE", provider=provider)
            )

        # Check MFA
        from app.core.mfa import create_mfa_token
        from app.models.mfa import MFATOTP

        mfa_totp = db.query(MFATOTP).filter(MFATOTP.user_id == user.id, MFATOTP.enabled).first()

        if mfa_totp:
            mfa_token = create_mfa_token(str(user.id))
            log_security_event(
                request,
                event_type="mfa_challenge_issued",
                outcome="allow",
                user_id=str(user.id),
                provider=provider,
            )
            # Store MFA info and redirect
            exchange_code = store_oauth_tokens(
                user_data=UserResponse.model_validate(user).model_dump(mode="json"),
                tokens={},  # No tokens yet - need MFA verification
                mfa_required=True,
                mfa_token=mfa_token,
                mfa_method="totp",
            )
            return RedirectResponse(url=_build_frontend_redirect(code=exchange_code))

        # Update last login
        user.last_login_at = datetime.now(UTC)
        db.commit()

        # Create tokens
        tokens = _create_tokens_for_user(user, db)

        # Log successful OAuth login
        log_security_event(
            request,
            event_type="oauth_callback_success",
            outcome="allow",
            user_id=str(user.id),
            provider=provider,
        )

        # Store tokens and redirect
        exchange_code = store_oauth_tokens(
            user_data=UserResponse.model_validate(user).model_dump(mode="json"),
            tokens=tokens.model_dump(mode="json"),
        )
        return RedirectResponse(url=_build_frontend_redirect(code=exchange_code))

    # New identity - check for email collision
    if email and email_verified:
        existing_user = db.query(User).filter(User.email == email.lower()).first()
        if existing_user:
            # Email collision - create link token and require linking confirmation
            link_token = create_oauth_link_token(provider.upper(), provider_subject, email.lower())

            log_security_event(
                request,
                event_type="oauth_link_required",
                outcome="deny",
                reason_code="OAUTH_LINK_REQUIRED",
                provider=provider,
            )
            return RedirectResponse(
                url=_build_frontend_redirect(
                    link_required=True,
                    link_token=link_token,
                    provider=provider,
                    email=email,
                )
            )

    # Create new user and identity
    user = User(
        name=name,
        email=email.lower() if email else f"{provider_subject}@{provider}.local",
        password_hash=None,  # No password for OAuth-only users
        role=UserRole.STUDENT.value,
        onboarding_completed=False,
        is_active=True,
        email_verified=email_verified if email else False,
    )
    db.add(user)
    db.flush()

    oauth_identity = OAuthIdentity(
        user_id=user.id,
        provider=provider_enum.value,
        provider_subject=provider_subject,
        email_at_link_time=email.lower() if email else None,
    )
    db.add(oauth_identity)
    db.commit()
    db.refresh(user)

    # Check MFA (new user won't have it, but check anyway)
    from app.core.mfa import create_mfa_token
    from app.models.mfa import MFATOTP

    mfa_totp = db.query(MFATOTP).filter(MFATOTP.user_id == user.id, MFATOTP.enabled).first()

    if mfa_totp:
        mfa_token = create_mfa_token(str(user.id))
        exchange_code = store_oauth_tokens(
            user_data=UserResponse.model_validate(user).model_dump(mode="json"),
            tokens={},
            mfa_required=True,
            mfa_token=mfa_token,
            mfa_method="totp",
        )
        return RedirectResponse(url=_build_frontend_redirect(code=exchange_code))

    # Create tokens
    tokens = _create_tokens_for_user(user, db)

    # Log OAuth account creation
    log_security_event(
        request,
        event_type="oauth_callback_success",
        outcome="allow",
        user_id=str(user.id),
        provider=provider,
    )

    # Store tokens and redirect
    exchange_code = store_oauth_tokens(
        user_data=UserResponse.model_validate(user).model_dump(mode="json"),
        tokens=tokens.model_dump(mode="json"),
    )
    return RedirectResponse(url=_build_frontend_redirect(code=exchange_code))


@router.post(
    "/exchange",
    response_model=OAuthExchangeResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange OAuth code for tokens",
    description="Exchange a short-lived OAuth code for user data and tokens. Called by frontend BFF.",
)
async def oauth_exchange(
    request_data: OAuthExchangeRequest,
    request: Request,
) -> OAuthExchangeResponse:
    """Exchange OAuth code for tokens (one-time use)."""
    token_data = get_oauth_tokens(request_data.code)

    if not token_data:
        log_security_event(
            request,
            event_type="oauth_exchange_failed",
            outcome="deny",
            reason_code="OAUTH_CODE_INVALID",
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="OAUTH_CODE_INVALID",
            message="Invalid or expired OAuth code",
        )

    log_security_event(
        request,
        event_type="oauth_exchange_success",
        outcome="allow",
    )

    # Build response
    user_data = token_data.get("user")
    tokens_data = token_data.get("tokens")

    return OAuthExchangeResponse(
        user=UserResponse.model_validate(user_data) if user_data else None,
        tokens=(
            TokensResponse.model_validate(tokens_data)
            if tokens_data and tokens_data.get("access_token")
            else None
        ),
        mfa_required=token_data.get("mfa_required", False),
        mfa_token=token_data.get("mfa_token"),
        method=token_data.get("mfa_method"),
    )


@router.post(
    "/link/confirm",
    response_model=OAuthLinkConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm OAuth account linking",
    description="Link an OAuth identity to an existing local account after password verification.",
)
async def oauth_link_confirm(
    request_data: OAuthLinkConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> OAuthLinkConfirmResponse:
    """Confirm OAuth account linking."""
    # Get and validate link token (one-time use)
    link_data = get_oauth_link_token(request_data.link_token)
    if not link_data:
        log_security_event(
            request,
            event_type="oauth_link_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Invalid or expired link token",
        )

    provider = link_data["provider"]
    provider_subject = link_data["provider_subject"]
    link_email = link_data["email"]

    # Verify email matches
    if request_data.email.lower() != link_email.lower():
        log_security_event(
            request,
            event_type="oauth_link_failed",
            outcome="deny",
            reason_code="VALIDATION_ERROR",
            provider=provider,
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Email does not match link token",
        )

    # Find user by email
    user = db.query(User).filter(User.email == link_email.lower()).first()
    if not user:
        log_security_event(
            request,
            event_type="oauth_link_failed",
            outcome="deny",
            reason_code="NOT_FOUND",
            provider=provider,
        )
        raise_app_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="User not found",
        )

    # Ensure user is active
    if not user.is_active:
        log_security_event(
            request,
            event_type="oauth_link_failed",
            outcome="deny",
            reason_code="FORBIDDEN",
            provider=provider,
            user_id=str(user.id),
        )
        raise_app_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="User account is inactive",
        )

    # Verify password (OAuth-only users may not have password_hash)
    from app.core.security import verify_password

    if not user.password_hash:
        log_security_event(
            request,
            event_type="oauth_link_failed",
            outcome="deny",
            reason_code="VALIDATION_ERROR",
            provider=provider,
            user_id=str(user.id),
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="User account has no password (OAuth-only). Cannot link.",
        )

    if not verify_password(request_data.password, user.password_hash):
        log_security_event(
            request,
            event_type="oauth_link_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
            provider=provider,
            user_id=str(user.id),
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Invalid password",
        )

    # Check if identity already exists
    provider_enum = OAuthProvider(provider.upper())
    existing = (
        db.query(OAuthIdentity)
        .filter(
            OAuthIdentity.provider == provider_enum.value,
            OAuthIdentity.provider_subject == provider_subject,
        )
        .first()
    )

    if existing:
        log_security_event(
            request,
            event_type="oauth_link_failed",
            outcome="deny",
            reason_code="CONFLICT",
            provider=provider,
            user_id=str(user.id),
        )
        raise_app_error(
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            message="OAuth identity already linked",
        )

    # Create identity link
    oauth_identity = OAuthIdentity(
        user_id=user.id,
        provider=provider_enum.value,
        provider_subject=provider_subject,
        email_at_link_time=link_email.lower(),
    )
    db.add(oauth_identity)
    db.commit()

    # Log successful OAuth linking
    log_security_event(
        request,
        event_type="oauth_link_confirmed",
        outcome="allow",
        user_id=str(user.id),
        provider=provider,
    )

    return OAuthLinkConfirmResponse()
