# Mobile-Safe Authentication

This document describes the mobile-safe authentication and token refresh strategy.

**Status**: Implemented (Task 174)  
**Last Updated**: 2026-01-28

---

## Table of Contents

1. [Overview](#overview)
2. [Token Lifecycle](#token-lifecycle)
3. [Refresh Endpoint](#refresh-endpoint)
4. [Logout Endpoint](#logout-endpoint)
5. [Mobile Retry Behavior](#mobile-retry-behavior)
6. [Refresh Locking](#refresh-locking)
7. [Logout-Everywhere Semantics](#logout-everywhere-semantics)
8. [Error Codes](#error-codes)
9. [Security Constraints](#security-constraints)

---

## Overview

Mobile clients require reliable authentication with:
- **Short-lived access tokens** (5-15 minutes) for security
- **Rotating refresh tokens** for seamless re-authentication
- **Safe concurrency handling** to prevent duplicate tokens
- **Revocation support** for logout and security incidents

### Key Features

- ✅ Token rotation on every refresh
- ✅ Token family tracking (revoke all tokens from same login)
- ✅ Redis locking prevents concurrent refresh
- ✅ Strict rate limiting
- ✅ Standard error codes for mobile retry logic

---

## Token Lifecycle

### 1. Login

**Endpoint**: `POST /api/v1/auth/login`

**Response**:
```json
{
  "user": {...},
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "abc123...",
    "token_type": "bearer"
  }
}
```

**Token Properties**:
- **Access Token**: JWT, expires in 15 minutes (configurable)
- **Refresh Token**: Opaque string, expires in 14 days (configurable)
- **Family ID**: Generated UUID, groups tokens from same login

### 2. Using Access Token

**Header**: `Authorization: Bearer <access_token>`

Access tokens are used for all authenticated API requests. They expire quickly (15 min) for security.

### 3. Refreshing Tokens

When access token expires (401), mobile client should:
1. Call refresh endpoint with refresh token
2. Receive new access + refresh tokens
3. Update stored tokens
4. Retry original request with new access token

### 4. Token Rotation

Every refresh:
- Old refresh token is marked as `rotated_at`
- New refresh token is issued
- Both tokens share same `family_id`
- Old refresh token cannot be reused

### 5. Logout

**Endpoint**: `POST /api/v1/auth/logout`

Revokes entire token family (all tokens from same login session).

---

## Refresh Endpoint

### POST /api/v1/auth/refresh

**Request**:
```json
{
  "refresh_token": "abc123..."
}
```

**Response (200 OK)**:
```json
{
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "xyz789...",
    "token_type": "bearer"
  }
}
```

### Behavior

1. **Validates refresh token** (hash verification)
2. **Acquires Redis lock** (prevents concurrent refresh)
3. **Checks token status**:
   - Not rotated
   - Not revoked
   - Not expired
4. **Rotates tokens**:
   - Marks old token as rotated
   - Issues new access + refresh tokens
   - Links tokens via `replaced_by_token_id`
5. **Releases lock**

### Concurrency Safety

**Redis Lock**: `refresh:lock:{token_hash}`

- TTL: 5 seconds
- Prevents multiple simultaneous refresh calls
- If lock not acquired → returns 429 (retry)

**Result**: Only one valid refresh token per family at a time.

---

## Logout Endpoint

### POST /api/v1/auth/logout

**Request**:
```json
{
  "refresh_token": "abc123..."
}
```

**Response (200 OK)**:
```json
{
  "status": "ok"
}
```

### Behavior

1. **Validates refresh token**
2. **Revokes entire token family**:
   - All tokens with same `family_id` are revoked
   - Session is revoked
   - Session is blacklisted in Redis
3. **Access tokens expire naturally** (not immediately revoked)

### Logout-Everywhere Semantics

When a refresh token is used to logout:
- **All tokens from same login** are revoked
- **All devices using that login session** are logged out
- **Access tokens** remain valid until expiry (short-lived, acceptable)

**Use Case**: User logs out on one device → all devices from that login are logged out.

---

## Mobile Retry Behavior

### On 401 Unauthorized

When mobile client receives 401:

1. **Check error code**:
   - `REFRESH_EXPIRED` → Force re-login
   - `REFRESH_REVOKED` → Force re-login
   - `REFRESH_TOKEN_REUSE` → Force re-login (security incident)
   - `UNAUTHORIZED` → Try refresh

2. **If refreshable**:
   - Call `POST /api/v1/auth/refresh`
   - Update stored tokens
   - Retry original request

3. **If not refreshable**:
   - Clear stored tokens
   - Redirect to login

### Retry Strategy

```python
# Pseudo-code
def api_request_with_retry(url, access_token, refresh_token):
    response = request(url, headers={"Authorization": f"Bearer {access_token}"})
    
    if response.status == 401:
        error_code = response.json()["error_code"]
        
        if error_code in ["REFRESH_EXPIRED", "REFRESH_REVOKED", "REFRESH_TOKEN_REUSE"]:
            # Force re-login
            clear_tokens()
            redirect_to_login()
            return
        
        # Try refresh
        refresh_response = refresh_tokens(refresh_token)
        if refresh_response.success:
            new_access_token = refresh_response.tokens.access_token
            new_refresh_token = refresh_response.tokens.refresh_token
            save_tokens(new_access_token, new_refresh_token)
            # Retry original request
            return request(url, headers={"Authorization": f"Bearer {new_access_token}"})
        else:
            # Refresh failed - force re-login
            clear_tokens()
            redirect_to_login()
            return
    
    return response
```

---

## Refresh Locking

### Redis Lock Mechanism

**Lock Key**: `refresh:lock:{token_hash}`

**Purpose**: Prevent concurrent refresh of same token.

**Scenario**: Mobile client makes two simultaneous refresh calls.

**Without Lock**:
- Both calls succeed
- Two valid refresh tokens issued
- Security risk (token duplication)

**With Lock**:
- First call acquires lock → succeeds
- Second call cannot acquire lock → returns 429
- Only one valid refresh token

### Lock TTL

- **TTL**: 5 seconds
- **Auto-release**: Lock expires automatically
- **Fail-open**: If Redis unavailable, operation proceeds (degraded safety)

### Error Response (Lock Not Acquired)

```json
{
  "error_code": "CONCURRENT_REFRESH",
  "message": "Refresh already in progress. Please retry.",
  "details": null,
  "request_id": "uuid"
}
```

**HTTP Status**: 429 Too Many Requests

**Mobile Action**: Retry after short delay (1-2 seconds).

---

## Logout-Everywhere Semantics

### Token Family

A **token family** groups all refresh tokens from the same login session.

**Properties**:
- Same `family_id` (UUID)
- Created on login
- Shared across all refreshes from that login
- Revoked together on logout

### Example Flow

1. **Login** → `family_id: abc-123`
   - Token 1: `family_id: abc-123`

2. **Refresh** → `family_id: abc-123` (same family)
   - Token 1: rotated
   - Token 2: `family_id: abc-123`

3. **Refresh again** → `family_id: abc-123` (same family)
   - Token 2: rotated
   - Token 3: `family_id: abc-123`

4. **Logout** → Revoke all tokens with `family_id: abc-123`
   - Token 1: revoked
   - Token 2: revoked
   - Token 3: revoked

### Multi-Device Scenario

**Device A** (login session 1):
- Login → `family_id: abc-123`
- Token A1, A2, A3 (all `family_id: abc-123`)

**Device B** (login session 2):
- Login → `family_id: xyz-789`
- Token B1, B2, B3 (all `family_id: xyz-789`)

**Logout on Device A**:
- Revokes `family_id: abc-123` (Device A tokens)
- Device B tokens (`family_id: xyz-789`) remain valid

**Logout-All**:
- Revokes all token families for user
- All devices logged out

---

## Error Codes

### Standard Error Codes

| Code | HTTP Status | Description | Mobile Action |
|------|-------------|-------------|---------------|
| `UNAUTHORIZED` | 401 | Invalid refresh token | Force re-login |
| `REFRESH_EXPIRED` | 401 | Refresh token expired | Force re-login |
| `REFRESH_REVOKED` | 401 | Refresh token revoked | Force re-login |
| `REFRESH_TOKEN_REUSE` | 401 | Token reuse detected (security) | Force re-login |
| `CONCURRENT_REFRESH` | 429 | Refresh already in progress | Retry after delay |

### Error Response Format

```json
{
  "error_code": "REFRESH_EXPIRED",
  "message": "Refresh token has expired",
  "details": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Security Constraints

### Token Storage

- ✅ **Never log tokens** (access or refresh)
- ✅ **Never store refresh tokens unhashed** (always hash before storage)
- ✅ **Use constant-time comparison** for token verification

### Rate Limiting

**Refresh Endpoint**:
- **Per User**: 60 requests per hour (configurable)
- **Per IP**: Rate limited (configurable)
- **Strict enforcement**: Prevents abuse

### Token Rotation

- ✅ **Every refresh rotates** (old token invalidated)
- ✅ **Token family tracking** (reuse detection)
- ✅ **Family revocation** on reuse (security)

### Access Token Expiry

- **TTL**: 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Short-lived** for security
- **Mobile clients** should refresh proactively (before expiry)

---

## Testing Examples

### Refresh Success

```bash
# Login first
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'

# Refresh tokens
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "abc123..."
  }'
```

**Expected**: 200 OK with new tokens

### Refresh Reuse Detection

```bash
# First refresh
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "abc123..."
  }'

# Try to reuse old refresh token (should fail)
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "abc123..."
  }'
```

**Expected**: 401 with `REFRESH_TOKEN_REUSE` error

### Logout

```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "abc123..."
  }'
```

**Expected**: 200 OK, token family revoked

### Concurrent Refresh (Lock Test)

```bash
# Two simultaneous requests (use separate terminals)
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "abc123..."
  }' &

curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "abc123..."
  }'
```

**Expected**: 
- First request: 200 OK
- Second request: 429 with `CONCURRENT_REFRESH` (or 200 if lock released)

---

## Implementation Details

### Token Model

**RefreshToken** fields:
- `id`: UUID (primary key)
- `user_id`: UUID (foreign key)
- `session_id`: UUID (foreign key to AuthSession)
- `family_id`: UUID (token family identifier)
- `token_hash`: String (hashed refresh token)
- `issued_at`: DateTime
- `expires_at`: DateTime
- `rotated_at`: DateTime | null
- `revoked_at`: DateTime | null
- `replaced_by_token_id`: UUID | null (links to new token)

### Redis Lock

**Key Format**: `refresh:lock:{token_hash}`

**TTL**: 5 seconds

**Behavior**:
- `SET NX EX` (set if not exists with expiry)
- Auto-releases after TTL
- Manual release on success

### Rate Limiting

**Per User**: `rl:refresh:user:{user_id}`
- Limit: 60 per hour (configurable)
- Window: 3600 seconds

**Per IP**: `rl:refresh:ip:{ip_address}`
- Limit: Configurable
- Window: Configurable

---

## Mobile Client Best Practices

### Token Storage

- ✅ Store tokens securely (keychain/keystore)
- ✅ Encrypt tokens at rest
- ✅ Never log tokens

### Refresh Strategy

1. **Proactive Refresh**: Refresh before access token expires (e.g., at 80% of TTL)
2. **Retry on 401**: Automatically refresh and retry on 401
3. **Handle Errors**: Check error codes for appropriate action
4. **Concurrent Safety**: Handle 429 (CONCURRENT_REFRESH) with retry

### Example Implementation

```typescript
class TokenManager {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  
  async refreshTokens(): Promise<void> {
    if (!this.refreshToken) {
      throw new Error("No refresh token");
    }
    
    const response = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: this.refreshToken }),
    });
    
    if (response.status === 401) {
      const error = await response.json();
      if (["REFRESH_EXPIRED", "REFRESH_REVOKED", "REFRESH_TOKEN_REUSE"].includes(error.error_code)) {
        // Force re-login
        this.clearTokens();
        throw new Error("Refresh token invalid - re-login required");
      }
    }
    
    if (response.status === 429) {
      // Concurrent refresh - retry after delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      return this.refreshTokens();
    }
    
    if (!response.ok) {
      throw new Error("Refresh failed");
    }
    
    const data = await response.json();
    this.accessToken = data.tokens.access_token;
    this.refreshToken = data.tokens.refresh_token;
    this.saveTokens();
  }
}
```

---

## Next Steps (Task 175)

- [ ] React Native shell implementation
- [ ] Deferred token refresh queue
- [ ] Background refresh scheduling
- [ ] Token expiry monitoring

---

**Last Updated**: 2026-01-28  
**Maintained By**: Backend Team
