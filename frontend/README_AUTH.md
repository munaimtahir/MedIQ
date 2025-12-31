# Frontend Authentication - BFF Pattern with httpOnly Cookies

This document describes the authentication implementation using a Backend-for-Frontend (BFF) pattern with httpOnly cookies.

## Architecture

- **Browser** → Only talks to Next.js (same-origin)
- **Next.js BFF** → Proxies to FastAPI (server-to-server)
- **Tokens** → Stored in httpOnly cookies (never in localStorage)
- **Auth Flow** → Login/signup set cookies, logout clears cookies

## Environment Variables

Create a `.env.local` file in the frontend directory:

```env
# Backend URL (server-side only, NOT NEXT_PUBLIC)
BACKEND_URL=http://backend:8000

# Cookie configuration
# Note: In production (NODE_ENV=production), Secure is ALWAYS true (HTTPS required)
# COOKIE_SECURE is ignored in production if set to false
COOKIE_SECURE=false          # Only used in dev; production always forces Secure=true
COOKIE_SAMESITE=lax          # lax, strict, or none (default: lax)
COOKIE_DOMAIN=               # Optional, for subdomains (leave empty for single domain)

# Cookie TTL (seconds)
ACCESS_COOKIE_MAXAGE_SECONDS=900        # 15 minutes (default)
REFRESH_COOKIE_MAXAGE_SECONDS=1209600   # 14 days (default)
```

### Production Security

**Important:** In production (`NODE_ENV=production`):
- Cookies are **ALWAYS** set with `Secure=true` (HTTPS required)
- If `COOKIE_SECURE=false` is set in production, it is **ignored** and a warning is logged
- Production deployments **must** use HTTPS
- On `http://localhost` (dev), `Secure=false` is used automatically

## API Routes (BFF)

All auth endpoints are under `/api/auth/*`:

- `POST /api/auth/login` - Login with email/password
- `POST /api/auth/signup` - Create new account
- `GET /api/auth/me` - Get current user
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout and clear cookies

## Client Usage

```typescript
import { authClient } from "@/lib/authClient";

// Login
const result = await authClient.login({ email, password });
if (result.data?.user) {
  // Success - cookies are set automatically
}

// Get current user
const meResult = await authClient.me();
const user = meResult.data?.user;

// Logout
await authClient.logout();
```

## Route Guards

Middleware protects routes:

- `/student/*` - Requires authentication (any role)
- `/admin/*` - Requires ADMIN or REVIEWER role
- `/login`, `/signup` - Public (no auth required)

Unauthenticated users are redirected to `/login` with a `redirect` query parameter.

## Automatic Token Refresh

The `fetcher` utility automatically refreshes tokens on 401:

```typescript
import fetcher from "@/lib/fetcher";

// Automatically handles token refresh
const data = await fetcher("/api/some-endpoint");
```

## Security Features

- ✅ httpOnly cookies (not accessible to JavaScript)
- ✅ **Secure flag enforced in production** (always true, HTTPS required)
- ✅ Secure=false in dev (works with http://localhost)
- ✅ SameSite protection (default: lax)
- ✅ Token rotation on refresh
- ✅ Automatic logout on refresh failure
- ✅ No tokens in localStorage
- ✅ MFA pending tokens rejected in middleware
- ✅ Centralized cookie configuration (no duplication)

## Testing

1. **Login Flow:**
   ```bash
   curl -X POST http://localhost:3000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com","password":"password"}' \
     -c cookies.txt
   ```

2. **Get Current User:**
   ```bash
   curl http://localhost:3000/api/auth/me \
     -b cookies.txt
   ```

3. **Logout:**
   ```bash
   curl -X POST http://localhost:3000/api/auth/logout \
     -b cookies.txt \
     -c cookies.txt
   ```

## Cookie Verification Checklist

### Development (http://localhost:3000)
- ✅ Cookies appear with `httpOnly` flag
- ✅ Cookies appear with `Secure=false` (works on HTTP)
- ✅ Cookies appear with `SameSite=Lax`
- ✅ Logout clears cookies (`Max-Age=0`)

### Production (https://yourdomain.com)
- ✅ Cookies appear with `httpOnly` flag
- ✅ Cookies appear with `Secure=true` (HTTPS required)
- ✅ Cookies appear with `SameSite=Lax`
- ✅ Logout clears cookies (`Max-Age=0`)
- ✅ `COOKIE_SECURE=false` is ignored (warning logged if set)

## Manual Test Steps

1. **Login:**
   - Navigate to `/login`
   - Enter credentials
   - Should redirect to `/student/dashboard` or `/admin` based on role
   - Cookies should be set (check DevTools → Application → Cookies)

2. **Protected Routes:**
   - Visit `/student/dashboard` without cookies → redirects to `/login`
   - Visit `/admin` as student → redirects to `/403`
   - Visit `/admin` as admin → access granted

3. **Token Refresh:**
   - Wait for access token to expire (or manually clear access_token cookie)
   - Make any API call
   - Should automatically refresh and retry

4. **Logout:**
   - Click logout button in sidebar
   - Cookies should be cleared
   - Should redirect to `/login`
   - Visiting `/student/*` should redirect to `/login`

