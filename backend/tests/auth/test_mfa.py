"""Tests for MFA endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.core.security import create_access_token, create_mfa_token
from app.models.mfa import MFATOTP, MFABackupCode
from tests.helpers.seed import create_test_student


@pytest.mark.asyncio
async def test_mfa_setup_generates_secret(
    async_client: AsyncClient,
    db: Session,
    test_user,
) -> None:
    """Test that MFA setup generates TOTP secret and provisioning URI."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    response = await async_client.post(
        "/v1/auth/mfa/totp/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "provisioning_uri" in data
    assert "secret" in data
    assert data["provisioning_uri"].startswith("otpauth://")
    assert len(data["secret"]) > 0


@pytest.mark.asyncio
async def test_mfa_setup_already_enabled(
    async_client: AsyncClient,
    db: Session,
    test_user,
) -> None:
    """Test that MFA setup fails if already enabled."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Enable MFA first
    from app.core.mfa import encrypt_totp_secret, generate_totp_secret
    
    secret = generate_totp_secret()
    encrypted = encrypt_totp_secret(secret)
    mfa_totp = MFATOTP(
        user_id=test_user.id,
        secret_encrypted=encrypted,
        enabled=True,
    )
    db.add(mfa_totp)
    db.commit()
    
    # Try to setup again
    response = await async_client.post(
        "/v1/auth/mfa/totp/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "VALIDATION_ERROR" in data["error"]["code"] or "MFA already enabled" in data["error"]["message"]


@pytest.mark.asyncio
async def test_mfa_verify_enables_mfa(
    async_client: AsyncClient,
    db: Session,
    test_user,
) -> None:
    """Test that MFA verify enables MFA and returns backup codes."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Setup MFA first
    from app.core.mfa import encrypt_totp_secret, generate_totp_secret
    
    secret = generate_totp_secret()
    encrypted = encrypt_totp_secret(secret)
    mfa_totp = MFATOTP(
        user_id=test_user.id,
        secret_encrypted=encrypted,
        enabled=False,
    )
    db.add(mfa_totp)
    db.commit()
    
    # Mock TOTP verification to return True
    with patch("app.api.v1.endpoints.mfa.verify_totp_code", return_value=True):
        response = await async_client.post(
            "/v1/auth/mfa/totp/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": "123456"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "backup_codes" in data
        assert len(data["backup_codes"]) > 0
        
        # Verify MFA is enabled in DB
        db.refresh(mfa_totp)
        assert mfa_totp.enabled is True


@pytest.mark.asyncio
async def test_mfa_verify_invalid_code(
    async_client: AsyncClient,
    db: Session,
    test_user,
) -> None:
    """Test that MFA verify rejects invalid TOTP code."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Setup MFA
    from app.core.mfa import encrypt_totp_secret, generate_totp_secret
    
    secret = generate_totp_secret()
    encrypted = encrypt_totp_secret(secret)
    mfa_totp = MFATOTP(
        user_id=test_user.id,
        secret_encrypted=encrypted,
        enabled=False,
    )
    db.add(mfa_totp)
    db.commit()
    
    # Mock TOTP verification to return False
    with patch("app.api.v1.endpoints.mfa.verify_totp_code", return_value=False):
        response = await async_client.post(
            "/v1/auth/mfa/totp/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": "000000"},
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "MFA_INVALID" in data["error"]["code"]


@pytest.mark.asyncio
async def test_mfa_complete_with_totp_code(
    async_client: AsyncClient,
    db: Session,
    test_user,
) -> None:
    """Test that MFA complete verifies TOTP code and returns tokens."""
    # Enable MFA
    from app.core.mfa import encrypt_totp_secret, generate_totp_secret
    
    secret = generate_totp_secret()
    encrypted = encrypt_totp_secret(secret)
    mfa_totp = MFATOTP(
        user_id=test_user.id,
        secret_encrypted=encrypted,
        enabled=True,
    )
    db.add(mfa_totp)
    db.commit()
    
    # Create MFA token
    mfa_token = create_mfa_token(str(test_user.id))
    
    # Mock TOTP verification
    with patch("app.api.v1.endpoints.mfa.verify_totp_code", return_value=True):
        response = await async_client.post(
            "/v1/auth/mfa/complete",
            json={
                "mfa_token": mfa_token,
                "code": "123456",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert "access_token" in data["tokens"]


@pytest.mark.asyncio
async def test_mfa_complete_with_backup_code(
    async_client: AsyncClient,
    db: Session,
    test_user,
) -> None:
    """Test that MFA complete accepts backup codes."""
    # Enable MFA
    from app.core.mfa import encrypt_totp_secret, generate_totp_secret, hash_backup_code
    
    secret = generate_totp_secret()
    encrypted = encrypt_totp_secret(secret)
    mfa_totp = MFATOTP(
        user_id=test_user.id,
        secret_encrypted=encrypted,
        enabled=True,
    )
    db.add(mfa_totp)
    
    # Create backup code
    backup_code = "BACKUP-12345"
    backup_code_hash = hash_backup_code(backup_code)
    backup_code_record = MFABackupCode(
        user_id=test_user.id,
        code_hash=backup_code_hash,
    )
    db.add(backup_code_record)
    db.commit()
    
    # Create MFA token
    mfa_token = create_mfa_token(str(test_user.id))
    
    # Mock backup code verification
    with patch("app.api.v1.endpoints.mfa.verify_backup_code", return_value=True):
        response = await async_client.post(
            "/v1/auth/mfa/complete",
            json={
                "mfa_token": mfa_token,
                "backup_code": backup_code,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        
        # Verify backup code was marked as used
        db.refresh(backup_code_record)
        assert backup_code_record.used_at is not None


@pytest.mark.asyncio
async def test_mfa_complete_invalid_token(
    async_client: AsyncClient,
) -> None:
    """Test that MFA complete rejects invalid MFA token."""
    response = await async_client.post(
        "/v1/auth/mfa/complete",
        json={
            "mfa_token": "invalid_token",
            "code": "123456",
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert "UNAUTHORIZED" in data["error"]["code"]


@pytest.mark.asyncio
async def test_mfa_backup_codes_regenerate(
    async_client: AsyncClient,
    db: Session,
    test_user,
) -> None:
    """Test that backup codes can be regenerated."""
    token = create_access_token(user_id=str(test_user.id), role=test_user.role)
    
    # Enable MFA
    from app.core.mfa import encrypt_totp_secret, generate_totp_secret
    
    secret = generate_totp_secret()
    encrypted = encrypt_totp_secret(secret)
    mfa_totp = MFATOTP(
        user_id=test_user.id,
        secret_encrypted=encrypted,
        enabled=True,
    )
    db.add(mfa_totp)
    
    # Create old backup codes
    old_backup = MFABackupCode(
        user_id=test_user.id,
        code_hash="old_hash",
    )
    db.add(old_backup)
    db.commit()
    
    # Mock TOTP verification
    with patch("app.api.v1.endpoints.mfa.verify_totp_code", return_value=True):
        response = await async_client.post(
            "/v1/auth/mfa/backup-codes/regenerate",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": "123456"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "backup_codes" in data
        assert len(data["backup_codes"]) > 0
        
        # Verify old backup codes were deleted
        old_codes = db.query(MFABackupCode).filter(MFABackupCode.user_id == test_user.id).all()
        # Should only have new codes (count should match new backup codes)
        assert len(old_codes) == len(data["backup_codes"])
