# CDN Configuration (Cloudflare) - Static-Only Shield Mode

This document describes the Cloudflare CDN configuration for the Medical Exam Platform in "static-only shield" mode. The CDN is configured to:

- **Cache only static assets and public pages**
- **NEVER cache API responses or authenticated content**
- **Protect origin from DDoS while maintaining correctness**

---

## Architecture Overview

```
User → Cloudflare CDN → Origin (Next.js + FastAPI)
```

**Key Principles:**
1. **Static assets** (`/_next/static/*`): Cached at edge (1 year)
2. **Public pages** (`/`, `/login`, `/signup`): Short cache (5 minutes)
3. **API endpoints** (`/v1/*`, `/api/*`): **BYPASS cache always**
4. **Authenticated routes** (`/student/*`, `/admin/*`): **BYPASS cache always**

---

## DNS Configuration

### Step 1: Add DNS Records

1. Log in to Cloudflare Dashboard
2. Select your domain
3. Go to **DNS** → **Records**

**Recommended Configuration:**

| Type | Name | Content | Proxy Status | TTL |
|------|------|---------|--------------|-----|
| A/AAAA | `@` | Origin IP | 🟠 Proxied | Auto |
| A/AAAA | `api` | Origin IP | 🟠 Proxied | Auto |

**Why proxy both?**
- **DDoS Protection**: Both frontend and API benefit from Cloudflare's DDoS mitigation
- **Cache Control**: We enforce cache bypass via Cache Rules (not DNS)
- **Security**: WAF and rate limiting at edge

**Alternative (if you prefer):**
- Frontend: 🟠 Proxied (for DDoS protection)
- API: ⚪ DNS Only (direct to origin, no CDN)

---

## Cache Rules Configuration

### Step 2: Create Cache Rules

Go to **Rules** → **Cache Rules** in Cloudflare Dashboard.

Create rules in **this exact order** (order matters - first match wins):

#### Rule 1: BYPASS API Endpoints

**Name:** `Bypass API`

**When incoming requests match:**
- **URL Path** → **starts with** → `/api/`
- **OR**
- **URL Path** → **starts with** → `/v1/`

**Then:**
- **Cache status** → **Bypass**
- **Origin Cache-Control** → **Respect**

**Priority:** 1 (highest)

---

#### Rule 2: BYPASS Authenticated App Routes

**Name:** `Bypass Auth Routes`

**When incoming requests match:**
- **URL Path** → **starts with** → `/admin`
- **OR**
- **URL Path** → **starts with** → `/student`
- **OR**
- **URL Path** → **starts with** → `/onboarding`

**Then:**
- **Cache status** → **Bypass**

**Priority:** 2

---

#### Rule 3: CACHE Next.js Static Assets

**Name:** `Cache Next Static`

**When incoming requests match:**
- **URL Path** → **starts with** → `/_next/static/`

**Then:**
- **Cache status** → **Eligible**
- **Edge TTL** → **1 year** (31536000 seconds)
- **Browser TTL** → **1 year** (31536000 seconds)

**Priority:** 3

---

#### Rule 4: CACHE Public Pages (Short)

**Name:** `Cache Public Pages`

**When incoming requests match:**
- **URL Path** → **equals** → `/`
- **OR**
- **URL Path** → **equals** → `/login`
- **OR**
- **URL Path** → **equals** → `/signup`
- **OR**
- **URL Path** → **equals** → `/legal`
- **OR**
- **URL Path** → **equals** → `/contact`

**Then:**
- **Cache status** → **Eligible**
- **Edge TTL** → **5 minutes** (300 seconds)
- **Browser TTL** → **5 minutes** (300 seconds)

**Priority:** 4

---

#### Rule 5: CACHE Media Files (Optional)

**Name:** `Cache Media`

**When incoming requests match:**
- **URL Path** → **starts with** → `/media/`
- **OR**
- **URL Path** → **starts with** → `/uploads/`

**Then:**
- **Cache status** → **Eligible**
- **Edge TTL** → **1 day** (86400 seconds)
- **Browser TTL** → **1 day** (86400 seconds)

**Priority:** 5

**Note:** Only enable if media filenames are content-hashed or immutable. If not, use shorter TTL or bypass.

---

## Security Settings

### Step 3: Configure Security

Go to **Security** → **Settings**

#### SSL/TLS

- **SSL/TLS encryption mode:** Full (strict)
- **Always Use HTTPS:** ON
- **Automatic HTTPS Rewrites:** ON
- **Minimum TLS Version:** 1.2

#### HSTS

- **HTTP Strict Transport Security (HSTS):** ON
- **Max Age:** 31536000 (1 year)
- **Include Subdomains:** ON (if applicable)
- **Preload:** OFF (unless you've submitted to HSTS preload list)

#### WAF (Web Application Firewall)

- **WAF:** ON (baseline rules)
- **Security Level:** Medium
- **Challenge Passage:** 30 minutes

**Custom Rules (Optional):**
- Block known bad bots
- Rate limit `/login` and `/signup` endpoints (light edge layer, app rate limits still apply)

#### Bot Fight Mode

- **Bot Fight Mode:** ON (optional, but recommended)
- **Super Bot Fight Mode:** OFF (requires paid plan)

#### Rate Limiting (Optional)

Create rate limit rules for:

1. **Login Endpoint:**
   - Path: `/login`
   - Rate: 5 requests per minute per IP
   - Action: Challenge (CAPTCHA)

2. **Signup Endpoint:**
   - Path: `/signup`
   - Rate: 3 requests per hour per IP
   - Action: Challenge (CAPTCHA)

**Note:** These are **light edge layers**. App-level rate limits still apply and are the primary enforcement.

---

## Page Rules (Legacy - Not Recommended)

**⚠️ Do NOT use Page Rules for cache control.**

Use **Cache Rules** instead (newer, more flexible). Page Rules are limited and can conflict with Cache Rules.

---

## Cache Settings

### Step 4: Global Cache Settings

Go to **Caching** → **Configuration**

- **Caching Level:** Standard
- **Browser Cache TTL:** Respect Existing Headers
- **Always Online:** ON (optional, for static assets)
- **Development Mode:** OFF (unless debugging)

**⚠️ CRITICAL: Do NOT enable "Cache Everything" globally.**

This would cache API responses and break the application. Our Cache Rules handle caching correctly.

---

## Verification

### Step 5: Verify Configuration

After deploying, verify cache behavior:

#### 1. Verify API Bypass

```bash
curl -I https://api.<your-domain>/v1/health
```

**Expected headers:**
```
Cache-Control: no-store
CF-Cache-Status: BYPASS
X-Origin: api
```

#### 2. Verify Static Assets Cache

```bash
curl -I https://<your-domain>/_next/static/<somefile>.js
```

**Expected headers:**
```
Cache-Control: public, max-age=31536000, immutable
CF-Cache-Status: HIT (after first request)
```

#### 3. Verify Public Pages Cache

```bash
curl -I https://<your-domain>/
```

**Expected headers:**
```
Cache-Control: public, max-age=300
CF-Cache-Status: HIT (after first request, within 5 minutes)
```

#### 4. Verify Authenticated Routes Bypass

```bash
curl -I https://<your-domain>/student/dashboard
```

**Expected headers:**
```
Cache-Control: no-store
CF-Cache-Status: BYPASS
```

---

## Debug Headers

The origin sets these debug headers to verify cache behavior:

- **X-Origin**: `"api"` (FastAPI) or `"frontend"` (Next.js)
- **X-Request-ID**: Request tracking ID
- **X-App-Version**: Git SHA (first 8 chars, if available)
- **CF-Cache-Status**: Cloudflare cache status
  - `MISS`: Not in cache (first request)
  - `HIT`: Served from cache
  - `BYPASS`: Bypassed cache (as configured)
  - `DYNAMIC`: Dynamic content (not cacheable)

---

## Troubleshooting

### Issue: API responses are being cached

**Symptoms:** `CF-Cache-Status: HIT` on API endpoints

**Resolution:**
1. Check Cache Rules order (API bypass rule must be priority 1)
2. Verify rule conditions match `/api/` and `/v1/`
3. Purge cache: **Caching** → **Purge Cache** → **Purge Everything**
4. Test again

### Issue: Static assets not caching

**Symptoms:** `CF-Cache-Status: MISS` on `/_next/static/*`

**Resolution:**
1. Verify Cache Rule 3 is active and matches `/_next/static/`
2. Check origin headers: should include `Cache-Control: public, max-age=31536000, immutable`
3. Wait for first request to populate cache (first request is always MISS)

### Issue: Public pages showing stale content

**Symptoms:** Changes not reflected after 5 minutes

**Resolution:**
1. This is expected (5-minute cache TTL)
2. To force update: **Caching** → **Purge Cache** → **Custom Purge** → Enter URL
3. Or wait for cache to expire (5 minutes)

### Issue: Authenticated content showing wrong user data

**Symptoms:** User A sees User B's data

**CRITICAL SECURITY ISSUE** - This should never happen if configured correctly.

**Immediate Actions:**
1. **Disable proxy immediately** (grey cloud on DNS records)
2. Verify Cache Rules: `/student/*` and `/admin/*` must bypass
3. Check origin headers: should include `Cache-Control: no-store`
4. Purge all cache
5. Re-enable proxy only after verification

---

## Rollback Procedure

### Emergency Rollback (Disable CDN)

1. **Go to DNS** → **Records**
2. **Click grey cloud** (⚪) on all proxied records
3. **DNS will resolve directly to origin** (bypass Cloudflare)
4. **Verify:** `curl -I https://<domain>/` should show origin headers directly

### Partial Rollback (Disable Caching)

1. **Go to Caching** → **Configuration**
2. **Set Caching Level:** Bypass
3. **All requests bypass cache** (but still go through Cloudflare for DDoS protection)

### Purge Cache

1. **Go to Caching** → **Purge Cache**
2. **Purge Everything** (removes all cached content)
3. **Or Custom Purge** (specific URLs)

---

## Performance Impact

### Expected Improvements

- **Static assets:** 90%+ cache hit rate (after warm-up)
- **Public pages:** 50-70% cache hit rate (5-minute TTL)
- **API endpoints:** 0% cache (by design, always bypass)
- **Origin load reduction:** 30-50% (static assets served from edge)

### Monitoring

Monitor these metrics in Cloudflare Analytics:

- **Cache Hit Ratio:** Should be 30-50% overall (mostly static assets)
- **Bandwidth Saved:** Should show significant savings
- **Origin Requests:** Should decrease (especially for static assets)
- **Error Rate:** Should remain stable (no increase)

---

## Best Practices

1. **Never cache API responses** - Always bypass `/v1/*` and `/api/*`
2. **Never cache authenticated content** - Always bypass `/student/*` and `/admin/*`
3. **Use Cache Rules, not Page Rules** - More flexible and maintainable
4. **Test in staging first** - Verify cache behavior before production
5. **Monitor CF-Cache-Status headers** - Verify expected behavior
6. **Purge cache after deployments** - If static assets change
7. **Keep origin headers correct** - CDN respects origin `Cache-Control` headers

---

## References

- [Cloudflare Cache Rules Documentation](https://developers.cloudflare.com/cache/how-to/cache-rules/)
- [Cloudflare Cache Headers](https://developers.cloudflare.com/cache/concepts/default-cache-behavior/)
- [Origin Cache-Control Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control)
- [Runbook: CDN Verification](./runbook.md#cdn-verification)
