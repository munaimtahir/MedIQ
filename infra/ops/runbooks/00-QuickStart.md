# Quick Start Runbook

**Purpose**: Fast reference for checking status, restarting services, and verifying health.

## Check Status

### Container Status

```bash
# Check all containers
docker compose ps

# Expected output: All services should show "Up" status
# Look for:
# - exam_platform_traefik_staging: Up
# - exam_platform_backend_staging: Up
# - exam_platform_frontend_staging: Up
# - exam_platform_postgres_staging: Up (healthy)
# - exam_platform_redis_staging: Up (healthy)
```

### Service Logs

```bash
# Backend logs (last 50 lines)
docker compose logs --tail=50 backend_staging

# Frontend logs (last 50 lines)
docker compose logs --tail=50 frontend_staging

# Traefik logs (last 50 lines)
docker compose logs --tail=50 traefik

# Follow logs in real-time
docker compose logs -f backend_staging
```

### Health Endpoints

```bash
# Backend health (should return 200)
curl -I https://<STAGING_DOMAIN>/api/v1/health
# Or if using subdomain:
curl -I https://api-<STAGING_DOMAIN>/v1/health

# Backend readiness (checks DB, Redis)
curl -I https://<STAGING_DOMAIN>/api/v1/ready
# Or:
curl -I https://api-<STAGING_DOMAIN>/v1/ready

# Frontend (should return 200)
curl -I https://<STAGING_DOMAIN>/

# Full health check with response body
curl https://<STAGING_DOMAIN>/api/v1/health
# Expected: {"status":"ok"}

# Full readiness check
curl https://<STAGING_DOMAIN>/api/v1/ready
# Expected: {"status":"ok","checks":{...},"request_id":"..."}
```

## Restart Services Safely

**Order**: Backend first, then frontend (to avoid frontend serving stale data while backend is down).

### Restart Backend

```bash
# Stop backend
docker compose stop backend_staging

# Start backend
docker compose start backend_staging

# Or restart in one command
docker compose restart backend_staging

# Wait for backend to be healthy (30 seconds)
sleep 30

# Verify backend is responding
curl -I https://<STAGING_DOMAIN>/api/v1/health
```

### Restart Frontend

```bash
# Stop frontend
docker compose stop frontend_staging

# Start frontend
docker compose start frontend_staging

# Or restart in one command
docker compose restart frontend_staging

# Wait for frontend to be ready (10 seconds)
sleep 10

# Verify frontend is responding
curl -I https://<STAGING_DOMAIN>/
```

### Restart All Services

```bash
# Restart all services (use with caution)
docker compose restart

# Wait for services to stabilize
sleep 45

# Verify all services
curl -I https://<STAGING_DOMAIN>/
curl -I https://<STAGING_DOMAIN>/api/v1/health
```

## Verify Health

### Quick Verification Checklist

After any intervention, verify:

1. **Containers are running**:
   ```bash
   docker compose ps | grep -E "(Up|healthy)"
   ```

2. **Backend health endpoint returns 200**:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://<STAGING_DOMAIN>/api/v1/health
   # Expected: 200
   ```

3. **Backend readiness endpoint returns 200**:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://<STAGING_DOMAIN>/api/v1/ready
   # Expected: 200 (or 503 if degraded, but should not be 500)
   ```

4. **Frontend returns 200**:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://<STAGING_DOMAIN>/
   # Expected: 200
   ```

5. **No error logs in last 30 seconds**:
   ```bash
   docker compose logs --since=30s backend_staging | grep -i error
   # Expected: No output (or only expected errors)
   ```

### Detailed Health Check

```bash
# Full health check script
#!/bin/bash
DOMAIN="<STAGING_DOMAIN>"

echo "Checking containers..."
docker compose ps

echo -e "\nChecking backend health..."
curl -s https://${DOMAIN}/api/v1/health | jq .

echo -e "\nChecking backend readiness..."
curl -s https://${DOMAIN}/api/v1/ready | jq .

echo -e "\nChecking frontend..."
curl -I https://${DOMAIN}/ | head -1

echo -e "\nChecking recent errors..."
docker compose logs --since=1m backend_staging | grep -i error | tail -5
```

## Common Issues

### Backend Not Responding

1. Check container status: `docker compose ps backend_staging`
2. Check logs: `docker compose logs --tail=100 backend_staging`
3. Check database connectivity: `docker compose exec backend_staging ping postgres_staging`
4. Restart backend: `docker compose restart backend_staging`

### Frontend Not Responding

1. Check container status: `docker compose ps frontend_staging`
2. Check logs: `docker compose logs --tail=100 frontend_staging`
3. Check backend connectivity: `docker compose exec frontend_staging ping backend_staging`
4. Restart frontend: `docker compose restart frontend_staging`

### All Services Down

1. Check Docker daemon: `docker ps`
2. Check disk space: `df -h`
3. Check memory: `free -h`
4. Restart all: `docker compose restart`
5. If still down, see [01-Incident-Checklist.md](./01-Incident-Checklist.md)

## Next Steps

- If health checks fail, proceed to [01-Incident-Checklist.md](./01-Incident-Checklist.md)
- For rollback procedures, see [02-Rollback.md](./02-Rollback.md)
- For database issues, see [03-Database.md](./03-Database.md)
