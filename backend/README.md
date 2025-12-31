# Medical Exam Platform - Backend

Production-ready FastAPI backend with versioned API, structured logging, database migrations, and comprehensive error handling.

## Structure

```
backend/
├── app/
│   ├── main.py              # Application factory and entry point
│   ├── api/
│   │   └── v1/
│   │       ├── router.py    # Main v1 API router
│   │       └── endpoints/   # Endpoint modules (health, auth, etc.)
│   ├── core/
│   │   ├── config.py        # Settings (env-driven)
│   │   ├── errors.py        # Error handling and consistent error format
│   │   ├── logging.py       # Structured JSON logging
│   │   └── security_headers.py  # Security headers middleware
│   ├── db/
│   │   ├── engine.py        # Database engine
│   │   ├── session.py       # Session management
│   │   └── base.py          # Base model class
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   └── common/              # Shared utilities
│       └── request_id.py    # Request ID middleware
├── alembic/                 # Database migrations
├── alembic.ini              # Alembic configuration
├── requirements.txt         # Python dependencies
└── Dockerfile               # Docker image definition
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (via Docker Compose)
- Docker and Docker Compose (for containerized setup)

### Local Development

1. **Set up environment variables:**

   Copy `.env.example` to `.env` and configure:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your settings (database URL, CORS origins, etc.)

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run database migrations:**

   ```bash
   # Create initial migration (if needed)
   alembic revision --autogenerate -m "Initial migration"

   # Apply migrations
   alembic upgrade head
   ```

4. **Start the development server:**

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Or use Docker Compose:

   ```bash
   docker compose -f infra/docker/compose/docker-compose.dev.yml up --build
   ```

### Docker Setup

The backend is configured to run via Docker Compose. The compose file is located at:

```
infra/docker/compose/docker-compose.dev.yml
```

The backend service:
- Waits for PostgreSQL to be healthy
- Auto-reloads on code changes (dev mode)
- Exposes port 8000

## API Endpoints

All API endpoints are versioned under `/v1`:

- `GET /` - Root endpoint (API info)
- `GET /v1/health` - Health check (process alive)
- `GET /v1/ready` - Readiness check (dependencies)
- `POST /v1/auth/signup` - User registration
- `POST /v1/auth/login` - User login
- `POST /v1/auth/refresh` - Refresh tokens
- `POST /v1/auth/logout` - Logout (revoke refresh token)
- `GET /v1/auth/me` - Get current user
- `POST /v1/auth/password-reset/request` - Request password reset
- `POST /v1/auth/password-reset/confirm` - Confirm password reset
- `GET /docs` - OpenAPI documentation (dev only)
- `GET /redoc` - ReDoc documentation (dev only)

## Database Migrations

This project uses Alembic for database migrations.

### Creating a Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration
alembic revision -m "Description of changes"
```

### Applying Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific revision
alembic upgrade <revision>

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision>
```

### Migration Best Practices

- Always review auto-generated migrations before applying
- Test migrations on a copy of production data
- Never edit existing migrations (create new ones instead)
- Keep migrations small and focused

## Configuration

Configuration is managed via environment variables (see `.env.example`):

### Required (Production)

- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - Secret key for JWT tokens (must be strong, random string)
- `TOKEN_PEPPER` - Server-side pepper for token hashing (must be strong, random string)
- `ENV` - Environment: `dev`, `staging`, or `prod`

### Optional

- `JWT_ALG` - JWT algorithm (default: `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Access token TTL (default: `15`)
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token TTL (default: `14`)
- `PASSWORD_RESET_EXPIRE_MINUTES` - Password reset token TTL (default: `30`)
- `REDIS_URL` - Redis connection string (optional)
- `CORS_ORIGINS` - Comma-separated list of allowed origins
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `API_PREFIX` - API prefix (default: `/v1`)
- `SEED_DEMO_ACCOUNTS` - Seed demo accounts in dev (default: `false`)
- `REDIS_ENABLED` - Enable Redis (default: `true`)
- `REDIS_REQUIRED` - Require Redis connection (default: `false` in dev, `true` in prod)
- `RL_LOGIN_IP_LIMIT` - Login rate limit per IP (default: `20` per 10 min)
- `RL_LOGIN_EMAIL_LIMIT` - Login rate limit per email (default: `10` per 10 min)
- `RL_SIGNUP_IP_LIMIT` - Signup rate limit per IP (default: `5` per hour)
- `RL_RESET_IP_LIMIT` - Password reset rate limit per IP (default: `5` per hour)
- `RL_RESET_EMAIL_LIMIT` - Password reset rate limit per email (default: `3` per hour)
- `RL_REFRESH_USER_LIMIT` - Refresh token rate limit per user (default: `60` per hour)
- `LOGIN_FAIL_EMAIL_THRESHOLD` - Failed login attempts before email lockout (default: `8`)
- `LOGIN_FAIL_IP_THRESHOLD` - Failed login attempts before IP lockout (default: `30`)
- `EMAIL_LOCK_TTL` - Email lockout duration in seconds (default: `900` = 15 min)
- `IP_LOCK_TTL` - IP lockout duration in seconds (default: `900` = 15 min)
- `IP_LOCK_ESCALATION` - Enable IP lockout escalation (default: `true`)
- `IP_LOCK_MAX_TTL` - Maximum IP lockout duration in seconds (default: `86400` = 24 hours)
- `OAUTH_GOOGLE_CLIENT_ID` - Google OAuth client ID
- `OAUTH_GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `OAUTH_GOOGLE_REDIRECT_URI` - Google OAuth redirect URI
- `OAUTH_MICROSOFT_CLIENT_ID` - Microsoft OAuth client ID
- `OAUTH_MICROSOFT_CLIENT_SECRET` - Microsoft OAuth client secret
- `OAUTH_MICROSOFT_REDIRECT_URI` - Microsoft OAuth redirect URI
- `OAUTH_STATE_TTL` - OAuth state TTL in seconds (default: `600` = 10 min)
- `OAUTH_NONCE_TTL` - OAuth nonce TTL in seconds (default: `600` = 10 min)
- `MFA_ENCRYPTION_KEY` - Fernet key for encrypting TOTP secrets (required in prod)
- `MFA_TOTP_ISSUER` - TOTP issuer name (default: `ExamPrepSite`)
- `MFA_TOTP_PERIOD` - TOTP time period in seconds (default: `30`)
- `MFA_TOTP_DIGITS` - TOTP code length (default: `6`)
- `MFA_BACKUP_CODES_COUNT` - Number of backup codes (default: `10`)
- `MFA_TOKEN_EXPIRE_MINUTES` - MFA pending token TTL (default: `5`)

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {},
    "request_id": "uuid"
  }
}
```

Error codes:
- `VALIDATION_ERROR` - Request validation failed (422)
- `HTTP_ERROR` - HTTP exception (4xx/5xx)
- `INTERNAL_ERROR` - Unhandled exception (500)

## Logging

The application uses structured JSON logging with the following fields:

- `timestamp` - ISO 8601 timestamp
- `level` - Log level (DEBUG, INFO, WARNING, ERROR)
- `logger` - Logger name
- `module` - Python module
- `function` - Function name
- `request_id` - Request ID (for request logs)
- `method` - HTTP method (for request logs)
- `path` - Request path (for request logs)
- `status_code` - HTTP status code (for request logs)
- `latency_ms` - Request latency in milliseconds

## Request ID

Every request is assigned a unique request ID:

- Generated automatically if not provided in `X-Request-ID` header
- Included in response header `X-Request-ID`
- Included in all log entries for the request
- Included in error responses

## Health Checks

### Health Endpoint (`/v1/health`)

Simple liveness check. Returns 200 if the API process is running.

### Readiness Endpoint (`/v1/ready`)

Checks dependencies:

- **Database**: Connectivity test (`SELECT 1`)
- **Redis**: Optional ping (if `REDIS_URL` is configured)

Returns:
- `ok` - All checks passed
- `degraded` - Some optional checks failed (e.g., Redis)
- `down` - Critical checks failed (e.g., Database)

## Security Headers

The application automatically adds security headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()`
- `Strict-Transport-Security` (HTTPS only, production only)

## CORS

CORS is configured via `CORS_ORIGINS` environment variable (comma-separated list).

Example:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
ruff check .
```

### Type Checking

```bash
mypy app/
```

## Production Deployment

1. Set `ENV=prod` in environment
2. Ensure all required environment variables are set
3. Run database migrations before starting the application
4. Use a production ASGI server (e.g., Gunicorn with Uvicorn workers)
5. Set up proper logging aggregation
6. Configure monitoring and alerting

## Authentication & Authorization

The backend includes a complete authentication system with:

- **User registration and login** (`POST /v1/auth/signup`, `POST /v1/auth/login`)
- **JWT access tokens** (short-lived, 15 minutes default)
- **Refresh token rotation** (`POST /v1/auth/refresh`)
- **Token revocation** (`POST /v1/auth/logout`)
- **Password reset** (stub endpoints, email sending not implemented yet)
- **RBAC** (Role-Based Access Control) with `STUDENT`, `ADMIN`, `REVIEWER` roles

### Demo Accounts (Dev Only)

When `ENV=dev` and `SEED_DEMO_ACCOUNTS=true`, the following accounts are automatically created:

- **Admin**: `admin@example.com` / `Admin123!`
- **Student**: `student@example.com` / `Student123!`

### Using Authentication

**Sign up:**
```bash
curl -X POST http://localhost:8000/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com", "password": "SecurePass123!"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "password": "SecurePass123!"}'
```

**Get current user:**
```bash
curl -X GET http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

**Refresh tokens:**
```bash
curl -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

**Logout:**
```bash
curl -X POST http://localhost:8000/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

### Protecting Routes

Use the `get_current_user` dependency to require authentication:

```python
from app.core.dependencies import get_current_user
from app.models.user import User

@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id}
```

Use `require_roles` to enforce role-based access:

```python
from app.core.dependencies import require_roles
from app.models.user import UserRole

@router.get("/admin-only")
async def admin_route(
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    return {"message": "Admin access granted"}
```

## Security Verification

A security verification harness is available to validate critical security behaviors:

```bash
# Run security tests
pytest -q backend/tests/security/test_security_controls.py
```

The harness verifies:
1. Invalid login returns generic error (doesn't reveal account existence)
2. Rate limiting returns 429 with Retry-After header
3. Account lockout after repeated failures
4. OAuth invalid state handling
5. MFA invalid code handling
6. Logs include request_id and event_type
7. No secrets appear in logs

### Running Security Tests

```bash
# Ensure backend is running
docker compose up -d

# Run security verification
pytest -q backend/tests/security/test_security_controls.py -v
```

## Multi-Device Policy

The system supports **single-device** authentication by default:
- On login, all existing refresh tokens for the user are revoked
- Only one active refresh token per user is allowed
- This provides better security but limits multi-device usage

### Logout All Devices

Users can log out from all devices:

```bash
curl -X POST http://localhost:8000/v1/auth/logout-all \
  -H "Authorization: Bearer <access_token>"
```

This revokes all refresh tokens for the authenticated user.

**Note:** To enable multi-device support, modify the login endpoint to not revoke existing tokens. The current implementation prioritizes security over convenience.

## OAuth/OIDC Security

### Redirect URI Validation

OAuth redirect URIs are validated against an allow-list:
- Set `OAUTH_ALLOWED_REDIRECT_URIS` in environment (comma-separated)
- User-provided redirect URIs are rejected if not in allow-list
- Default redirect URIs from config are always allowed

Example:
```env
OAUTH_ALLOWED_REDIRECT_URIS=http://localhost:3000/callback,https://app.example.com/callback
```

### State/Nonce Security

- OAuth state and nonce are stored in Redis with TTL (default 600s)
- State keys are deleted immediately after use (one-time use)
- Prevents replay attacks and CSRF

### JWKS Caching

- JWKS (JSON Web Key Set) are cached in-memory with TTL (default 3600s)
- Reduces external HTTP requests to OAuth providers
- Cache expires and refreshes automatically

## MFA Security

### Backup Code Regeneration

Users can regenerate backup codes (requires TOTP confirmation):

```bash
curl -X POST http://localhost:8000/v1/auth/mfa/backup-codes/regenerate \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}'
```

**Security:** Old backup codes are invalidated when new ones are generated.

### Disable MFA

Users can disable MFA (requires password or TOTP confirmation):

```bash
curl -X POST http://localhost:8000/v1/auth/mfa/disable \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"password": "user-password"}'
```

Or with TOTP:
```bash
curl -X POST http://localhost:8000/v1/auth/mfa/disable \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}'
```

### MFA Pending Token

- MFA step-up tokens are short-lived JWTs (default 5 minutes)
- Token type is `mfa_pending` (cannot be used as access token)
- Includes `sub`, `iat`, `exp`, and `jti` claims
- Verified in MFA complete endpoint

### TOTP Clock Skew

- TOTP verification allows ±1 timestep drift (30 seconds)
- Handles minor clock synchronization issues
- Configurable via `MFA_TOTP_PERIOD` (default 30s)

## Environment Variables

### OAuth/OIDC

- `OAUTH_GOOGLE_CLIENT_ID` - Google OAuth client ID
- `OAUTH_GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `OAUTH_GOOGLE_REDIRECT_URI` - Google redirect URI
- `OAUTH_MICROSOFT_CLIENT_ID` - Microsoft OAuth client ID
- `OAUTH_MICROSOFT_CLIENT_SECRET` - Microsoft OAuth client secret
- `OAUTH_MICROSOFT_REDIRECT_URI` - Microsoft redirect URI
- `OAUTH_STATE_TTL` - OAuth state TTL in seconds (default 600)
- `OAUTH_LINK_TTL` - OAuth link token TTL in seconds (default 600)
- `OAUTH_ALLOWED_REDIRECT_URIS` - Comma-separated list of allowed redirect URIs
- `JWKS_CACHE_TTL_SECONDS` - JWKS cache TTL in seconds (default 3600)

### MFA

- `MFA_ENCRYPTION_KEY` - Fernet key for encrypting TOTP secrets (required in prod)
- `MFA_TOTP_ISSUER` - TOTP issuer name (default "ExamPrepSite")
- `MFA_TOTP_PERIOD` - TOTP period in seconds (default 30)
- `MFA_TOTP_DIGITS` - TOTP code length (default 6)
- `MFA_BACKUP_CODES_COUNT` - Number of backup codes (default 10)
- `MFA_TOKEN_EXPIRE_MINUTES` - MFA pending token TTL in minutes (default 5)

## Next Steps

After this foundation is in place, you can add:

- Additional OAuth providers
- Enhanced session management
- User management endpoints
- Business logic services
- Additional API endpoints
- Background tasks
- Caching layer

