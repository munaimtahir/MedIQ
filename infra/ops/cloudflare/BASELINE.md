# Cloudflare Baseline Configuration

This document provides a reproducible, opinionated baseline configuration for Cloudflare in front of the Exam Prep Platform. It is designed to work alongside Traefik as the reverse proxy, providing CDN caching, WAF protection, bot mitigation, and rate limiting.

## Overview

Cloudflare sits in front of Traefik, providing:
- **CDN**: Static asset caching for frontend
- **WAF**: Web Application Firewall protection
- **Bot Protection**: Automated bot detection and mitigation
- **Rate Limiting**: API endpoint protection
- **TLS/SSL**: End-to-end encryption with Full (strict) mode
- **Security Headers**: Complementary to application headers (avoid duplication)

## Prerequisites

- Cloudflare account with domain added
- DNS nameservers pointed to Cloudflare
- Traefik configured with Let's Encrypt certificates
- Understanding of your application's security header configuration

## Step-by-Step Configuration

### 1. DNS Configuration

#### Production DNS Records

Navigate to: **DNS → Records**

| Type | Name | Content | Proxy Status | TTL | Notes |
|------|------|---------|--------------|-----|-------|
| A | `@` | `<server-ip>` | 🟠 Proxied | Auto | Root domain (frontend) |
| A | `api` | `<server-ip>` | 🟠 Proxied | Auto | API subdomain (backend) |
| AAAA | `@` | `<server-ipv6>` | 🟠 Proxied | Auto | IPv6 root domain |
| AAAA | `api` | `<server-ipv6>` | 🟠 Proxied | Auto | IPv6 API subdomain |

**Important**: 
- **Proxied** (orange cloud) = Traffic goes through Cloudflare (required for WAF, caching, etc.)
- **DNS-only** (grey cloud) = Direct DNS resolution (bypass Cloudflare)

#### Staging DNS Records

| Type | Name | Content | Proxy Status | TTL | Notes |
|------|------|---------|--------------|-----|-------|
| A | `staging` | `<staging-server-ip>` | 🟠 Proxied | Auto | Staging frontend |
| A | `api-staging` | `<staging-server-ip>` | 🟠 Proxied | Auto | Staging API |

### 2. SSL/TLS Configuration

Navigate to: **SSL/TLS → Overview**

**Settings:**
- **SSL/TLS encryption mode**: `Full (strict)`
  - Cloudflare ↔ Origin: HTTPS (valid certificate required)
  - Client ↔ Cloudflare: HTTPS (Cloudflare certificate)
  - **Why**: Traefik provides valid Let's Encrypt certificates, so strict mode is safe

**Additional Settings:**
- **Always Use HTTPS**: `On` (redirect HTTP to HTTPS)
- **Minimum TLS Version**: `TLS 1.2`
- **Opportunistic Encryption**: `On`
- **TLS 1.3**: `On`
- **Automatic HTTPS Rewrites**: `On`

Navigate to: **SSL/TLS → Edge Certificates**

- **Always Use HTTPS**: `On`
- **HTTP Strict Transport Security (HSTS)**: 
  - **Enable HSTS**: `On`
  - **Max Age**: `31536000` (1 year)
  - **Include Subdomains**: `On`
  - **Preload**: `On` (after testing)
  - **Note**: Application also sets HSTS. Cloudflare's HSTS is redundant but safe (last header wins).

### 3. Caching Configuration

#### Cache Rules (Recommended - Replaces Page Rules)

Navigate to: **Caching → Configuration → Cache Rules**

**Rule 1: Cache Static Assets (Long TTL)**

- **Rule Name**: `Cache Static Assets`
- **When incoming requests match**:
  - **Hostname**: `equals` → `example.com` OR `staging.example.com`
  - **URI Path**: `starts with` → `/` AND matches regex `.*\.(js|css|woff|woff2|ttf|eot|svg|png|jpg|jpeg|gif|webp|ico|avif)$`
- **Then**:
  - **Cache Status**: `Cache`
  - **Edge Cache TTL**: `1 month` (or `31536000` seconds)
  - **Browser Cache TTL**: `Respect Existing Headers`
  - **Cache Level**: `Cache Everything`

**Rule 2: Cache Frontend Assets Directory**

- **Rule Name**: `Cache Frontend Assets`
- **When incoming requests match**:
  - **Hostname**: `equals` → `example.com` OR `staging.example.com`
  - **URI Path**: `starts with` → `/assets/` OR `/_next/static/`
- **Then**:
  - **Cache Status**: `Cache`
  - **Edge Cache TTL**: `1 month`
  - **Browser Cache TTL**: `Respect Existing Headers`
  - **Cache Level**: `Cache Everything`

**Rule 3: Bypass API Endpoints**

- **Rule Name**: `Bypass API Cache`
- **When incoming requests match**:
  - **Hostname**: `equals` → `api.example.com` OR `api-staging.example.com`
  - **OR URI Path**: `starts with` → `/api/`
- **Then**:
  - **Cache Status**: `Bypass`
  - **Cache Level**: `Bypass`

**Rule 4: Bypass Frontend Dynamic Routes**

- **Rule Name**: `Bypass Frontend Dynamic`
- **When incoming requests match**:
  - **Hostname**: `equals` → `example.com` OR `staging.example.com`
  - **URI Path**: `starts with` → `/api/` OR `/admin/` OR `/student/`
- **Then**:
  - **Cache Status**: `Bypass`
  - **Cache Level**: `Bypass`

#### Browser Cache TTL

Navigate to: **Caching → Configuration → Browser Cache TTL**

- **Browser Cache TTL**: `Respect Existing Headers`
  - Application sets appropriate cache headers
  - Static assets: Long TTL (1 year)
  - API responses: No cache
  - HTML pages: Short TTL or no cache

### 4. Web Application Firewall (WAF)

Navigate to: **Security → WAF**

#### Managed Rules

**Cloudflare Managed Ruleset:**
- **Status**: `On`
- **Sensitivity**: `Medium` (recommended baseline)
  - **Low**: Too permissive, may miss attacks
  - **Medium**: Balanced protection (recommended)
  - **High**: May cause false positives (tune after monitoring)

**OWASP Core Ruleset:**
- **Status**: `On`
- **Sensitivity**: `Medium`

**Cloudflare Exposed Credentials Check:**
- **Status**: `On`
- **Action**: `Log` (monitor first, then `Block` if needed)

#### Custom Rules

Navigate to: **Security → WAF → Custom Rules**

**Rule 1: Block Admin Endpoints from Non-Allowed IPs** (Optional - requires Zero Trust)

- **Rule Name**: `Restrict Admin Endpoints`
- **Expression**: 
  ```
  (http.request.uri.path contains "/v1/admin" and not ip.src in {192.0.2.0/24 203.0.113.0/24})
  ```
- **Action**: `Block`
- **Note**: Replace IP ranges with your allowed admin IPs. Requires Zero Trust IP Access rules for better management.

**Rule 2: Block Common Attack Patterns**

- **Rule Name**: `Block SQL Injection Patterns`
- **Expression**:
  ```
  (http.request.uri.query contains "union select" or http.request.uri.query contains "'; drop table" or http.request.body contains "union select")
  ```
- **Action**: `Block`

#### Handling False Positives

If WAF blocks legitimate traffic:

1. **Check Firewall Events**: Security → Events
2. **Identify Rule**: Note the rule ID and sensitivity
3. **Create Exception**: 
   - Navigate to **Security → WAF → Custom Rules**
   - Click **Add exception**
   - **When incoming requests match**: Your specific condition
   - **Then**: `Skip` → Select the rule causing false positives
4. **Monitor**: Review exceptions regularly for security impact

### 5. Bot Protection

Navigate to: **Security → Bots**

**Bot Fight Mode:**
- **Status**: `On` (Free plan)
  - Basic bot detection and challenge

**Super Bot Fight Mode:** (Pro plan and above)
- **Status**: `On` (if available)
  - Enhanced bot detection
  - JavaScript challenge for suspicious bots

**Bot Management:** (Business plan and above)
- **Status**: `On` (if available)
- **Score Threshold**: `30` (lower = more strict)
- **Configure**:
  - **Verified Bots**: `Allow` (Googlebot, Bingbot, etc.)
  - **Likely Bots**: `Challenge` or `Block`
  - **Automated Bots**: `Block`

**Note**: For login endpoints, consider Cloudflare Turnstile (see section 9).

### 6. Rate Limiting

Navigate to: **Security → WAF → Rate limiting rules**

**Rule 1: Strict Rate Limit for Auth Endpoints**

- **Rule Name**: `Auth Endpoints Rate Limit`
- **When incoming requests match**:
  - **URI Path**: `starts with` → `/api/auth/login` OR `/api/auth/signup` OR `/api/v1/auth/login` OR `/api/v1/auth/signup`
- **Rate**: `5 requests per 1 minute`
- **Action**: `Block` for `1 minute`
- **Bypass**: `None` (or specific IPs if needed)

**Rule 2: Moderate Rate Limit for API Endpoints**

- **Rule Name**: `API Rate Limit`
- **When incoming requests match**:
  - **Hostname**: `equals` → `api.example.com` OR `api-staging.example.com`
  - **OR URI Path**: `starts with` → `/api/`
- **Rate**: `100 requests per 1 minute`
- **Action**: `Challenge` (CAPTCHA) for `1 minute`
- **Bypass**: `None`

**Rule 3: General Rate Limit**

- **Rule Name**: `General Rate Limit`
- **When incoming requests match**:
  - **All requests** (no specific condition)
- **Rate**: `1000 requests per 1 minute`
- **Action**: `Challenge` for `1 minute`
- **Bypass**: `None`

**Note**: These are Cloudflare-level rate limits. The application also has Redis-based rate limiting. Cloudflare provides first-line defense; application rate limiting handles authenticated users.

### 7. Security Headers

Navigate to: **Rules → Transform Rules → Modify Response Header**

**Important**: The application (FastAPI) already sets security headers. Cloudflare should **NOT duplicate** these headers to avoid conflicts. Only add headers that the application doesn't set.

**Check Application Headers First:**
- Application sets: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `HSTS` (if enabled)
- **Do NOT override these in Cloudflare**

**Optional: Add Missing Headers** (if application doesn't set them)

**Rule: Add Content Security Policy** (if not set by app)

- **Rule Name**: `Add CSP Header`
- **When incoming requests match**:
  - **Hostname**: `equals` → `example.com` OR `staging.example.com`
- **Then**:
  - **Set static**: `Content-Security-Policy` = `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://api.example.com;`
  - **Note**: Adjust CSP based on your frontend requirements. This is a restrictive example.

**Best Practice**: Let the application control security headers. Cloudflare should only add headers that complement (not override) application headers.

### 8. Zero Trust / IP Allowlisting (Admin Endpoints)

Navigate to: **Zero Trust → Access → Applications** (requires Zero Trust subscription)

**Application: Admin API**

1. **Add Application**:
   - **Application Name**: `Admin API`
   - **Application Domain**: `api.example.com`
   - **Path**: `/v1/admin/*`
   - **Session Duration**: `24 hours`

2. **Policy**:
   - **Action**: `Allow`
   - **Include**:
     - **Require**: `IP Address` → Add allowed IP ranges
     - **OR**: `Email` → Add admin email addresses
   - **Exclude**: `None`

3. **Additional Settings**:
   - **CORS Settings**: `Allow all origins` (or configure specific origins)
   - **Cookie settings**: `SameSite=Lax`, `Secure=true`

**Alternative (Without Zero Trust)**: Use WAF Custom Rules (see section 4) to block admin endpoints from non-allowed IPs.

### 9. Turnstile (Optional - For Login Protection)

Navigate to: **Turnstile** (if available on your plan)

**When to Use:**
- High-volume login attacks
- Bot-driven credential stuffing
- Need for invisible challenges (better UX than CAPTCHA)

**Configuration:**
- **Site Key**: Generate in Cloudflare dashboard
- **Secret Key**: Store securely (use in backend validation)
- **Widget Mode**: `Invisible` (recommended for better UX)
- **Domain**: Add your domain(s)

**Backend Integration:**
- Validate Turnstile tokens server-side before processing login
- See: https://developers.cloudflare.com/turnstile/

**Note**: This is optional and can be added later if login attacks increase.

### 10. Logging and Analytics

#### Web Analytics

Navigate to: **Analytics → Web Analytics**

- **Enable**: `On` (if available)
- **Privacy**: Respects user privacy (no cookies)
- **Use Cases**: Traffic patterns, popular pages, geographic distribution

#### Logpush (Enterprise Plan)

Navigate to: **Analytics → Logs → Logpush**

**Enable Logpush for:**
- **HTTP Requests**: Push to S3, GCS, or Datadog
- **Firewall Events**: WAF blocks, challenges, rate limits
- **Spectrum Events**: If using Spectrum

**Use Cases:**
- Security incident investigation
- Traffic analysis
- Performance monitoring
- Compliance logging

#### Real-Time Analytics

Navigate to: **Analytics → Web Traffic**

- **View**: Real-time request rates, status codes, top paths
- **Use**: Quick health checks, traffic spikes

### 11. Performance Settings

Navigate to: **Speed → Optimization**

**Auto Minify:**
- **JavaScript**: `On`
- **CSS**: `On`
- **HTML**: `On` (optional - may break some apps)

**Brotli:**
- **Status**: `On`
- **Compresses responses** (better than gzip)

**Early Hints:**
- **Status**: `On` (if available)
- **Preloads resources** for faster page loads

**HTTP/2:**
- **Status**: `On` (automatic)

**HTTP/3 (QUIC):**
- **Status**: `On` (if available)
- **Modern protocol** for faster connections

### 12. Network Settings

Navigate to: **Network**

**IPv6 Compatibility:**
- **Status**: `On`
- **IPv6 to IPv4**: `On` (if origin doesn't support IPv6)

**IP Geolocation:**
- **Status**: `On`
- **Use**: Route traffic, block regions if needed

**Pseudo IPv4:**
- **Status**: `Off` (unless needed for legacy systems)

## Compatibility Notes

### JWT Authentication

**Compatibility**: ✅ **Fully Compatible**

- JWT tokens in `Authorization: Bearer <token>` header pass through Cloudflare unchanged
- No special configuration needed
- Rate limiting applies per IP (not per JWT), which is acceptable for first-line defense

**Considerations:**
- Application-level rate limiting (Redis-based) handles authenticated user limits
- Cloudflare rate limiting provides DDoS protection at edge

### Cookies

**Compatibility**: ✅ **Fully Compatible**

- Cookies set by application (e.g., refresh tokens) work normally
- `SameSite`, `Secure`, `HttpOnly` attributes respected
- CORS credentials (`Access-Control-Allow-Credentials: true`) work with Cloudflare

**Configuration:**
- Ensure `CORS_ALLOW_CREDENTIALS=true` in application
- Set `SameSite=Lax` or `SameSite=None; Secure` for cross-origin cookies
- Cloudflare does not modify cookie attributes

### CORS

**Compatibility**: ✅ **Fully Compatible**

- CORS headers set by application pass through Cloudflare
- Cloudflare does not modify CORS headers
- Preflight requests (`OPTIONS`) are handled by application

**Configuration:**
- Application sets: `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, etc.
- Cloudflare: No CORS configuration needed (application handles it)

### WebSockets

**Compatibility**: ⚠️ **Requires Configuration**

If your application uses WebSockets:

1. **Enable WebSockets in Cloudflare**:
   - Navigate to: **Network**
   - **WebSockets**: `On`

2. **Traefik Configuration**:
   - Ensure Traefik supports WebSocket upgrades
   - Cloudflare proxies WebSocket connections automatically when enabled

3. **Rate Limiting**:
   - WebSocket connections are not subject to HTTP rate limiting rules
   - Consider application-level connection limits

**Note**: This application does not currently use WebSockets, but configuration is documented for future use.

### Traefik Integration

**Compatibility**: ✅ **Fully Compatible**

- Cloudflare → Traefik: HTTPS (Full strict mode)
- Traefik → Application: HTTP (internal network)
- Traefik handles:
  - Let's Encrypt certificates (for Cloudflare validation)
  - Internal routing
  - Application-level middleware

**Forwarded Headers:**
- Cloudflare sets: `CF-Connecting-IP` (real client IP)
- Traefik should use `CF-Connecting-IP` instead of `X-Forwarded-For` for accurate client IPs
- Application can read real IP from `CF-Connecting-IP` header

## Security Headers Strategy

### Application Headers (FastAPI)

The application sets these headers (do not duplicate in Cloudflare):
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=(), ...`
- `HSTS: max-age=31536000; includeSubDomains; preload` (if enabled)

### Cloudflare Headers (Optional Additions)

Only add headers that the application doesn't set:
- `Content-Security-Policy` (if not set by app - see section 7)
- `X-XSS-Protection: 1; mode=block` (legacy, but harmless)

**Best Practice**: Let the application control security headers. Cloudflare should complement, not override.

## Verification Checklist

After configuration:

- [ ] DNS records proxied (orange cloud)
- [ ] SSL/TLS mode: Full (strict)
- [ ] Always Use HTTPS: On
- [ ] HSTS enabled (if using Cloudflare HSTS)
- [ ] Cache rules configured (static assets cached, API bypassed)
- [ ] WAF managed rules: Medium sensitivity
- [ ] Bot protection enabled
- [ ] Rate limiting rules configured (auth endpoints stricter)
- [ ] Security headers: No duplication with application
- [ ] Zero Trust IP allowlisting (if using admin endpoints)
- [ ] Analytics/logging enabled (if needed)

## Testing

### Test Caching

```bash
# Static asset (should be cached)
curl -I https://example.com/_next/static/chunk.js
# Look for: CF-Cache-Status: HIT

# API endpoint (should bypass cache)
curl -I https://api.example.com/v1/health
# Look for: CF-Cache-Status: DYNAMIC or BYPASS
```

### Test Rate Limiting

```bash
# Rapid requests to auth endpoint (should trigger rate limit)
for i in {1..10}; do
  curl -X POST https://api.example.com/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test"}'
  sleep 0.5
done
# Should see: 429 Too Many Requests or challenge page
```

### Test WAF

```bash
# SQL injection attempt (should be blocked)
curl "https://api.example.com/v1/questions?q=1' OR '1'='1"
# Should see: 403 Forbidden (WAF block)
```

### Test Security Headers

```bash
# Check headers (application headers should be present)
curl -I https://example.com/
# Verify: X-Content-Type-Options, X-Frame-Options, etc.
```

## Troubleshooting

### Caching Issues

**Problem**: Static assets not cached
- **Check**: Cache Rules status (should be active)
- **Check**: Cache Level (should be "Cache Everything" for static assets)
- **Check**: Origin cache headers (should allow caching)

**Problem**: API responses cached
- **Check**: Cache Rules for API bypass
- **Check**: Origin `Cache-Control` headers (should be `no-cache`)

### WAF False Positives

**Problem**: Legitimate requests blocked
- **Solution**: Create WAF exception (see section 4)
- **Solution**: Lower sensitivity to "Low" temporarily, then tune
- **Solution**: Whitelist specific IPs in WAF custom rules

### Rate Limiting Too Strict

**Problem**: Legitimate users rate limited
- **Solution**: Increase rate limit thresholds
- **Solution**: Add bypass for authenticated users (requires application integration)
- **Solution**: Whitelist specific IPs

### SSL/TLS Errors

**Problem**: "SSL handshake failed" errors
- **Check**: SSL/TLS mode (should be "Full" or "Full (strict)")
- **Check**: Origin certificate validity (Traefik Let's Encrypt)
- **Check**: Minimum TLS version compatibility

## Maintenance

### Regular Reviews

- **Weekly**: Review WAF events for false positives
- **Monthly**: Review rate limiting effectiveness
- **Quarterly**: Review and update cache rules
- **Quarterly**: Review security header configuration

### Updates

- **Cloudflare Dashboard**: Check for new managed rules updates
- **WAF Rules**: Update sensitivity based on attack patterns
- **Rate Limits**: Adjust based on traffic patterns

## Files Reference

- `infra/ops/cloudflare/BASELINE.md` - This file
- `infra/traefik/traefik.yml` - Traefik configuration
- `backend/app/core/security_headers.py` - Application security headers

## Operational Runbooks

For Cloudflare operational procedures, see the [Runbooks](../runbooks/) directory:

- [08-Cloudflare.md](../runbooks/08-Cloudflare.md) - Comprehensive Cloudflare runbook covering:
  - ✅ WAF incident response (false positives, attack mitigation)
  - ✅ Rate limiting incidents (legitimate user blocks, DDoS response)
  - ✅ Cache invalidation (emergency cache clears, automated purge)
  - ✅ SSL/TLS incidents (certificate issues, handshake failures)
  - ✅ Bot protection tuning (adjusting thresholds, handling challenges)
  - ✅ Zero Trust access troubleshooting
  - ✅ Cloudflare analytics integration
  - ✅ WAF rule exception management
  - ✅ Rate limiting bypass procedures
  - ✅ Cloudflare log analysis
  - ✅ DNS failover procedures

## TODO Checklist for Future Enhancements

- [ ] Add Cloudflare analytics integration with observability stack (Prometheus/Grafana)
- [ ] Add monitoring/alerting for Cloudflare events (WAF blocks, rate limits) via webhooks
- [ ] Add Cloudflare API integration for automated configuration (Terraform provider)
