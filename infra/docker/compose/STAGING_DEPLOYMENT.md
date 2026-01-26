# Staging Environment Deployment Guide

## Quick Reference

### Prerequisites Checklist

- [ ] DNS records configured:
  - `staging.<DOMAIN>` → server IP
  - `api-staging.<DOMAIN>` → server IP
- [ ] Environment variables set (see `.env.staging.example`):
  - `DOMAIN`
  - `POSTGRES_PASSWORD_STAGING` (different from production)
  - `JWT_SECRET_STAGING` (different from production)
  - `AUTH_TOKEN_PEPPER_STAGING` (different from production)
  - Other staging-specific vars

### Initial Deployment

```bash
# 1. Start staging infrastructure
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d postgres_staging redis_staging

# 2. Wait for postgres_staging to be healthy
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  ps postgres_staging

# 3. Run database migrations
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  run --rm backend_staging alembic upgrade head

# 4. Start staging application services
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d backend_staging frontend_staging

# 5. Verify staging is accessible
curl https://staging.<DOMAIN>
curl https://api-staging.<DOMAIN>/health
```

### Update Staging

```bash
# Rebuild and restart staging backend
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d --build backend_staging

# Rebuild and restart staging frontend
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d --build frontend_staging

# If migrations needed:
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  run --rm backend_staging alembic upgrade head
```

### Stop Staging (Production Continues)

```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  stop backend_staging frontend_staging postgres_staging redis_staging
```

### Remove Staging (Keeps Data)

```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  rm -f backend_staging frontend_staging postgres_staging redis_staging
```

### Remove Staging (Destructive - Deletes Data)

```bash
# WARNING: This deletes all staging data
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  down -v postgres_staging redis_staging
```

## Environment Isolation

### Verify Isolation

```bash
# Check staging uses separate database
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec backend_staging env | grep DATABASE_URL
# Should show: postgres_staging:5432/exam_platform_staging

# Check staging uses separate Redis
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec backend_staging env | grep REDIS_URL
# Should show: redis_staging:6379

# Check staging uses different secrets
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec backend_staging env | grep -E "JWT_SECRET|AUTH_TOKEN_PEPPER"
# Should show _STAGING suffixed vars with different values
```

## Common Issues

### Staging Not Accessible

1. **Check DNS:**
   ```bash
   dig staging.<DOMAIN> +short
   dig api-staging.<DOMAIN> +short
   ```

2. **Check Traefik routers:**
   ```bash
   docker logs exam_platform_traefik | grep -i staging
   ```

3. **Check service labels:**
   ```bash
   docker inspect exam_platform_backend_staging | grep -A 20 Labels
   ```

### Database Connection Errors

```bash
# Verify postgres_staging is running
docker ps | grep postgres_staging

# Check logs
docker logs exam_platform_postgres_staging --tail=20

# Test connection
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec postgres_staging psql -U exam_user_staging -d exam_platform_staging -c "SELECT 1;"
```

### Migration Errors

```bash
# Check current migration status
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  run --rm backend_staging alembic current

# View migration history
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  run --rm backend_staging alembic history
```

## Smoke Tests

```bash
# Test production (should be unaffected)
curl -I https://<DOMAIN>
curl -I https://api.<DOMAIN>/health

# Test staging
curl -I https://staging.<DOMAIN>
curl -I https://api-staging.<DOMAIN>/health

# Test redirects
curl -I http://staging.<DOMAIN>
curl -I http://api-staging.<DOMAIN>

# Run full smoke test with staging
./infra/scripts/smoke-test-traefik.sh <DOMAIN> --staging
```
