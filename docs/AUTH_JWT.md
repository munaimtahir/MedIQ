# JWT Authentication (Canonical)

## Backend Expectations

Source files:
- `backend/app/core/dependencies.py`
- `backend/app/core/security.py`
- `backend/app/api/v1/endpoints/auth.py`

Rules:
- Protected endpoints require `Authorization: Bearer <access_token>`.
- Access token is JWT with role + user id claims.
- Refresh token is opaque (stored hashed in DB), not a JWT.
- Refresh endpoint: `POST /v1/auth/refresh` rotates refresh tokens.
- Logout endpoints:
  - `POST /v1/auth/logout`
  - `POST /v1/auth/logout-all`

## Frontend BFF + Cookie Model

Source files:
- `frontend/app/api/auth/login/route.ts`
- `frontend/app/api/auth/refresh/route.ts`
- `frontend/lib/server/cookies.ts`
- `frontend/lib/server/backendClient.ts`

Flow:
1. Browser calls Next BFF route (`/api/auth/login`).
2. BFF calls backend login and receives tokens.
3. BFF sets `access_token` + `refresh_token` as `httpOnly` cookies.
4. Server-side BFF forwards access token as Bearer token to backend.
5. On auth expiry, client/BFF should call `/api/auth/refresh` and rotate cookies.
6. If refresh fails, cookies are cleared and user must login again.

## Local Dev Login (Demo Accounts)

Enable in `.env`:

```bash
ENV=dev
SEED_DEMO_ACCOUNTS=true
```

Demo credentials:
- `admin@example.com` / `Admin123!`
- `student@example.com` / `Student123!`
- `reviewer@example.com` / `Reviewer123!`

Created by: `backend/app/core/seed_auth.py`.

## Security Notes

- Tokens are not stored in `localStorage`.
- Cookies are `httpOnly`; frontend JS cannot read token values.
- `COOKIE_SECURE=true` is enforced in production by frontend cookie helpers.
- In production, backend validates that JWT signing keys and token pepper values are set (`backend/app/core/config.py`).
