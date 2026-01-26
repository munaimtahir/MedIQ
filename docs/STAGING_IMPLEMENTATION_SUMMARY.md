# Staging Environment Implementation Summary

## Overview

This document summarizes the staging environment implementation that extends the Traefik reverse proxy setup to support both production and staging domains on the same server.

## Implementation Date

January 2026

## Architecture

### Domains

**Production:**
- Frontend: `https://<DOMAIN>`
- Backend: `https://api.<DOMAIN>`

**Staging:**
- Frontend: `https://staging.<DOMAIN>`
- Backend: `https://api-staging.<DOMAIN>`

### Services

**Production Services:**
- `backend` (FastAPI)
- `frontend` (Next.js)
- `postgres` (PostgreSQL)
- `redis` (Redis cache)

**Staging Services (New):**
- `backend_staging` (FastAPI)
- `frontend_staging` (Next.js)
- `postgres_staging` (PostgreSQL - separate database)
- `redis_staging` (Redis - separate cache)

**Shared Infrastructure:**
- `traefik` (Reverse proxy - handles both prod and staging)
- `neo4j` (Graph database - shared, read-only recommended)
- `elasticsearch` (Search - shared with separate index prefix)

## Key Features

### 1. Complete Isolation

- **Separate Databases**: Staging uses `postgres_staging` with its own volume
- **Separate Cache**: Staging uses `redis_staging` with its own volume
- **Separate Secrets**: Different JWT secrets and token peppers
- **Separate CORS**: Staging CORS only allows staging domains
- **Separate Environment**: `ENV=staging` flag

### 2. Security

- **No Secret Reuse**: Staging secrets are completely different from production
- **Email Safety**: Staging uses shadow mode (no real emails sent)
- **Database Isolation**: Staging cannot access production data
- **Network Isolation**: All services on internal `app` network, no host ports

### 3. Traefik Integration

- **Same Instance**: Both prod and staging use the same Traefik instance
- **Automatic HTTPS**: Let's Encrypt certificates for staging domains
- **HTTP → HTTPS Redirect**: Automatic redirects for staging
- **Security Headers**: Same edge security headers as production

### 4. Deployment Flexibility

- **Independent Deployment**: Staging can be started/stopped without affecting production
- **Selective Updates**: Update staging services independently
- **Easy Tear Down**: Remove staging without touching production

## Files Created/Modified

### Configuration Files

1. **`infra/docker/compose/docker-compose.prod.yml`**
   - Added staging services (postgres_staging, redis_staging, backend_staging, frontend_staging)
   - Added staging volumes
   - Added Traefik labels for staging routers

2. **`infra/docker/compose/.env.staging.example`**
   - Template for staging environment variables
   - Separate secrets configuration
   - Staging-specific CORS and OAuth settings

### Documentation

3. **`docs/runbook.md`**
   - Added "Staging Environment" section
   - Deployment procedures
   - Migration instructions
   - Troubleshooting guide

4. **`infra/docker/compose/STAGING_DEPLOYMENT.md`**
   - Quick reference guide
   - Step-by-step deployment
   - Common operations
   - Troubleshooting checklist

5. **`infra/docker/compose/README_PROD.md`**
   - Updated with staging information
   - Staging DNS requirements
   - Staging environment variables

### Scripts

6. **`infra/scripts/smoke-test-traefik.sh`**
   - Added `--staging` flag support
   - Staging HTTP → HTTPS redirect tests
   - Staging HTTPS health checks
   - Staging security headers verification

7. **`infra/scripts/deploy-staging.sh`** (New)
   - Automated staging deployment script
   - Health check waiting
   - Optional migration support
   - Service verification

8. **`infra/scripts/verify-staging-isolation.sh`** (New)
   - Isolation verification script
   - Database/Redis isolation checks
   - Secret uniqueness verification
   - CORS configuration validation

## Deployment Process

### Initial Setup

1. **DNS Configuration:**
   ```bash
   staging.<DOMAIN>      A    <server-ip>
   api-staging.<DOMAIN>  A    <server-ip>
   ```

2. **Environment Variables:**
   - Copy `.env.staging.example` to `.env.staging`
   - Set all staging-specific secrets (MUST be different from production)

3. **Deploy:**
   ```bash
   # Manual
   docker compose -f infra/docker/compose/docker-compose.prod.yml \
     up -d postgres_staging redis_staging backend_staging frontend_staging
   
   # Or use helper script
   ./infra/scripts/deploy-staging.sh --migrate
   ```

4. **Run Migrations:**
   ```bash
   docker compose -f infra/docker/compose/docker-compose.prod.yml \
     run --rm backend_staging alembic upgrade head
   ```

### Updates

```bash
# Rebuild and restart staging
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d --build backend_staging frontend_staging

# Run migrations if needed
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  run --rm backend_staging alembic upgrade head
```

## Verification

### Smoke Tests

```bash
# Production + Staging
./infra/scripts/smoke-test-traefik.sh <DOMAIN> --staging
```

### Isolation Verification

```bash
./infra/scripts/verify-staging-isolation.sh
```

### Manual Checks

```bash
# Verify staging services are running
docker compose -f infra/docker/compose/docker-compose.prod.yml ps

# Check staging database
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec postgres_staging psql -U exam_user_staging -d exam_platform_staging -c "SELECT 1;"

# Test staging endpoints
curl https://staging.<DOMAIN>
curl https://api-staging.<DOMAIN>/health
```

## Security Considerations

### ✅ Implemented

- Separate secrets (JWT_SECRET_STAGING, AUTH_TOKEN_PEPPER_STAGING)
- Separate databases (no data mixing)
- Email shadow mode (no accidental emails)
- CORS isolation (staging domains only)
- Network isolation (internal only, no host ports)

### ⚠️ Shared Resources

- **Neo4j**: Staging can share Neo4j with production (read-only recommended)
- **Elasticsearch**: Staging uses separate index prefix (`platform_staging`)
- **Traefik**: Shared instance (but routes are isolated by domain)

## Troubleshooting

### Common Issues

1. **Staging not accessible**
   - Check DNS: `dig staging.<DOMAIN> +short`
   - Check Traefik logs: `docker logs exam_platform_traefik | grep staging`
   - Verify service labels: `docker inspect exam_platform_backend_staging | grep Labels`

2. **Database connection errors**
   - Verify postgres_staging is running: `docker ps | grep postgres_staging`
   - Check logs: `docker logs exam_platform_postgres_staging`
   - Test connection: `docker compose exec postgres_staging psql -U exam_user_staging -d exam_platform_staging`

3. **Migration errors**
   - Check current status: `docker compose run --rm backend_staging alembic current`
   - View history: `docker compose run --rm backend_staging alembic history`

## Best Practices

1. **Always use different secrets** for staging
2. **Never copy production data** to staging (use test data)
3. **Use shadow email mode** to prevent accidental emails
4. **Run isolation verification** after deployment
5. **Keep staging in sync** with production migrations
6. **Test staging thoroughly** before deploying to production

## Future Enhancements

Potential improvements:
- [ ] Automated staging data refresh from production snapshots
- [ ] Staging-specific feature flags
- [ ] Automated staging deployment from CI/CD
- [ ] Staging environment monitoring and alerts
- [ ] Staging database backup automation

## Related Documentation

- `infra/docker/compose/STAGING_DEPLOYMENT.md` - Quick deployment guide
- `docs/runbook.md` - Operations runbook (includes staging section)
- `infra/docker/compose/README_PROD.md` - Production deployment overview
