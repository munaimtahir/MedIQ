# Secrets Rotation Procedures

This document outlines safe procedures for rotating critical secrets in production without downtime.

## Overview

The platform uses several secrets that require periodic rotation:
- **JWT Signing Keys**: Used to sign and verify access tokens
- **Refresh Token Pepper**: Used to hash refresh tokens before storage
- **MFA Encryption Key**: Used to encrypt TOTP secrets (Fernet)

All rotation procedures follow a **zero-downtime overlap window** pattern:
1. Add new secret alongside existing one
2. System accepts tokens/secrets created with either key during overlap
3. After overlap window, remove old secret

---

## JWT Signing Key Rotation

### Current Implementation

✅ **Already Implemented**: The system supports overlapping JWT keys via:
- `JWT_SIGNING_KEY_CURRENT`: Signs all new tokens
- `JWT_SIGNING_KEY_PREVIOUS`: Validates old tokens during rotation window
- `JWT_SECRET`: Legacy fallback (deprecated, use `JWT_SIGNING_KEY_CURRENT`)

**Behavior:**
- New tokens are **always** signed with `CURRENT` key
- Token verification tries `CURRENT` first, then `PREVIOUS` if `CURRENT` fails
- This allows old tokens to remain valid during rotation overlap

### Rotation Procedure

#### Phase 1: Add New Key (No Downtime)

1. **Generate new signing key:**
   ```bash
   # Generate a strong random key (32+ bytes, base64-encoded)
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Set `JWT_SIGNING_KEY_PREVIOUS` to current key:**
   ```bash
   # In your secrets manager / environment
   JWT_SIGNING_KEY_PREVIOUS=<current_value_of_JWT_SIGNING_KEY_CURRENT>
   ```

3. **Set `JWT_SIGNING_KEY_CURRENT` to new key:**
   ```bash
   JWT_SIGNING_KEY_CURRENT=<newly_generated_key>
   ```

4. **Deploy configuration change:**
   - Update environment variables in your deployment system
   - Restart application services (rolling restart recommended)
   - Verify: New tokens are signed with `CURRENT`, old tokens still validate

5. **Monitor:**
   - Check logs for "Token verified with PREVIOUS key" messages (expected during overlap)
   - Monitor authentication success rates (should remain 100%)
   - Verify no authentication errors spike

#### Phase 2: Overlap Window (Recommended: 2x Access Token TTL)

**Duration:** Minimum `2 * ACCESS_TOKEN_EXPIRE_MINUTES` (default: 30 minutes)

During this window:
- Old tokens (signed with `PREVIOUS`) continue to work
- New tokens (signed with `CURRENT`) are issued
- All tokens validate successfully

**Why 2x TTL?**
- Ensures all active tokens expire and are refreshed with new key
- Provides buffer for clock skew and delayed refreshes

#### Phase 3: Remove Old Key (After Overlap)

1. **Wait for overlap window to complete** (e.g., 30+ minutes after Phase 1)

2. **Verify no tokens are using PREVIOUS key:**
   ```bash
   # Check logs for PREVIOUS key usage (should be zero)
   # Monitor authentication metrics (should be stable)
   ```

3. **Remove `JWT_SIGNING_KEY_PREVIOUS`:**
   ```bash
   # Unset or set to empty
   JWT_SIGNING_KEY_PREVIOUS=
   ```

4. **Deploy and verify:**
   - Old tokens signed with `PREVIOUS` should now fail (expected)
   - New tokens continue to work
   - No authentication errors for active users

### Verification Steps

After each phase, verify:

```bash
# 1. Test new token creation (should use CURRENT)
curl -X POST https://api.example.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "..."}'
# Verify token works

# 2. Test old token (during overlap, should work with PREVIOUS)
# Use a token signed before rotation
curl -X GET https://api.example.com/v1/auth/me \
  -H "Authorization: Bearer <old_token>"
# Should succeed during overlap, fail after PREVIOUS removed

# 3. Check application logs
# Look for "Token verified with PREVIOUS key" (expected during overlap)
```

### Rollback Plan

If issues occur during rotation:

1. **Immediate rollback:**
   ```bash
   # Revert to previous configuration
   JWT_SIGNING_KEY_CURRENT=<previous_value>
   JWT_SIGNING_KEY_PREVIOUS=
   ```

2. **Deploy rollback configuration**

3. **Verify:**
   - All tokens signed with old `CURRENT` key work
   - No authentication failures

4. **Investigate root cause** before retrying rotation

---

## Refresh Token Pepper Rotation

### Current Implementation

✅ **Implemented**: The system supports overlapping pepper values via:
- `AUTH_TOKEN_PEPPER_CURRENT`: Used to hash new refresh tokens
- `AUTH_TOKEN_PEPPER_PREVIOUS`: Used to verify old refresh tokens during rotation
- `AUTH_TOKEN_PEPPER`: Legacy fallback (deprecated, use `AUTH_TOKEN_PEPPER_CURRENT`)
- `TOKEN_PEPPER`: Legacy fallback (deprecated)

**Behavior:**
- New refresh tokens are hashed with `CURRENT` pepper
- Token verification tries `CURRENT` first, then `PREVIOUS` if `CURRENT` fails
- This allows old refresh tokens to remain valid during rotation overlap

### Rotation Procedure

#### Phase 1: Add New Pepper (No Downtime)

1. **Generate new pepper:**
   ```bash
   # Generate a strong random pepper (32+ bytes, base64-encoded)
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Set `AUTH_TOKEN_PEPPER_PREVIOUS` to current pepper:**
   ```bash
   AUTH_TOKEN_PEPPER_PREVIOUS=<current_value_of_AUTH_TOKEN_PEPPER_CURRENT>
   ```

3. **Set `AUTH_TOKEN_PEPPER_CURRENT` to new pepper:**
   ```bash
   AUTH_TOKEN_PEPPER_CURRENT=<newly_generated_pepper>
   ```

4. **Deploy configuration change:**
   - Update environment variables
   - Restart application services
   - Verify: New refresh tokens are hashed with `CURRENT`, old tokens still validate

5. **Monitor:**
   - Check authentication success rates
   - Monitor refresh token validation errors (should remain low)

#### Phase 2: Overlap Window (Recommended: 2x Refresh Token TTL)

**Duration:** Minimum `2 * REFRESH_TOKEN_EXPIRE_DAYS` (default: 28 days)

During this window:
- Old refresh tokens (hashed with `PREVIOUS`) continue to work
- New refresh tokens (hashed with `CURRENT`) are issued
- All refresh tokens validate successfully

**Why 2x TTL?**
- Refresh tokens have long TTL (14 days default)
- Ensures all active refresh tokens are rotated or expire
- Provides buffer for infrequent users

#### Phase 3: Remove Old Pepper (After Overlap)

1. **Wait for overlap window to complete** (e.g., 28+ days after Phase 1)

2. **Verify no refresh tokens are using PREVIOUS pepper:**
   - Check logs for PREVIOUS pepper usage (should be zero)
   - Monitor refresh token validation metrics

3. **Remove `AUTH_TOKEN_PEPPER_PREVIOUS`:**
   ```bash
   AUTH_TOKEN_PEPPER_PREVIOUS=
   ```

4. **Deploy and verify:**
   - Old refresh tokens hashed with `PREVIOUS` should now fail (expected)
   - New refresh tokens continue to work
   - Users with expired refresh tokens will need to re-login (expected)

### Verification Steps

After each phase:

```bash
# 1. Test new refresh token creation
# Login to get new refresh token (hashed with CURRENT)
curl -X POST https://api.example.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "..."}'
# Save refresh_token from response

# 2. Test refresh with new token
curl -X POST https://api.example.com/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<new_refresh_token>"}'
# Should succeed

# 3. Test old refresh token (during overlap, should work with PREVIOUS)
# Use a refresh token issued before rotation
curl -X POST https://api.example.com/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<old_refresh_token>"}'
# Should succeed during overlap, fail after PREVIOUS removed
```

### Rollback Plan

If issues occur:

1. **Immediate rollback:**
   ```bash
   AUTH_TOKEN_PEPPER_CURRENT=<previous_value>
   AUTH_TOKEN_PEPPER_PREVIOUS=
   ```

2. **Deploy rollback configuration**

3. **Verify:**
   - All refresh tokens hashed with old `CURRENT` pepper work
   - No authentication failures

---

## MFA Encryption Key Rotation

### Current Implementation

⚠️ **Not Yet Implemented**: MFA encryption key rotation requires re-encrypting all TOTP secrets.

**Current State:**
- `MFA_ENCRYPTION_KEY`: Fernet key used to encrypt TOTP secrets
- Single key (no overlap support yet)

### Rotation Procedure (Future)

**Note:** This requires a migration to re-encrypt all TOTP secrets. Implementation pending.

1. **Generate new Fernet key:**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Re-encrypt all TOTP secrets:**
   - Background job to decrypt with old key, encrypt with new key
   - Store both keys during migration
   - Verify all secrets re-encrypted successfully

3. **Switch to new key:**
   - Update `MFA_ENCRYPTION_KEY`
   - Remove old key after verification

**Recommendation:** Implement overlapping key support similar to JWT/pepper rotation.

---

## Recommended Cadence

### JWT Signing Key
- **Regular rotation:** Every 90 days
- **After security incident:** Immediately
- **After key exposure:** Immediately (emergency rotation)

### Refresh Token Pepper
- **Regular rotation:** Every 180 days
- **After security incident:** Immediately
- **After pepper exposure:** Immediately (emergency rotation)

### MFA Encryption Key
- **Regular rotation:** Every 365 days (or when re-encryption migration is implemented)
- **After security incident:** Immediately (requires migration)

---

## Emergency Rotation

If a secret is **compromised or exposed**, follow these steps:

### Immediate Actions

1. **Generate new secret immediately**
2. **Set both CURRENT and PREVIOUS:**
   - `CURRENT` = new secret
   - `PREVIOUS` = old secret (to allow overlap)
3. **Deploy immediately** (no waiting for maintenance window)
4. **Monitor closely** for authentication failures
5. **After minimum overlap window**, remove `PREVIOUS`

### Post-Incident

1. **Audit logs** for suspicious authentication activity
2. **Revoke all active sessions** if compromise confirmed:
   ```bash
   # Via admin API or direct DB query
   UPDATE auth_sessions SET revoked_at = NOW() WHERE revoked_at IS NULL;
   ```
3. **Force password reset** for affected users
4. **Document incident** and update rotation cadence if needed

---

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Authentication success rate** (should remain ~100% during rotation)
2. **Token validation errors** (should spike only after PREVIOUS removed, and only for old tokens)
3. **PREVIOUS key/pepper usage** (should drop to zero after overlap window)
4. **Active session count** (should remain stable)

### Alert Thresholds

- **Authentication failure rate > 1%**: Investigate immediately
- **PREVIOUS key usage > 0 after overlap window**: Old tokens still active (extend overlap)
- **Token validation errors spike**: Potential rotation issue

### Log Messages

Look for these log messages during rotation:

```
# JWT rotation
"Token verified with PREVIOUS key (rotation overlap window)"

# Pepper rotation (if implemented)
"Refresh token verified with PREVIOUS pepper (rotation overlap window)"
```

---

## Testing Rotation Procedures

### Pre-Production Testing

1. **Test in staging environment:**
   - Perform full rotation procedure
   - Verify no authentication failures
   - Test rollback procedure

2. **Load testing:**
   - Simulate high authentication load during rotation
   - Verify system handles overlap window gracefully

3. **Failure scenarios:**
   - Test with invalid keys
   - Test rollback procedure
   - Test emergency rotation

### Production Validation

After each rotation phase:

1. **Smoke test authentication:**
   - Login with test account
   - Refresh tokens
   - Verify access to protected endpoints

2. **Monitor metrics:**
   - Authentication success rate
   - Token validation errors
   - Active session count

3. **Check logs:**
   - No unexpected errors
   - Expected rotation messages present

---

## Best Practices

1. **Always test in staging first**
2. **Use rolling restarts** to minimize downtime
3. **Monitor closely** during overlap window
4. **Document rotation dates** in runbook
5. **Automate rotation** where possible (future enhancement)
6. **Keep old secrets secure** until overlap window completes
7. **Never reuse old secrets** after rotation completes
8. **Rotate secrets proactively**, not reactively

---

## Troubleshooting

### Issue: Authentication failures during rotation

**Symptoms:** Users cannot log in or refresh tokens

**Possible causes:**
- Invalid key format
- Key not deployed correctly
- Clock skew between services

**Resolution:**
1. Check environment variables are set correctly
2. Verify key format (base64-encoded, correct length)
3. Check application logs for specific errors
4. Rollback if necessary

### Issue: Old tokens still failing after overlap window

**Symptoms:** Users with old tokens cannot authenticate

**Expected behavior:** After `PREVIOUS` is removed, old tokens should fail. Users should re-login.

**If unexpected:**
1. Verify overlap window was long enough (2x TTL)
2. Check if `PREVIOUS` was removed too early
3. Extend overlap window if needed

### Issue: New tokens failing after rotation

**Symptoms:** New tokens cannot be verified

**Possible causes:**
- `CURRENT` key not set correctly
- Key format incorrect
- Application not restarted after config change

**Resolution:**
1. Verify `CURRENT` key is set and correct
2. Check application restarted with new config
3. Rollback to previous `CURRENT` if needed

---

## References

- [JWT Key Rotation Implementation](../backend/app/core/security.py)
- [Refresh Token Pepper Implementation](../backend/app/core/security.py)
- [Security Documentation](./security.md)
- [Runbook](./runbook.md)
