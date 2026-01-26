# Production Deployment with Traefik

This document describes the production deployment setup using Traefik as the reverse proxy.

## Quick Start

### 1. Prerequisites

**DNS Configuration** (must be done before deployment):
```bash
# Production
<DOMAIN>          A    192.0.2.1
api.<DOMAIN>      A    192.0.2.1

# Staging (optional, same server)
staging.<DOMAIN>      A    192.0.2.1
api-staging.<DOMAIN>  A    192.0.2.1
```

**Environment Variables** (set on server):
```bash
# Production
export DOMAIN=example.com
export TRAEFIK_ACME_EMAIL=admin@example.com
export POSTGRES_PASSWORD=<secure-password>
export JWT_SECRET=<secure-secret>
export AUTH_TOKEN_PEPPER=<secure-pepper>

# Staging (MUST be different from production)
export POSTGRES_PASSWORD_STAGING=<different-secure-password>
export JWT_SECRET_STAGING=<different-secure-secret>
export AUTH_TOKEN_PEPPER_STAGING=<different-secure-pepper>
# ... other required vars (see .env.example and .env.staging.example)
```

### 2. Deploy

```bash
# From project root
docker compose -f infra/docker/compose/docker-compose.prod.yml up -d --build
```

### 3. Verify

```bash
# Check Traefik logs
docker logs exam_platform_traefik -f

# Run smoke tests
./infra/scripts/smoke-test-traefik.sh <DOMAIN>
```

## Architecture

```
Internet
   │
   ▼
Traefik (ports 80/443) ──┐
   │                     │
   ├─► https://<DOMAIN> ──┼─► Frontend (port 3000, internal)
   │                     │
   └─► https://api.<DOMAIN> ──┼─► Backend (port 8000, internal)
                              │
                              ├─► PostgreSQL (internal)
                              ├─► Redis (internal)
                              ├─► Neo4j (internal)
                              └─► Elasticsearch (internal)
```

## Key Features

- ✅ **Automatic HTTPS**: Let's Encrypt certificates with auto-renewal
- ✅ **HTTP → HTTPS Redirect**: All HTTP traffic redirected to HTTPS
- ✅ **Security Headers**: Applied at edge (HSTS, X-Frame-Options, etc.)
- ✅ **Internal Services**: No host port exposure (only Traefik is public)
- ✅ **Request ID Propagation**: X-Request-ID headers passed through
- ✅ **Access Logs**: JSON format for analysis
- ✅ **Compression**: Response compression enabled

## Service Access

**Production:**
- **Frontend**: `https://<DOMAIN>`
- **Backend API**: `https://api.<DOMAIN>`
- **Health Check**: `https://api.<DOMAIN>/health`

**Staging:**
- **Frontend**: `https://staging.<DOMAIN>`
- **Backend API**: `https://api-staging.<DOMAIN>`
- **Health Check**: `https://api-staging.<DOMAIN>/health`

## Networks

- **edge**: Only Traefik (public-facing)
- **app**: All application services (backend, frontend, databases)

## Volumes

**Production:**
- **traefik_letsencrypt**: Let's Encrypt certificates (persistent, shared)
- **traefik_logs**: Traefik access logs (persistent)
- **postgres_data**: Production database
- **redis_data**: Production cache

**Staging:**
- **postgres_staging_data**: Staging database (separate)
- **redis_staging_data**: Staging cache (separate)

## Troubleshooting

See `docs/runbook.md` → "Traefik Reverse Proxy" section for detailed troubleshooting.

### Quick Checks

```bash
# Verify only Traefik is listening on 80/443
ss -tulpen | grep -E ':80|:443'

# Check Traefik logs
docker logs exam_platform_traefik --tail=100

# Verify routers registered
docker logs exam_platform_traefik | grep -i router

# Test HTTP redirect
curl -I http://<DOMAIN>

# Test HTTPS
curl -I https://api.<DOMAIN>/health
```

## Security Notes

- Dashboard is **NOT** exposed publicly
- Docker socket mounted read-only
- All internal services have no host port exposure
- Security headers applied at both edge (Traefik) and app (FastAPI) levels
