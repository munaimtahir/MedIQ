# Security Documentation

## Overview

This document outlines the security architecture, policies, and practices for the Medical Exam Platform.

## Current State (Phase 1: Skeleton)

### Authentication

**Status:** Temporary / Development Only

**Current Implementation:**
- Header-based authentication: `X-User-Id`
- No password verification
- No token validation
- Demo credentials hardcoded in frontend

**Security Level:** ⚠️ **NOT PRODUCTION READY**

**Risks:**
- Anyone can impersonate any user by setting header
- No session management
- No CSRF protection
- Credentials visible in client code

---

## Planned Security Architecture

### Authentication & Authorization

#### OAuth2 / OpenID Connect

**Implementation Plan:**
- Support multiple providers:
  - Google OAuth
  - Microsoft Azure AD
  - Custom OAuth provider
- JWT token-based authentication
- Refresh token mechanism
- Token expiration and rotation

**Flow:**
```
1. User clicks "Login with Google"
2. Redirect to OAuth provider
3. User authorizes
4. Provider redirects back with authorization code
5. Backend exchanges code for tokens
6. Backend issues JWT access token + refresh token
7. Frontend stores tokens securely
8. Subsequent requests include JWT in Authorization header
```

#### JWT Token Structure

```json
{
  "sub": "user-id",
  "role": "student",
  "email": "user@example.com",
  "iat": 1234567890,
  "exp": 1234571490,
  "jti": "token-id"
}
```

**Token Storage:**
- Access token: In-memory (not localStorage)
- Refresh token: HttpOnly cookie (more secure)
- Consider using secure storage APIs

---

### Authorization

#### Role-Based Access Control (RBAC)

**Roles:**
- `student`: Can access student routes, practice sessions
- `admin`: Can access admin routes, question management
- `faculty`: (Future) Can review questions
- `super_admin`: (Future) Full system access

**Implementation:**
```python
# Backend middleware
def require_role(required_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = get_current_user()
            if user.role != required_role:
                raise HTTPException(403, "Insufficient permissions")
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

**Frontend Route Protection:**
```typescript
// Middleware or layout component
if (user.role !== 'admin') {
  router.push('/unauthorized');
}
```

---

### Data Protection

#### Encryption

**At Rest:**
- Database encryption (PostgreSQL TDE)
- Encrypted backups
- Secure key management (AWS KMS, Azure Key Vault)

**In Transit:**
- HTTPS/TLS 1.3 mandatory
- Certificate pinning (mobile apps)
- HSTS headers

**Sensitive Data:**
- Passwords: bcrypt/Argon2 hashing
- PII: Encryption at application level
- API keys: Environment variables, secrets management

#### Password Security

**Requirements:**
- Minimum 8 characters
- Require uppercase, lowercase, number
- Optional: special character requirement
- Password strength meter
- Prevent common passwords

**Storage:**
```python
# Hashing with bcrypt
import bcrypt

password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
# Store: password_hash (never plaintext)

# Verification
is_valid = bcrypt.checkpw(password.encode(), stored_hash)
```

**Password Reset:**
- Secure token generation
- Time-limited tokens (15 minutes)
- Single-use tokens
- Email verification required

---

### API Security

#### Rate Limiting

**Implementation:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/sessions")
@limiter.limit("10/minute")  # 10 requests per minute per IP
def create_session():
    ...
```

**Limits:**
- Login attempts: 5 per 15 minutes
- API calls: 100 per minute (authenticated)
- Question creation: 20 per hour (admin)
- Session creation: 10 per hour (student)

#### Input Validation

**Current:** Pydantic schemas validate request data

**Enhancements:**
- Sanitize user inputs
- SQL injection prevention (SQLAlchemy ORM handles this)
- XSS prevention (React escapes by default)
- CSRF tokens for state-changing operations

**Example:**
```python
from pydantic import BaseModel, validator

class QuestionCreate(BaseModel):
    question_text: str
    
    @validator('question_text')
    def sanitize_text(cls, v):
        # Remove potentially dangerous characters
        return v.strip()[:5000]  # Length limit
```

#### CORS Configuration

**Implementation:** Deny-by-default with environment-driven allowlists.

**Settings:**
- `CORS_ALLOW_ORIGINS_PUBLIC`: Comma-separated exact origins for public endpoints
- `CORS_ALLOW_ORIGINS_APP`: Comma-separated exact origins for app endpoints
- `CORS_ALLOW_METHODS`: Default `"GET,POST,PUT,PATCH,DELETE,OPTIONS"`
- `CORS_ALLOW_HEADERS`: Default `"Authorization,Content-Type,X-Request-ID"`
- `CORS_EXPOSE_HEADERS`: Default `"X-Request-ID,X-Response-Time-ms,X-DB-Queries,X-DB-Time-ms"`
- `CORS_ALLOW_CREDENTIALS`: Default `false` (set `true` if using cookie auth)

**Behavior:**
- Only exact origins allowed (no wildcards)
- Preflight requests handled correctly and fast
- Same CORS policy applies to `/v1/*` endpoints
- Health endpoints can be open but still secure

**Example Configuration:**
```python
# In .env
CORS_ALLOW_ORIGINS_APP=https://app.example.com,https://www.example.com
CORS_ALLOW_METHODS=GET,POST,PUT,PATCH,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Authorization,Content-Type,X-Request-ID
CORS_ALLOW_CREDENTIALS=true
```

**Production Best Practices:**
- Whitelist specific domains only
- No wildcard origins (`*`)
- Credentials only for trusted origins
- Preflight request caching handled by FastAPI CORSMiddleware

---

### Session Management

#### Token Family Isolation (Per-Device Sessions)

**Current:** ✅ **Implemented**

Each device/session gets its own refresh token "family" (isolated from other devices). Revoking one session doesn't log the user out everywhere.

**Architecture:**
- **`auth_sessions`**: Tracks each login session (device)
  - `id` (UUID), `user_id`, `created_at`, `last_seen_at`
  - `user_agent`, `ip_address` (optional metadata)
  - `revoked_at`, `revoke_reason` (for revocation tracking)
- **`refresh_tokens`**: Refresh tokens linked to sessions
  - `id` (UUID), `session_id` (FK to `auth_sessions`)
  - `token_hash` (SHA256 hash, never raw token)
  - `issued_at`, `expires_at`
  - `rotated_at`, `replaced_by_token_id` (for token rotation)
  - `revoked_at` (for revocation)

**Token Flow:**

1. **Login:**
   - Create `auth_session` record
   - Issue refresh token tied to `session_id`
   - Store only `token_hash` (never raw token in DB)

2. **Refresh:**
   - Verify refresh token hash (constant-time comparison)
   - Check token is active (not revoked, not rotated, not expired)
   - **Rotate:** Mark old token as `rotated_at`, issue new token in same session
   - Update `last_seen_at` on session

3. **Logout:**
   - Revoke current session only (not all sessions)
   - Revoke all refresh tokens in that session
   - Blacklist session in Redis (for fast access token invalidation)

4. **Session Management:**
   - `GET /v1/auth/sessions`: List all sessions for current user
   - `POST /v1/auth/sessions/{id}/revoke`: Revoke a specific session (own sessions only)
   - `POST /v1/auth/logout-all`: Revoke all sessions (admin can also revoke all for a user)

**Security:**
- **Token hashing:** Only `token_hash` stored (SHA256 with pepper). Raw tokens never in DB.
- **Constant-time comparison:** `secrets.compare_digest()` for token verification (prevents timing attacks).
- **Rate limiting:** Refresh endpoint rate-limited per user.
- **Reuse detection:** If a rotated token is reused, the entire session is revoked (security response).

**Incident Response (Compromised Token):**
- If a refresh token is compromised:
  1. User calls `POST /v1/auth/sessions/{id}/revoke` to revoke that device
  2. Or admin revokes all sessions for the user
  3. All refresh tokens in that session are revoked
  4. Session is blacklisted in Redis (access tokens invalidated immediately)
  5. User must re-authenticate on that device
  6. Other devices remain active (family isolation)

**Implementation:**
```python
# Token verification (constant-time)
from app.core.security import verify_token_hash

if refresh_token_record and not verify_token_hash(token, refresh_token_record.token_hash):
    # Invalid token
    return 401

# Token rotation on refresh
old_token.rotated_at = datetime.now(UTC)
new_token = create_refresh_token()
new_refresh_token_record = RefreshToken(
    session_id=session.id,  # Same session
    token_hash=hash_token(new_token),
    replaced_by_token_id=old_token.id,
)
```

---

### Content Security Policy (CSP)

**Current:** ✅ **Implemented (Report-Only Mode)**

Content-Security-Policy is implemented in **REPORT-ONLY** mode to harden against XSS attacks without breaking the application. Violations are collected and analyzed before enforcing a blocking policy.

#### Implementation

**Frontend (Next.js):**
- CSP headers added via `middleware.ts`
- `Content-Security-Policy-Report-Only` header set on all responses
- `Report-To` header configured for reporting API

**Starter Policy (Report-Only):**
```
default-src 'self'
script-src 'self' 'unsafe-eval' 'unsafe-inline'  # Temporary for Next.js
style-src 'self' 'unsafe-inline'                  # Temporary for Next.js
img-src 'self' data: blob:
font-src 'self' data:
connect-src 'self' <API_URL> ws: wss:
frame-ancestors 'none'
base-uri 'self'
form-action 'self'
report-uri /v1/security/csp-report
```

**Note:** `unsafe-inline` and `unsafe-eval` are temporary for Next.js compatibility. These should be removed after:
1. Collecting violation reports
2. Identifying required inline scripts/styles
3. Moving to nonces or hashes

#### Backend Report Collection

**Endpoint:** `POST /v1/security/csp-report`
- Accepts CSP violation reports (CSP reporting API format)
- Rate-limited: 100 requests/minute per IP
- Stores reports in `csp_reports` table
- Fire-and-forget: Always returns 204 (no content)

**Report Storage:**
- `document_uri`: Page where violation occurred
- `blocked_uri`: Resource that was blocked
- `violated_directive`: CSP directive violated (e.g., "script-src")
- `user_agent`, `ip_address`: Request metadata
- `source_file`, `line_number`, `column_number`: Source location (if available)

**Rate Limiting:**
- Policy: `security.csp_report` → 100/min per IP
- Fail-open: If Redis unavailable, requests are allowed (prevents blocking legitimate reports)

#### Rollout Plan

1. **Phase 1 (Current):** Report-Only Mode
   - Collect violation reports
   - Analyze common violations
   - Identify required inline scripts/styles

2. **Phase 2:** Tighten Policy
   - Remove `unsafe-inline` from `script-src`
   - Remove `unsafe-inline` from `style-src`
   - Use nonces or hashes for required inline content
   - Add specific domains for external resources

3. **Phase 3:** Enforce Mode
   - Switch from `Content-Security-Policy-Report-Only` to `Content-Security-Policy`
   - Monitor for false positives
   - Adjust policy as needed

#### Admin View (Future)

CSP reports can be viewed via:
- Database query: `SELECT * FROM csp_reports ORDER BY created_at DESC`
- Admin dashboard (optional future enhancement)

#### Configuration

**Environment Variables:**
- `NEXT_PUBLIC_API_URL`: API base URL (without `/v1`) for report-uri (default: `http://localhost:8000`)
- `NEXT_PUBLIC_API_BASE_URL`: API base URL (with `/v1`) - middleware handles both formats

**Tuning:**
- Adjust rate limits in `backend/app/security/rate_limit.py` → `RATE_LIMIT_POLICIES["security.csp_report"]`
- Sampling can be adjusted in `backend/app/api/v1/endpoints/security.py` (currently stores all reports)

**Verification:**
- See `docs/CSP_VERIFICATION.md` for verification checklist and troubleshooting

---

### Two-Person Approval (Production Governance)

**Current:** ✅ **Implemented (Production Only)**

High-risk actions require two-person approval in production environments to prevent accidental or malicious changes.

#### Environment Detection

- **Production:** `ENV=prod` → Two-person approval **required**
- **Non-Production:** `ENV=dev|staging|test` → Single admin with police-mode phrase **sufficient**

#### High-Risk Actions Requiring Approval

The following actions require two-person approval **only in production**:

1. **Profile Switch:**
   - `PROFILE_SWITCH_PRIMARY`: Switch to V1_PRIMARY profile
   - `PROFILE_SWITCH_FALLBACK`: Switch to V0_FALLBACK profile
   - **Endpoint:** `POST /v1/admin/algorithms/runtime/switch`
   - **Enforcement:** Direct calls return 409 (APPROVAL_REQUIRED) in production

2. **Infrastructure Enables:**
   - `IRT_ACTIVATE`: Activate IRT (shadow → active)
     - **Endpoint:** `POST /v1/admin/irt/activation/activate`
   - `ELASTICSEARCH_ENABLE`: Enable Elasticsearch search engine
     - **Endpoint:** `POST /v1/admin/search/runtime/switch` (when `mode="elasticsearch"`)
   - `NEO4J_ENABLE`: Enable Neo4j graph database
     - **Endpoint:** `POST /v1/admin/graph/runtime/switch` (when `mode="shadow"` or `mode="active"`)
   - `SNOWFLAKE_EXPORT_ENABLE`: Enable Snowflake data warehouse export
     - **Endpoint:** `POST /v1/admin/warehouse/runtime/switch` (when `mode="active"`)

**All other actions** (EXAM_MODE, FREEZE_UPDATES, module overrides) remain single-admin with police-mode confirmation phrase.

**Enforcement:** All high-risk endpoints automatically check for pending approval before executing. If no approval exists and the action requires approval in production, the endpoint returns `409 Conflict` with code `APPROVAL_REQUIRED`.

#### Approval Workflow

1. **Admin A Requests:**
   - Calls `POST /v1/admin/runtime/approvals/request`
   - Provides: `action_type`, `action_payload`, `reason`, `confirmation_phrase`
   - System creates pending approval record

2. **Admin B Approves:**
   - Views pending approvals: `GET /v1/admin/runtime/approvals/pending`
   - Approves: `POST /v1/admin/runtime/approvals/{id}/approve`
   - Must be **different admin** than requester
   - Must provide matching `confirmation_phrase`
   - Action is executed atomically upon approval

3. **Audit Trail:**
   - `switch_audit_log` records: `requested_by`, `approved_by`, `reason`, `before/after`
   - `two_person_approvals` table tracks request lifecycle

#### API Endpoints

- `POST /v1/admin/runtime/approvals/request` - Request approval
- `GET /v1/admin/runtime/approvals/pending` - List pending approvals
- `POST /v1/admin/runtime/approvals/{id}/approve` - Approve request
- `POST /v1/admin/runtime/approvals/{id}/reject` - Reject request

#### UI Integration

- **Pending Approvals Card:** Displays on admin algorithms page when approvals are pending
- **Automatic Request:** If direct action returns 409 (approval required), UI automatically creates approval request
- **Approval Dialog:** Second admin can approve/reject with confirmation phrase

#### Safety Features

- **Self-approval prevention:** Cannot approve your own request
- **Confirmation phrase required:** Approver must type exact phrase
- **Atomic execution:** Action executes only after approval
- **Audit trail:** Both requester and approver logged
- **Environment-aware:** Only enforced in production

#### Example Flow

```bash
# Admin A requests profile switch (production)
curl -X POST https://api.example.com/v1/admin/runtime/approvals/request \
  -H "Authorization: Bearer <ADMIN_A_TOKEN>" \
  -d '{
    "action_type": "PROFILE_SWITCH_FALLBACK",
    "action_payload": {"profile": "V0_FALLBACK"},
    "reason": "Performance issues detected",
    "confirmation_phrase": "SWITCH TO V0_FALLBACK"
  }'

# Admin B approves
curl -X POST https://api.example.com/v1/admin/runtime/approvals/{request_id}/approve \
  -H "Authorization: Bearer <ADMIN_B_TOKEN>" \
  -d '{
    "confirmation_phrase": "SWITCH TO V0_FALLBACK"
  }'
# → Action executes immediately
```

#### Configuration

- **Environment:** Set `ENV=prod` to enable two-person approval
- **Action Types:** Defined in `backend/app/api/v1/endpoints/admin_approvals.py` → `HIGH_RISK_ACTIONS`

---

### Data Privacy

#### GDPR Compliance (Future)

**Requirements:**
- Right to access: Export user data
- Right to deletion: Delete user account and data
- Data portability: Machine-readable export
- Consent management: Track user consent

**Implementation:**
- User data export endpoint
- Account deletion with cascade
- Audit log for data access
- Privacy policy acceptance tracking

#### PII Handling

**Personal Identifiable Information:**
- Email addresses
- Phone numbers
- Names
- IP addresses (logs)

**Protection:**
- Encryption at rest
- Access logging
- Minimal data collection
- Anonymization for analytics

---

### Security Headers

#### HTTP Security Headers (App-Level)

**Baseline Headers (Always Set):**
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information
- `X-Frame-Options: DENY` - Prevents clickjacking (change to `SAMEORIGIN` if you need iframes)
- `Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=(), usb=(), interest-cohort=()` - Restricts browser features
- `Cross-Origin-Opener-Policy: same-origin` - Isolates browsing context
- `Cross-Origin-Resource-Policy: same-origin` - Prevents cross-origin resource access

**Optional Headers (Environment-Controlled):**

**HSTS (Strict-Transport-Security):**
- Only enabled if `ENABLE_HSTS=true` AND `ENV=prod` AND HTTPS is guaranteed at edge
- Header: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- **Warning:** Only enable if you guarantee HTTPS at the edge/gateway level

**CSP (Content-Security-Policy):**
- Only enabled if `ENABLE_CSP=true` (default `false` to avoid breaking embeds)
- Default policy when enabled:
  ```
  default-src 'self';
  img-src 'self' data: https:;
  style-src 'self' 'unsafe-inline';
  script-src 'self' 'unsafe-eval';
  connect-src 'self' https: wss:;
  frame-ancestors 'none';
  ```
- **Note:** CSP can break third-party embeds. Test thoroughly before enabling in production.

**Implementation:**
The `SecurityHeadersMiddleware` automatically adds these headers to every response. Headers are always set (override any existing values) to ensure defense-in-depth.

**Configuration:**
```python
# In .env
ENABLE_HSTS=false  # Set true only in prod with HTTPS at edge
ENABLE_CSP=false   # Set true only after testing all embeds
```

---

### Edge/Gateway Header Enforcement

**Defense-in-Depth:** While the application sets security headers, it's recommended to also enforce them at the edge/gateway level for additional protection.

#### Recommended Gateway/CDN Configuration

**Cloudflare:**
1. Enable "Always Use HTTPS" in SSL/TLS settings
2. Add security headers via Page Rules or Transform Rules:
   ```
   X-Content-Type-Options: nosniff
   X-Frame-Options: DENY
   Referrer-Policy: strict-origin-when-cross-origin
   Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=(), usb=(), interest-cohort=()
   Cross-Origin-Opener-Policy: same-origin
   Cross-Origin-Resource-Policy: same-origin
   ```
3. Enable HSTS in SSL/TLS settings (if not set by app)
4. Configure WAF rules for additional protection

**Nginx:**
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # Force HTTPS redirect
    if ($scheme != "https") {
        return 301 https://$server_name$request_uri;
    }

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=(), usb=(), interest-cohort=()" always;
    add_header Cross-Origin-Opener-Policy "same-origin" always;
    add_header Cross-Origin-Resource-Policy "same-origin" always;
    
    # HSTS (only if HTTPS is guaranteed)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Proxy to FastAPI backend
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Caddy:**
```caddyfile
example.com {
    # Force HTTPS
    redir https://{host}{uri}

    # Security headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=(), usb=(), interest-cohort=()"
        Cross-Origin-Opener-Policy "same-origin"
        Cross-Origin-Resource-Policy "same-origin"
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    }

    reverse_proxy backend:8000
}
```

**Best Practices:**
1. **TLS Termination:** Always terminate TLS at the edge/gateway
2. **Header Enforcement:** Set security headers at both edge and app level (defense-in-depth)
3. **HSTS:** Only enable if HTTPS is guaranteed (never enable if HTTP is still accessible)
4. **Testing:** Use tools like [SecurityHeaders.com](https://securityheaders.com) to verify headers
5. **Monitoring:** Monitor for missing headers in production

**Note:** The application-level headers serve as a safety net. Edge-level headers provide the first line of defense and can protect even if the application fails to set headers.

---

### Vulnerability Management

#### Dependency Scanning

**Tools:**
- **Backend:** `pip-audit` (PyPI/OSV)
- **Frontend:** `pnpm audit` (npm advisory DB)
- CI runs both and uploads JSON reports as artifacts.

#### CI Dependency Audit Gates

The `dependency-audit` job runs on every push/PR to `main`:

1. **Backend:** Install deps → `pip-audit -f json -o backend-audit.json` → `scripts/audit_check_backend.py`
2. **Frontend:** `pnpm install --frozen-lockfile` → `pnpm audit --json > frontend-audit.json` → `scripts/audit_check_frontend.py`
3. **Artifacts:** `backend-audit.json` and `frontend-audit.json` are uploaded as `audit-reports`.

**Gate behavior:**
- **Backend:** Fail CI only on **CRITICAL** (and optionally **HIGH**). Low/medium do not block. Severity is resolved via OSV where needed.
- **Frontend:** Fail CI only if **CRITICAL** vulnerabilities exist. High/moderate/low do not block.
- **Config:** Set repository variable `FAIL_ON_HIGH=1` to also fail backend on HIGH.

#### Allowlist (`docs/security_allowlist_vulns.json`)

You can temporarily suppress a known vulnerability with justification and an expiry date.

**Format:**
```json
{
  "backend": [
    { "id": "CVE-2024-12345", "reason": "False positive; not in use path. Ticket DEV-123.", "expires": "2025-06-01" }
  ],
  "frontend": [
    { "id": "GHSA-xxxx-yyyy-zzzz", "reason": "Indirect dep; upgrade planned. Ticket DEV-456.", "expires": "2025-06-01" }
  ]
}
```

- **`id`:** CVE, GHSA, PYSEC, or npm advisory id. Must match exactly (case-insensitive).
- **`reason`:** Short justification (for humans). Required for auditability.
- **`expires`:** Date (YYYY-MM-DD). After this date the entry is ignored; CI will fail again if the vuln is still present.

**Allowlist responsibly:**
- Use only for **temporary** suppression (e.g. upstream fix pending, false positive, accepted risk with a ticket).
- Always set **`expires`** (e.g. 30–90 days). Prefer fixing over allowlisting.
- Prefer **backend** allowlist for CVE/GHSA; **frontend** for advisory id or GHSA.
- Never allowlist **CRITICAL** without a concrete remediation plan and expiry.

#### Process (general)

1. CI blocks on CRITICAL (and optionally HIGH for backend).
2. Critical: Patch within 24 hours.
3. High: Patch within 7 days (or allowlist with expiry if unavoidable).
4. Medium/Low: Patch in next release cycle; no CI block.

#### Penetration Testing

**Frequency:**
- Annual full penetration test
- Quarterly vulnerability assessments
- Continuous automated scanning

**Areas to Test:**
- Authentication bypass
- SQL injection
- XSS vulnerabilities
- CSRF attacks
- Session hijacking
- API abuse

---

### Audit & Logging

#### Security Event Logging

**Events to Log:**
- Login attempts (success/failure)
- Permission denied events
- Unusual API activity
- Data access (admin actions)
- Account changes
- Password resets

**Log Format:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "event": "login_attempt",
  "user_id": "user-123",
  "ip_address": "192.168.1.1",
  "success": true,
  "user_agent": "Mozilla/5.0..."
}
```

**Retention:**
- Security logs: 1 year
- Access logs: 90 days
- Application logs: 30 days

#### Audit Trail

**Tracked Actions:**
- Question creation/modification/deletion
- User role changes
- System configuration changes
- Data exports

**Implementation:**
```python
class AuditLog(Base):
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    action = Column(String)  # "question_created", "user_updated"
    resource_type = Column(String)  # "question", "user"
    resource_id = Column(String)
    changes = Column(JSON)  # Before/after state
    ip_address = Column(String)
    timestamp = Column(DateTime, default=func.now())
```

---

### Incident Response

#### Security Incident Procedure

1. **Detection**
   - Automated alerts
   - Manual reporting
   - Security monitoring

2. **Containment**
   - Isolate affected systems
   - Revoke compromised credentials
   - Block malicious IPs

3. **Investigation**
   - Log analysis
   - Timeline reconstruction
   - Impact assessment

4. **Remediation**
   - Patch vulnerabilities
   - Reset compromised accounts
   - Restore from backups if needed

5. **Post-Incident**
   - Root cause analysis
   - Process improvements
   - Documentation update

#### Contact Information

**Security Team:**
- Email: security@examprep.com
- Emergency: [To be defined]

**Reporting:**
- Security vulnerabilities: security@examprep.com
- Bug reports: support@examprep.com

---

### Compliance

#### Standards & Regulations

**Target Compliance:**
- GDPR (EU data protection)
- HIPAA (if handling medical records)
- SOC 2 Type II (enterprise customers)
- ISO 27001 (information security)

#### Security Certifications (Future)

- Regular security audits
- Third-party security assessments
- Compliance certifications
- Penetration test reports

---

## Security Checklist

### Development

- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (ORM usage)
- [ ] XSS prevention (React escaping)
- [ ] CSRF protection
- [ ] Rate limiting implemented
- [ ] Security headers configured
- [ ] Error messages don't leak sensitive info

### Deployment

- [ ] HTTPS enforced
- [ ] Secrets in environment variables
- [ ] Database credentials secured
- [ ] API keys not in code
- [ ] Security headers enabled
- [ ] CORS properly configured
- [ ] Firewall rules configured

### Monitoring

- [ ] Security event logging
- [ ] Failed login attempt tracking
- [ ] Unusual activity alerts
- [ ] Regular security scans
- [ ] Dependency updates automated

---

## Critical Action Audit & Police-Mode

### Critical Action Taxonomy

The following actions are classified as critical and require:
- Police-mode confirmation (typed phrase + reason)
- Mandatory audit logging
- Admin freeze protection

**Critical Audit Events:**
- `EMAIL_MODE_SWITCH` - Switch email runtime mode (DISABLED/SHADOW/ACTIVE)
- `EMAIL_OUTBOX_DRAIN` - Manually drain email outbox
- `NOTIFICATION_BROADCAST` - Broadcast notification to users
- `RANKING_MODE_SWITCH` - Switch ranking service mode
- `RANKING_COMPUTE` - Run ranking computation
- `WAREHOUSE_MODE_SWITCH` - Switch warehouse mode
- `SEARCH_MODE_SWITCH` - Switch search engine mode
- `ALGO_MODE_SWITCH` - Switch algorithm runtime profile
- `USER_ADMIN_UPDATE` - Update admin user permissions
- `ADMIN_FREEZE_CHANGED` - Enable/disable admin freeze
- `EXAM_MODE_CHANGED` - Enable/disable exam mode (blocks heavy operations)

### Police-Mode Confirmation

All critical endpoints require:
1. **Exact confirmation phrase** (case-sensitive, must match exactly)
2. **Non-empty reason** (required for audit trail)

**Standard Phrases:**
- `SWITCH EMAIL TO {DISABLED|SHADOW|ACTIVE}`
- `DRAIN EMAIL OUTBOX`
- `BROADCAST NOTIFICATION`
- `SWITCH RANKING TO {mode}`
- `RUN RANKING COMPUTE`
- `SWITCH ALGO TO {mode}`
- `SET ADMIN FREEZE`
- `ENABLE EXAM MODE` - Enable exam mode (blocks heavy operations)
- `DISABLE EXAM MODE` - Disable exam mode (resumes normal operations)

**Implementation:**
```python
from app.security.police_mode import validate_police_confirm

@router.post("/endpoint")
async def critical_endpoint(
    request_data: SomeRequest,  # Must include confirmation_phrase and reason
    request: Request,
    ...
):
    reason = validate_police_confirm(
        request,
        request_data.confirmation_phrase,
        request_data.reason,
        "DRAIN EMAIL OUTBOX",
    )
    # reason is validated and attached to request.state for audit
```

### Audit Log Requirements

All critical actions must create an audit log entry with:
- `actor_user_id` - User performing the action
- `actor_role` - Role of the actor (stored in meta)
- `action` - Critical event type (e.g., "EMAIL_MODE_SWITCH")
- `entity_type` - Type of entity affected
- `entity_id` - ID of the entity (or generated UUID for operations)
- `reason` - **Required** for critical actions (stored in meta)
- `request_id` - Request ID for traceability (stored in meta)
- `before` - State before change (if applicable)
- `after` - State after change (if applicable)
- `meta` - Additional metadata (IP, user-agent, etc.)
- `created_at` - Timestamp

**Audit Helper:**
```python
from app.core.audit import write_audit_critical

write_audit_critical(
    db=db,
    actor_user_id=current_user.id,
    actor_role=current_user.role,
    action="EMAIL_MODE_SWITCH",
    entity_type="EMAIL_RUNTIME",
    entity_id=uuid4(),
    reason=reason,  # Required
    request=request,  # For request_id extraction
    before=previous_state,
    after=new_state,
)
```

### Admin Freeze Emergency Switch

**Purpose:** Read-only mode for admin mutations during emergencies.

**Configuration:**
- Stored in `admin_security_runtime` table (singleton)
- Fields: `admin_freeze` (bool), `freeze_reason` (text), `set_by_user_id`, `set_at`

**Behavior:**
- When `admin_freeze=true`:
  - All critical admin mutation endpoints return **423 Locked**
  - Read endpoints remain accessible
  - Error response: `{ error: { code: "ADMIN_FREEZE", message: "Admin mutations disabled", details: { reason: "..." } } }`

**Endpoints:**
- `GET /v1/admin/security/runtime` - Get freeze status
- `POST /v1/admin/security/freeze` - Set/unset freeze (requires police-mode: "SET ADMIN FREEZE")

**Enforcement:**
All critical endpoints call `check_admin_freeze(db)` at the start:
```python
from app.security.admin_freeze import check_admin_freeze

@router.post("/critical-endpoint")
async def endpoint(...):
    check_admin_freeze(db)  # Raises 423 if frozen
    # ... rest of endpoint logic
```

## Security Roadmap

### Phase 1 (Current)
- ⚠️ Temporary authentication (development only)
- ✅ Input validation (Pydantic)
- ✅ CORS configuration
- ✅ Rate limiting (Redis-backed)
- ✅ Security headers
- ✅ Token revocation (rotation + reuse detection)
- ✅ Audit logging for critical actions
- ✅ Police-mode confirmation
- ✅ Admin freeze emergency switch

### Phase 2 (Next)
- ⏳ OAuth2/JWT authentication
- ⏳ Role-based access control
- ⏳ Session management
- ⏳ Password hashing
- ⏳ Security headers

### Phase 3 (Future)
- ⏳ Advanced rate limiting
- ⏳ Audit logging
- ⏳ Encryption at rest
- ⏳ Vulnerability scanning
- ⏳ Penetration testing

### Phase 4 (Advanced)
- ⏳ GDPR compliance
- ⏳ SOC 2 certification
- ⏳ Advanced threat detection
- ⏳ Security monitoring dashboard

