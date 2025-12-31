"""MFA endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.app_exceptions import raise_app_error
from app.core.dependencies import get_current_user
from app.core.mfa import (
    create_mfa_token,
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_backup_codes,
    generate_totp_provisioning_uri,
    generate_totp_secret,
    hash_backup_code,
    verify_backup_code,
    verify_mfa_token,
    verify_totp_code,
)
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.core.security_logging import log_security_event
from app.db.session import get_db
from app.models.mfa import MFABackupCode, MFATOTP
from app.models.user import User
from app.schemas.auth import TokensResponse, UserResponse
from app.schemas.mfa import (
    MFACompleteRequest,
    MFACompleteResponse,
    MFADisableRequest,
    MFADisableResponse,
    MFASetupResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
)

router = APIRouter(tags=["MFA"])


def _create_tokens_for_user(user: User, db: Session) -> TokensResponse:
    """Create access and refresh tokens for a user."""
    from datetime import timedelta

    from app.models.auth import RefreshToken

    # Create access token
    access_token = create_access_token(str(user.id), user.role)

    # Create refresh token
    refresh_token = create_refresh_token()
    token_hash = hash_token(refresh_token)

    # Calculate expiry
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Revoke old refresh tokens for this user
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
    "/totp/setup",
    response_model=MFASetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Setup MFA TOTP",
    description="Generate TOTP secret and provisioning URI for QR code.",
)
async def mfa_totp_setup(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MFASetupResponse:
    """Setup MFA TOTP."""
    # Check if already set up
    existing = db.query(MFATOTP).filter(MFATOTP.user_id == current_user.id).first()
    if existing and existing.enabled:
        log_security_event(
            request,
            event_type="mfa_setup_started",
            outcome="deny",
            reason_code="VALIDATION_ERROR",
            user_id=str(current_user.id),
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="MFA already enabled",
        )

    # Generate secret
    secret = generate_totp_secret()
    encrypted_secret = encrypt_totp_secret(secret)

    # Create or update record
    if existing:
        existing.secret_encrypted = encrypted_secret
        existing.enabled = False
        existing.verified_at = None
    else:
        existing = MFATOTP(
            user_id=current_user.id,
            secret_encrypted=encrypted_secret,
            enabled=False,
        )
        db.add(existing)

    db.commit()

    # Generate provisioning URI
    provisioning_uri = generate_totp_provisioning_uri(secret, current_user.email)

    # Log MFA setup start
    log_security_event(
        request,
        event_type="mfa_setup_started",
        outcome="allow",
        user_id=str(current_user.id),
    )

    return MFASetupResponse(
        provisioning_uri=provisioning_uri,
        secret=secret,  # Return once for QR code
    )


@router.post(
    "/totp/verify",
    response_model=MFAVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify and enable MFA TOTP",
    description="Verify TOTP code and enable MFA. Returns backup codes (shown once).",
)
async def mfa_totp_verify(
    request_data: MFAVerifyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MFAVerifyResponse:
    """Verify TOTP code and enable MFA."""
    # Get TOTP record
    mfa_totp = db.query(MFATOTP).filter(MFATOTP.user_id == current_user.id).first()
    if not mfa_totp:
        log_security_event(
            request,
            event_type="mfa_failed",
            outcome="deny",
            reason_code="NOT_FOUND",
            user_id=str(current_user.id),
        )
        raise_app_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="MFA not set up",
        )

    if mfa_totp.enabled:
        log_security_event(
            request,
            event_type="mfa_failed",
            outcome="deny",
            reason_code="VALIDATION_ERROR",
            user_id=str(current_user.id),
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="MFA already enabled",
        )

    # Decrypt secret
    secret = decrypt_totp_secret(mfa_totp.secret_encrypted)

    # Verify code
    if not verify_totp_code(secret, request_data.code):
        log_security_event(
            request,
            event_type="mfa_failed",
            outcome="deny",
            reason_code="MFA_INVALID",
            user_id=str(current_user.id),
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MFA_INVALID",
            message="Invalid TOTP code",
        )

    # Enable MFA
    mfa_totp.enabled = True
    mfa_totp.verified_at = datetime.now(timezone.utc)

    # Generate backup codes
    backup_codes = generate_backup_codes()
    for code in backup_codes:
        code_hash = hash_backup_code(code)
        backup_code = MFABackupCode(
            user_id=current_user.id,
            code_hash=code_hash,
        )
        db.add(backup_code)

    db.commit()

    # Log MFA enabled
    log_security_event(
        request,
        event_type="mfa_enabled",
        outcome="allow",
        user_id=str(current_user.id),
    )

    return MFAVerifyResponse(
        status="ok",
        backup_codes=backup_codes,  # Return once
    )


@router.post(
    "/complete",
    response_model=MFACompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete MFA step-up",
    description="Complete MFA verification during login and receive access tokens.",
)
async def mfa_complete(
    request_data: MFACompleteRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MFACompleteResponse:
    """Complete MFA step-up."""
    # Verify MFA token
    try:
        mfa_token_payload = verify_mfa_token(request_data.mfa_token)
        user_id = mfa_token_payload["sub"]
    except Exception as e:
        log_security_event(
            request,
            event_type="mfa_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Invalid or expired MFA token",
        )

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        log_security_event(
            request,
            event_type="mfa_failed",
            outcome="deny",
            reason_code="UNAUTHORIZED",
            user_id=str(user_id) if user_id else None,
        )
        raise_app_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="User not found or inactive",
        )

    # Get MFA TOTP
    mfa_totp = db.query(MFATOTP).filter(MFATOTP.user_id == user.id, MFATOTP.enabled == True).first()
    if not mfa_totp:
        log_security_event(
            request,
            event_type="mfa_failed",
            outcome="deny",
            reason_code="VALIDATION_ERROR",
            user_id=str(user.id),
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="MFA not enabled",
        )

    # Verify code or backup code
    verified = False

    if request_data.code:
        # Verify TOTP code
        secret = decrypt_totp_secret(mfa_totp.secret_encrypted)
        verified = verify_totp_code(secret, request_data.code)

    elif request_data.backup_code:
        # Verify backup code
        backup_codes = db.query(MFABackupCode).filter(
            MFABackupCode.user_id == user.id,
            MFABackupCode.used_at.is_(None),
        ).all()

        for backup_code_record in backup_codes:
            if verify_backup_code(request_data.backup_code, backup_code_record.code_hash):
                # Mark as used
                backup_code_record.used_at = datetime.now(timezone.utc)
                verified = True
                break

    if not verified:
        log_security_event(
            request,
            event_type="mfa_failed",
            outcome="deny",
            reason_code="MFA_INVALID",
            user_id=str(user.id),
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MFA_INVALID",
            message="Invalid MFA code",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Create tokens
    tokens = _create_tokens_for_user(user, db)

    # Log successful MFA completion
    log_security_event(
        request,
        event_type="mfa_completed",
        outcome="allow",
        user_id=str(user.id),
    )

    return MFACompleteResponse(
        user=UserResponse.model_validate(user).model_dump(),
        tokens=tokens.model_dump(),
    )


@router.post(
    "/backup-codes/regenerate",
    response_model=MFAVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate backup codes",
    description="Generate new backup codes (invalidates old ones).",
)
async def mfa_backup_codes_regenerate(
    request_data: MFAVerifyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MFAVerifyResponse:
    """Regenerate backup codes (requires password or TOTP confirmation)."""
    # Check MFA is enabled
    mfa_totp = db.query(MFATOTP).filter(MFATOTP.user_id == current_user.id, MFATOTP.enabled == True).first()
    if not mfa_totp:
        log_security_event(
            request,
            event_type="mfa_backup_codes_regenerate",
            outcome="deny",
            reason_code="VALIDATION_ERROR",
            user_id=str(current_user.id),
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="MFA not enabled",
        )

    # Verify password or TOTP code
    from app.core.security import verify_password

    verified = False
    if request_data.code:
        # Verify TOTP code
        secret = decrypt_totp_secret(mfa_totp.secret_encrypted)
        verified = verify_totp_code(secret, request_data.code)
    elif current_user.password_hash:
        # For password verification, we'd need a password field in the request
        # For now, require TOTP code
        log_security_event(
            request,
            event_type="mfa_backup_codes_regenerate",
            outcome="deny",
            reason_code="VALIDATION_ERROR",
            user_id=str(current_user.id),
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="TOTP code required for backup code regeneration",
        )

    if not verified:
        log_security_event(
            request,
            event_type="mfa_backup_codes_regenerate",
            outcome="deny",
            reason_code="MFA_INVALID",
            user_id=str(current_user.id),
        )
        raise_app_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MFA_INVALID",
            message="Invalid TOTP code",
        )

    # Delete old backup codes
    db.query(MFABackupCode).filter(MFABackupCode.user_id == current_user.id).delete()

    # Generate new backup codes
    backup_codes = generate_backup_codes()
    for code in backup_codes:
        code_hash = hash_backup_code(code)
        backup_code = MFABackupCode(
            user_id=current_user.id,
            code_hash=code_hash,
        )
        db.add(backup_code)

    db.commit()

    # Log backup codes regeneration
    log_security_event(
        request,
        event_type="mfa_backup_codes_regenerated",
        outcome="allow",
        user_id=str(current_user.id),
    )

    return MFAVerifyResponse(
        status="ok",
        backup_codes=backup_codes,  # Return once
    )

