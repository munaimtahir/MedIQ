# Runbook

## Local Development Email (Mailpit)

### Mailpit Inbox
- **Web UI**: `http://localhost:8025`
- **SMTP Port**: `1025` (inside docker network: `mailpit:1025`)

### Configuration
- Email backend is configured via `EMAIL_BACKEND` environment variable:
  - `mailpit` or `smtp`: Uses SMTP provider (connects to Mailpit in dev)
  - `console`: Falls back to console logging (if Mailpit is unavailable)

### Testing Password Reset
1. Start Mailpit: `docker compose up -d mailpit`
2. Open Mailpit UI: `http://localhost:8025`
3. Trigger password reset from frontend or admin panel
4. Check Mailpit inbox for reset email with reset link

### Fallback Behavior
If Mailpit is not running or SMTP connection fails, the system automatically falls back to console provider, which logs emails to backend logs/console. - Operations Guide

## Overview

This runbook provides operational procedures, troubleshooting guides, and runbooks for common tasks and incidents.

## Table of Contents

1. [Deployment Procedures](#deployment-procedures)
2. [Common Operations](#common-operations)
3. [Troubleshooting](#troubleshooting)
4. [Incident Response](#incident-response)
5. [Maintenance Tasks](#maintenance-tasks)

---

## Deployment Procedures

### Initial Setup

#### Prerequisites

- Docker and Docker Compose installed
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
- PostgreSQL 15+ (if not using Docker)

#### First-Time Deployment

```bash
# 1. Clone repository
git clone <repository-url>
cd "New Exam Prep Site"

# 2. Start services with Docker Compose
docker-compose up --build -d

# 3. Verify services are running
docker-compose ps

# 4. Check logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres

# 5. Seed database (if needed)
curl -X POST http://localhost:8000/seed
```

#### Service URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432

---

### Update Deployment

#### Backend Update

```bash
# 1. Pull latest code
git pull

# 2. Rebuild and restart backend
docker-compose up -d --build backend

# 3. Verify health
curl http://localhost:8000/health

# 4. Check logs for errors
docker-compose logs -f backend
```

#### Frontend Update

```bash
# 1. Pull latest code
git pull

# 2. Rebuild and restart frontend
docker-compose up -d --build frontend

# 3. Verify frontend loads
curl http://localhost:3000

# 4. Check logs
docker-compose logs -f frontend
```

#### Database Migration (Docker)

Run migrations **inside the backend container** (the app uses Docker; pydantic, alembic, etc. are available there):

```bash
# From repo root
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend alembic upgrade head

# If multiple heads exist, upgrade to a specific revision, e.g. 043:
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend alembic upgrade 043

# Rollback if needed
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend alembic downgrade -1
```

#### Tests (Docker)

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend python -m pytest tests/ -v
```

---

## Traefik Reverse Proxy

### Overview

Traefik serves as the **only public entrypoint** (ports 80/443) for the production deployment:
- **Frontend**: `https://<DOMAIN>`
- **Backend API**: `https://api.<DOMAIN>`

All other services (PostgreSQL, Redis, Neo4j, etc.) are internal-only with no host port exposure.

### Prerequisites

1. **DNS Configuration** (required before deployment):
   - `A` or `AAAA` record: `<DOMAIN>` → server IP
   - `A` or `AAAA` record: `api.<DOMAIN>` → server IP
   
   Example:
   ```
   example.com.          A    192.0.2.1
   api.example.com.      A    192.0.2.1
   ```

2. **Environment Variables** (set on server):
   ```bash
   export DOMAIN=example.com
   export TRAEFIK_ACME_EMAIL=admin@example.com
   export POSTGRES_PASSWORD=<secure-password>
   export JWT_SECRET=<secure-secret>
   export AUTH_TOKEN_PEPPER=<secure-pepper>
   # ... other required vars from .env.example
   ```

### Deployment Steps

1. **Start all services:**
   ```bash
   docker compose -f infra/docker/compose/docker-compose.prod.yml up -d --build
   ```

2. **Verify Traefik is running:**
   ```bash
   docker logs exam_platform_traefik --tail=50
   ```

3. **Check certificate issuance:**
   ```bash
   # Traefik will automatically request Let's Encrypt certificates
   # Watch logs for ACME challenge completion
   docker logs exam_platform_traefik -f | grep -i acme
   ```

4. **Verify certificate storage:**
   ```bash
   docker exec exam_platform_traefik ls -la /letsencrypt/
   # Should see acme.json file
   ```

### Certificate Management

- **Storage**: Certificates stored in `traefik_letsencrypt` Docker volume at `/letsencrypt/acme.json`
- **Auto-renewal**: Traefik automatically renews certificates 30 days before expiry
- **Backup**: Backup the volume to preserve certificates:
  ```bash
  docker run --rm -v exam_platform_traefik_letsencrypt:/data -v $(pwd):/backup \
    alpine tar czf /backup/letsencrypt-backup.tar.gz -C /data .
  ```

### Troubleshooting

#### Issue: Certificates not issuing

**Symptoms:**
- `404` errors in Traefik logs for `/.well-known/acme-challenge/...`
- Certificate resolver errors

**Causes & Solutions:**

1. **DNS not configured:**
   ```bash
   # Verify DNS resolution
   dig <DOMAIN> +short
   dig api.<DOMAIN> +short
   # Both should return server IP
   ```

2. **Ports blocked:**
   ```bash
   # Verify ports 80/443 are open
   ss -tulpen | grep -E ':80|:443'
   # Only Traefik should be listening
   
   # Check firewall
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

3. **Wrong Host rule in labels:**
   - Verify `DOMAIN` env var matches DNS
   - Check Traefik logs for router registration:
     ```bash
     docker logs exam_platform_traefik | grep -i router
     ```

4. **ACME rate limiting:**
   - Let's Encrypt has rate limits (50 certs/week per domain)
   - If exceeded, wait or use staging endpoint for testing

#### Issue: Services not accessible

**Check router registration:**
```bash
docker logs exam_platform_traefik | grep -E "router|service"
```

**Verify service labels:**
```bash
docker inspect exam_platform_backend | grep -A 20 Labels
docker inspect exam_platform_frontend | grep -A 20 Labels
```

**Check network connectivity:**
```bash
# Traefik should be on both networks
docker network inspect exam_platform_edge | grep traefik
docker network inspect exam_platform_app | grep -E "traefik|backend|frontend"
```

#### Issue: HTTP not redirecting to HTTPS

**Verify redirect middleware:**
```bash
docker logs exam_platform_traefik | grep redirect-to-https
```

**Test redirect:**
```bash
curl -I http://<DOMAIN>
# Should return 308 Permanent Redirect with Location: https://...
```

#### Issue: Security headers missing

**Verify middleware is applied:**
```bash
curl -I https://api.<DOMAIN>/health | grep -i "strict-transport\|x-frame\|nosniff"
```

**Check middleware definition:**
```bash
docker inspect exam_platform_traefik | grep -A 10 sec-headers
```

### Access Logs

Traefik access logs are stored in JSON format:
```bash
# View logs
docker exec exam_platform_traefik tail -f /var/log/traefik/access.log | jq

# Search for specific requests
docker exec exam_platform_traefik grep "api.example.com" /var/log/traefik/access.log | jq
```

### Traefik Dashboard (Private - Localhost Only)

The Traefik dashboard is **NOT exposed publicly** and is bound to `127.0.0.1:8080` on the server only. Access is via **SSH tunnel** for security.

#### Why Dashboard is Private

- **Security**: Dashboard exposes internal routing configuration and service status
- **No authentication**: Traefik dashboard has no built-in auth (SSH provides the security layer)
- **Best practice**: Never expose management interfaces publicly

#### Access via SSH Tunnel

**From your local machine:**

1. **Create SSH tunnel:**
   ```bash
   ssh -L 8080:127.0.0.1:8080 <user>@<server_ip>
   ```
   
   This forwards your local port 8080 to the server's localhost:8080.

2. **Open dashboard in browser:**
   ```
   http://localhost:8080/dashboard/
   ```

3. **Keep SSH session open** while using the dashboard.

**Alternative (if local port 8080 is in use):**
```bash
# Use a different local port (e.g., 8081)
ssh -L 8081:127.0.0.1:8080 <user>@<server_ip>
# Then access: http://localhost:8081/dashboard/
```

#### Common Uses

- **Verify routers**: Check that all services are properly registered
- **View middlewares**: See which middlewares are applied to which routes
- **ACME certificate status**: Monitor Let's Encrypt certificate issuance and renewal
- **Service health**: View backend service health and load balancing
- **Request metrics**: See request rates and response times

#### Troubleshooting

**Issue: Dashboard not loading**

1. **Check Traefik is running:**
   ```bash
   docker ps | grep traefik
   docker logs exam_platform_traefik --tail=50
   ```

2. **Verify entrypoint is bound to localhost:**
   ```bash
   # On server
   ss -tulpen | grep 8080
   # Should show: LISTEN on 127.0.0.1:8080
   ```

3. **Check router is configured:**
   ```bash
   docker inspect exam_platform_traefik | grep -A 10 "traefik-dashboard"
   ```

**Issue: SSH tunnel connection refused**

1. **Verify SSH access to server:**
   ```bash
   ssh <user>@<server_ip> "echo 'SSH works'"
   ```

2. **Check Traefik container is accessible from host:**
   ```bash
   # On server
   curl http://127.0.0.1:8080/dashboard/
   # Should return HTML
   ```

3. **Verify entrypoint configuration:**
   ```bash
   docker exec exam_platform_traefik cat /etc/traefik/traefik.yml | grep -A 2 traefik
   ```

**Issue: Port already in use (local machine)**

If local port 8080 is already in use:
```bash
# Use a different local port
ssh -L 8081:127.0.0.1:8080 <user>@<server_ip>
# Access via: http://localhost:8081/dashboard/
```

**Issue: Cannot access from external machine**

This is **expected behavior**. The dashboard is intentionally not accessible from the internet. You **must** use SSH tunnel:
```bash
# This should fail (connection refused/timeout)
curl http://<server_ip>:8080
# This is correct - dashboard is localhost-only
```

### Request ID Propagation

FastAPI generates `X-Request-ID` headers. Traefik passes these through automatically. Verify:
```bash
curl -v https://api.<DOMAIN>/health 2>&1 | grep -i request-id
```

### Health Checks

**Traefik health:**
```bash
docker ps | grep traefik
docker logs exam_platform_traefik --tail=20
```

**Backend health (via Traefik):**
```bash
curl https://api.<DOMAIN>/health
```

**Frontend health:**
```bash
curl -I https://<DOMAIN>
```

### Common Commands

```bash
# Restart Traefik
docker compose -f infra/docker/compose/docker-compose.prod.yml restart traefik

# View real-time logs
docker logs exam_platform_traefik -f

# Check certificate expiry
docker exec exam_platform_traefik cat /letsencrypt/acme.json | jq '.letsencrypt.Certificates[].domain'

# Force certificate renewal (if needed)
docker compose -f infra/docker/compose/docker-compose.prod.yml restart traefik
```

### Security Notes

- **Dashboard**: Not exposed publicly (security best practice)
- **Docker Socket**: Mounted read-only (`:ro`)
- **Security Headers**: Applied at edge (defense-in-depth with app-level headers)
- **Internal Services**: No host port exposure (only accessible via Docker networks)
- **HTTPS Only**: HTTP automatically redirects to HTTPS

---

## Staging Environment

### Overview

Staging environment runs on the **same server** as production but is completely isolated:
- **Separate containers**: `backend_staging`, `frontend_staging`
- **Separate databases**: `postgres_staging`, `redis_staging`
- **Separate domains**: `staging.<DOMAIN>`, `api-staging.<DOMAIN>`
- **Separate secrets**: Different JWT secrets, token peppers, etc.

### DNS Configuration

**Required DNS records:**
```
staging.<DOMAIN>          A    <server-ip>
api-staging.<DOMAIN>      A    <server-ip>
```

### Environment Variables

**Create `.env.staging` file** (copy from `.env.staging.example`):
```bash
# Critical: Use DIFFERENT secrets from production
export DOMAIN=example.com
export POSTGRES_PASSWORD_STAGING=<different-from-prod>
export JWT_SECRET_STAGING=<different-from-prod>
export AUTH_TOKEN_PEPPER_STAGING=<different-from-prod>
# ... see .env.staging.example for full list
```

### Deployment

#### Initial Staging Setup

1. **Set environment variables:**
   ```bash
   # Load staging env vars
   source .env.staging
   ```

2. **Start staging services:**
   ```bash
   # Start only staging services (production remains untouched)
   docker compose -f infra/docker/compose/docker-compose.prod.yml \
     up -d postgres_staging redis_staging backend_staging frontend_staging
   ```

3. **Run database migrations:**
   ```bash
   # Run migrations on staging database
   docker compose -f infra/docker/compose/docker-compose.prod.yml \
     run --rm backend_staging alembic upgrade head
   ```

4. **Verify staging is accessible:**
   ```bash
   curl https://staging.<DOMAIN>
   curl https://api-staging.<DOMAIN>/health
   ```

#### Update Staging (Without Affecting Production)

```bash
# Rebuild and restart staging backend only
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d --build backend_staging

# Rebuild and restart staging frontend only
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d --build frontend_staging

# Restart all staging services
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  restart backend_staging frontend_staging
```

### Database Migrations

**Run migrations on staging:**
```bash
# One-off migration
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  run --rm backend_staging alembic upgrade head

# Or if backend entrypoint runs migrations automatically, just restart:
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  restart backend_staging
```

**Rollback staging migration:**
```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  run --rm backend_staging alembic downgrade -1
```

### Staging Data Management

**Reset staging database:**
```bash
# Drop and recreate staging database
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec postgres_staging psql -U exam_user_staging -d postgres \
  -c "DROP DATABASE IF EXISTS exam_platform_staging;"
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec postgres_staging psql -U exam_user_staging -d postgres \
  -c "CREATE DATABASE exam_platform_staging;"

# Run migrations
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  run --rm backend_staging alembic upgrade head
```

**Copy production data to staging (if needed):**
```bash
# WARNING: Only do this if you need to test with production-like data
# Export from production
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec postgres pg_dump -U exam_user exam_platform > prod_dump.sql

# Import to staging
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec -T postgres_staging psql -U exam_user_staging exam_platform_staging < prod_dump.sql
```

### Tear Down Staging

**Stop staging services (production continues running):**
```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  stop backend_staging frontend_staging postgres_staging redis_staging
```

**Remove staging containers (keeps volumes):**
```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  rm -f backend_staging frontend_staging postgres_staging redis_staging
```

**Remove staging containers AND volumes (destructive):**
```bash
# WARNING: This deletes all staging data
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  down -v postgres_staging redis_staging
```

### Isolation Verification

**Verify staging is isolated from production:**
```bash
# Check staging backend can't access production database
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec backend_staging psql $DATABASE_URL -c "SELECT current_database();"
# Should show: exam_platform_staging

# Check staging uses separate Redis
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec backend_staging redis-cli -u $REDIS_URL ping
# Should connect to redis_staging, not redis
```

### Staging URLs

- **Frontend**: `https://staging.<DOMAIN>`
- **Backend API**: `https://api-staging.<DOMAIN>`
- **Health Check**: `https://api-staging.<DOMAIN>/health`

### Troubleshooting

#### Issue: Staging services not accessible

**Check Traefik routers:**
```bash
docker logs exam_platform_traefik | grep -i "staging\|api-staging"
```

**Verify DNS:**
```bash
dig staging.<DOMAIN> +short
dig api-staging.<DOMAIN> +short
```

**Check service labels:**
```bash
docker inspect exam_platform_backend_staging | grep -A 20 Labels
docker inspect exam_platform_frontend_staging | grep -A 20 Labels
```

#### Issue: Staging database connection errors

**Verify postgres_staging is running:**
```bash
docker ps | grep postgres_staging
docker logs exam_platform_postgres_staging --tail=20
```

**Test connection:**
```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec postgres_staging psql -U exam_user_staging -d exam_platform_staging -c "SELECT 1;"
```

#### Issue: Staging using production secrets

**Verify environment variables:**
```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  exec backend_staging env | grep -E "JWT_SECRET|AUTH_TOKEN_PEPPER|DATABASE_URL"
# Should show _STAGING suffixed vars with different values
```

### Staging Access Protection (Basic Auth)

Staging environments are protected with Traefik Basic Authentication to prevent public access.

#### Generate Basic Auth Credentials

**On Linux:**
```bash
# Install htpasswd (if not already installed)
sudo apt-get install apache2-utils  # Debian/Ubuntu
# or
sudo yum install httpd-tools         # RHEL/CentOS

# Generate bcrypt hash
htpasswd -nbB <USERNAME> <PASSWORD>
# Example:
htpasswd -nbB staging_user mySecurePassword123
# Output: staging_user:$2y$10$abc123def456...
```

**On macOS:**
```bash
# htpasswd is usually available via Homebrew
brew install httpd
htpasswd -nbB <USERNAME> <PASSWORD>
```

**On Windows (using Docker):**
```bash
# Use Docker to run htpasswd
docker run --rm httpd:alpine htpasswd -nbB <USERNAME> <PASSWORD>
```

#### Configure Basic Auth

1. **Set environment variable:**
   ```bash
   # In .env.staging or server environment
   export STAGING_BASIC_AUTH_USERS="staging_user:\$2y\$10\$abc123def456..."
   # Note: Escape $ signs if setting in shell, or use quotes in .env file
   ```

2. **Optional: Add IP Allowlist:**
   ```bash
   # Only allow specific IPs (in addition to Basic Auth)
   export STAGING_ALLOW_IPS="1.2.3.4/32,5.6.7.0/24"
   # Leave empty to allow all IPs (Basic Auth only)
   ```

3. **Restart Traefik to apply changes:**
   ```bash
   docker compose -f infra/docker/compose/docker-compose.prod.yml restart traefik
   ```

#### Enable/Disable Protection

**To disable Basic Auth (temporarily):**
```bash
# Unset the environment variable
unset STAGING_BASIC_AUTH_USERS
# Or set to empty in .env.staging
STAGING_BASIC_AUTH_USERS=

# Restart Traefik
docker compose -f infra/docker/compose/docker-compose.prod.yml restart traefik
```

**To re-enable:**
```bash
# Set the environment variable again
export STAGING_BASIC_AUTH_USERS="staging_user:\$2y\$10\$..."
docker compose -f infra/docker/compose/docker-compose.prod.yml restart traefik
```

#### Accessing Staging

**Via Browser:**
- Navigate to `https://staging.<DOMAIN>` or `https://api-staging.<DOMAIN>`
- Browser will prompt for username and password
- Enter credentials configured in `STAGING_BASIC_AUTH_USERS`

**Via curl:**
```bash
# Without credentials (will get 401)
curl -I https://staging.<DOMAIN>

# With credentials
curl -I -u staging_user:mySecurePassword123 https://staging.<DOMAIN>

# API endpoint
curl -I -u staging_user:mySecurePassword123 https://api-staging.<DOMAIN>/health
```

#### Troubleshooting Basic Auth

**Issue: 401 Unauthorized even with correct credentials**

1. **Check hash format:**
   ```bash
   # Verify the hash is properly escaped in environment
   docker compose -f infra/docker/compose/docker-compose.prod.yml \
     exec traefik env | grep STAGING_BASIC_AUTH_USERS
   ```

2. **Check Traefik logs:**
   ```bash
   docker logs exam_platform_traefik | grep -i "auth\|staging"
   ```

3. **Verify middleware is applied:**
   ```bash
   docker inspect exam_platform_traefik | grep -A 5 "staging-auth"
   ```

**Issue: Wrong hash format**

- Ensure you're using bcrypt (`-B` flag in htpasswd)
- Hash must start with `$2y$` or `$2a$`
- Escape `$` signs if setting in shell: `\$2y\$10\$...`
- In `.env` files, quotes are usually sufficient

**Issue: Basic Auth not working**

- Verify `STAGING_BASIC_AUTH_USERS` is set in Traefik container environment
- Check that staging routers include `staging-auth@docker` in middlewares
- Restart Traefik after changing environment variables
- If `STAGING_BASIC_AUTH_USERS` is empty, Traefik will fail to create the middleware and staging routers will not work

**Issue: Want to add IP allowlist**

If you want to add IP allowlist in addition to Basic Auth:

1. Set `STAGING_ALLOW_IPS` environment variable:
   ```bash
   export STAGING_ALLOW_IPS="1.2.3.4/32,5.6.7.0/24"
   ```

2. Manually update staging router labels in `docker-compose.prod.yml`:
   ```yaml
   # Change from:
   - "traefik.http.routers.api-staging.middlewares=staging-auth@docker,sec-headers@docker,compress@docker"
   # To:
   - "traefik.http.routers.api-staging.middlewares=staging-ip@docker,staging-auth@docker,sec-headers@docker,compress@docker"
   ```

3. Do the same for `frontend-staging` router

4. Restart Traefik:
   ```bash
   docker compose -f infra/docker/compose/docker-compose.prod.yml restart traefik
   ```

### Security Notes

- ✅ **Separate secrets**: Staging uses different JWT secrets and token peppers
- ✅ **Separate databases**: No risk of staging affecting production data
- ✅ **Email safety**: Staging uses shadow mode or disabled email
- ✅ **CORS isolation**: Staging CORS only allows staging domains
- ✅ **No host ports**: Staging services only accessible via Traefik
- ✅ **Basic Auth protection**: Staging requires authentication (not public)
- ⚠️ **Shared Neo4j/Elasticsearch**: Staging can share these (read-only recommended)

---

## Production Performance Hardening

### Overview

The platform is hardened for **zero-lag, predictable latency** under exam-time load spikes. Hardening focuses on:
- **Edge layer** (Traefik): Timeouts, connection limits
- **Application layer** (FastAPI): Worker model, concurrency limits
- **Database layer** (Postgres): Pool sizing, indexes
- **Cache layer** (Redis): Fast timeouts, graceful degradation
- **Container runtime**: CPU/memory limits

### Traefik Edge Hardening

**Timeouts** (protect against slow clients):
- Read timeout: 15s
- Write timeout: 15s
- Idle timeout: 60s

**Connection Limits**:
- Inflight request limit: 100 concurrent per IP
- Applied to: `api` and `api-staging` routers
- Prevents backend overload from connection storms

**Configuration**: Set in `infra/traefik/traefik.yml` and `docker-compose.prod.yml` labels.

### FastAPI Application Hardening

**Worker Model**:
- **Uvicorn workers**: `(2 * CPU cores) + 1` formula
- Default: 5 workers (for 1.5 CPU container)
- Override via `UVICORN_WORKERS` environment variable

**Concurrency Limits**:
- `--limit-concurrency=200`: Max concurrent requests per worker
- `--limit-max-requests=10000`: Graceful worker recycling (prevents memory leaks)
- `--timeout-keep-alive=5`: Keep-alive timeout

**Configuration**:
```bash
# In docker-compose.prod.yml or .env
UVICORN_WORKERS=5
UVICORN_TIMEOUT_KEEP_ALIVE=5
UVICORN_LIMIT_CONCURRENCY=200
UVICORN_LIMIT_MAX_REQUESTS=10000
```

**Verification**:
```bash
# Check worker count
docker exec exam_platform_backend ps aux | grep uvicorn

# Check process count (should be workers + 1 master)
docker exec exam_platform_backend ps aux | grep -c uvicorn
```

### PostgreSQL Database Hardening

**Connection Pool** (SQLAlchemy):
- `pool_size=10`: Base pool size (increased from 5)
- `max_overflow=10`: Additional connections beyond pool_size
- `pool_timeout=30`: Seconds to wait for connection
- `pool_pre_ping=True`: Verify connections before use (reconnect on stale)

**Configuration**: Set in `backend/app/db/engine.py` (hardcoded for production safety).

**Shared Buffers** (Postgres):
- Set to 25% of container memory limit
- For 2GB limit: `shared_buffers=512MB`
- Configured via `POSTGRES_SHARED_BUFFERS` environment variable

**Index Audit**:
Critical indexes verified:
- ✅ `test_sessions(user_id, created_at)` - User attempt history
- ✅ `session_answers(session_id)` - Answer lookups
- ✅ `questions(block_id, theme_id)` - Question filtering
- ✅ `revision_queue(user_id, due_at, status)` - Revision scheduling
- ✅ `user_theme_mastery(user_id, theme_id)` - Mastery lookups
- ✅ `attempt_events(user_id, event_ts)` - Analytics queries

**Missing Index Check**:
```bash
# On server, check for missing indexes
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
SELECT tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename IN ('test_sessions', 'session_answers', 'questions', 'revision_queue', 'user_theme_mastery')
ORDER BY tablename, indexname;
"
```

### Redis Hardening

**Timeouts** (fast fail):
- `socket_connect_timeout=1`: Fast fail on connect
- `socket_timeout=1`: Fast fail on operations
- Prevents slow Redis from blocking requests

**Graceful Degradation**:
- Rate limiting: Fail-open if Redis unavailable (logs warning)
- Token blacklist: Falls back to DB checks if Redis unavailable
- Circuit breaker pattern: Degrades gracefully, never blocks requests

**Configuration**: Set in `backend/app/core/redis_client.py`.

### Container Resource Limits

**Backend**:
- CPU: 1.5 cores (limit), 0.5 cores (reservation)
- Memory: 1GB (limit), 512MB (reservation)
- File descriptors: 65535 (soft/hard)

**Frontend**:
- CPU: 0.5 cores (limit), 0.25 cores (reservation)
- Memory: 512MB (limit), 256MB (reservation)

**Postgres**:
- Memory: 2GB (limit), 1GB (reservation)
- Shared buffers: 512MB (25% of limit)

**Configuration**: Set in `docker-compose.prod.yml` via `deploy.resources`.

### Exam Mode

**Purpose**: Disable heavy operations during exam spikes to prioritize student-facing requests. Exam Mode is a **database-backed runtime flag** that can be toggled via the admin UI without requiring backend restarts or environment variable changes.

**Key Features**:
- **Reversible**: Can be enabled/disabled instantly via admin UI
- **Auditable**: All toggles are logged with who/when/why
- **Safe under load**: Uses cached reads (10s TTL) to avoid database blocking
- **Non-disruptive**: Active student sessions are unaffected (snapshot at creation)

**When to Enable**:
- During scheduled exam windows
- When experiencing high concurrent user load
- Before known traffic spikes
- During maintenance windows to prevent background jobs from interfering

**What Gets Blocked** (when Exam Mode is enabled):
- Heavy analytics recompute jobs (BKT parameter recomputation)
- Bulk question imports (non-dry-run)
- IRT calibration runs
- Rank prediction runs
- Email outbox draining
- Notification broadcasts
- Search reindexing (nightly manual triggers)
- Warehouse exports (Snowflake)
- Graph rebuilds (Neo4j sync/rebuild)

**What Remains Available** (always allowed):
- Student session creation (`POST /v1/sessions`)
- Answer submissions (`POST /v1/sessions/{id}/answer`)
- Session submission (`POST /v1/sessions/{id}/submit`)
- Authentication flows (login, signup, password reset)
- Read-only endpoints (analytics viewing, question browsing)
- Revision queue reads

**Enable via Admin UI**:
1. Navigate to **Admin → Settings → System** tab
2. Find the **Exam Mode** card
3. Click **"Enable"** button
4. In the confirmation modal:
   - Type the exact phrase: **"ENABLE EXAM MODE"**
   - Provide a reason (minimum 10 characters)
   - Click **"Confirm"**

**Enable via API**:
```bash
curl -X POST https://api.<DOMAIN>/v1/admin/system/exam-mode \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "confirmation_phrase": "ENABLE EXAM MODE",
    "reason": "Scheduled exam window starting at 9:00 AM. Blocking heavy operations to prioritize student traffic."
  }'
```

**Disable via Admin UI**:
1. Navigate to **Admin → Settings → System** tab
2. Find the **Exam Mode** card
3. Click **"Disable"** button
4. In the confirmation modal:
   - Type the exact phrase: **"DISABLE EXAM MODE"**
   - Provide a reason (minimum 10 characters)
   - Click **"Confirm"**

**Disable via API**:
```bash
curl -X POST https://api.<DOMAIN>/v1/admin/system/exam-mode \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false,
    "confirmation_phrase": "DISABLE EXAM MODE",
    "reason": "Exam window completed. Resuming normal operations."
  }'
```

**Check Current Status**:
```bash
# Via API
curl -X GET https://api.<DOMAIN>/v1/admin/system/exam-mode \
  -H "Authorization: Bearer <admin_token>"

# Response includes:
# {
#   "enabled": true,
#   "updated_at": "2025-01-25T09:00:00Z",
#   "updated_by": { "id": "...", "email": "admin@example.com" },
#   "reason": "Scheduled exam window",
#   "source": "db"
# }
```

**Via Admin UI**: The Exam Mode card in **Admin → Settings → System** shows:
- Current state (ACTIVE/INACTIVE badge)
- Last updated timestamp
- Updated by (user email)
- Reason for last change

**Session Snapshot Behavior**:
- When a session is created, the current Exam Mode state is **snapshot** into `test_sessions.exam_mode_at_start`
- This ensures that **changing Exam Mode mid-exam does not affect active sessions**
- Answer and submit endpoints do **not** re-check Exam Mode; they rely on the snapshot
- This guarantees consistent behavior throughout a session's lifetime

**Verification**:
```sql
-- Check current Exam Mode state
SELECT key, value, updated_at, updated_by, reason
FROM system_flags
WHERE key = 'EXAM_MODE';

-- Check which sessions were created during Exam Mode
SELECT id, user_id, exam_mode_at_start, created_at
FROM test_sessions
WHERE exam_mode_at_start = true
ORDER BY created_at DESC
LIMIT 10;
```

**Caching & Performance**:
- Exam Mode state is cached in-memory with a 10-second TTL (configurable via `SYSTEM_FLAGS_CACHE_TTL_SECONDS`)
- Cache is automatically refreshed after admin toggles
- If database read fails, system falls back to last known cached value (defaults to `false` if never loaded)
- This ensures Exam Mode checks never block requests or cause cascading failures

**Error Responses**:
When Exam Mode is active and a blocked endpoint is called:
```json
{
  "error": {
    "code": "EXAM_MODE_ACTIVE",
    "message": "Action blocked during exam mode",
    "details": {
      "action": "bkt_recompute"
    }
  }
}
```
HTTP Status: **423 Locked**

**Audit Trail**:
All Exam Mode toggles are logged in the audit log:
- Event type: `EXAM_MODE_CHANGED`
- Includes `before` and `after` states
- Includes `reason` and `updated_by` user
- Query audit log:
```sql
SELECT event_type, created_at, actor_user_id, reason, before, after
FROM audit_log
WHERE event_type = 'EXAM_MODE_CHANGED'
ORDER BY created_at DESC
LIMIT 20;
```

**Troubleshooting**:

**Issue: Exam Mode toggle not working**
- Verify you have ADMIN role
- Check admin freeze is not active (`GET /v1/admin/security/runtime`)
- Verify confirmation phrase matches exactly (case-sensitive)
- Check audit log for errors

**Issue: Blocked endpoint still accessible**
- Verify Exam Mode is actually enabled: `GET /v1/admin/system/exam-mode`
- Check endpoint has `require_not_exam_mode` dependency applied
- Verify cache TTL hasn't expired (should refresh within 10s)

**Issue: Session behavior changed mid-exam**
- This should **never happen** due to snapshot mechanism
- Verify `exam_mode_at_start` column is set correctly on session creation
- Check that answer/submit endpoints do not call `is_exam_mode()` directly

**Legacy Environment Variable**:
The `EXAM_MODE` environment variable is **deprecated** and kept only for backward compatibility. The database-backed `system_flags.EXAM_MODE` is now the **source of truth**. Any code checking `settings.EXAM_MODE` should be updated to use `is_exam_mode()` from `app.system.flags`.

### Health & Readiness Endpoints

**`/health`** (Liveness):
- Shallow check: Process alive only
- Returns: `200 OK` if API is running
- Used by: Container orchestrators

**`/ready`** (Readiness):
- Deep check: Dependencies available
- Checks:
  - Database: `SELECT 1` ping
  - Redis: Optional ping (non-blocking)
- Returns:
  - `200 OK`: All checks passed
  - `503 Service Unavailable`: Critical dependency down
- Used by: Traefik health checks, load balancers

**Traefik Integration**:
Traefik should route only to containers that pass readiness checks. Configure health check labels if needed.

### Observability Signals

**Request Duration**:
- Logged in `X-Response-Time-ms` header
- Structured logs: `total_ms` field
- Slow request warnings: `>500ms` (warn), `>1500ms` (error)

**Database Query Duration**:
- Logged in `X-DB-Time-ms` header
- Slow SQL warnings: `>100ms` (warn), `>300ms` (error)
- Top 5 slow queries tracked per request

**Query Count**:
- Logged in `X-DB-Queries` header
- Helps identify N+1 query issues

**Verification**:
```bash
# Check response headers
curl -I https://api.<DOMAIN>/health | grep -i "x-response-time\|x-db"

# Check logs for slow requests
docker logs exam_platform_backend --tail=100 | grep -i "slow\|warn\|error" | grep -i "request\|sql"
```

### Baseline Performance Targets

**Expected Latency** (under normal load):
- Health check: `<50ms` (p95)
- Session create: `<200ms` (p95)
- Answer submit: `<100ms` (p95)
- Session submit: `<300ms` (p95)

**Under Exam-Time Load** (50 concurrent users):
- No 5xx errors
- p95 latency: `<500ms` (API endpoints)
- No database connection exhaustion
- No cascading failures

### Load Testing

**Baseline Test**:
```bash
# Single request latency
curl -w "%{time_total}\n" -o /dev/null -s https://api.<DOMAIN>/health
```

**Concurrent Load Test** (using `hey` or `k6`):
```bash
# Install hey: go install github.com/rakyll/hey@latest

# Test session answer submits (50 concurrent users, 100 requests each)
hey -n 100 -c 50 -m POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question_id":"...","selected_index":0}' \
  https://api.<DOMAIN>/v1/sessions/<session_id>/answer
```

**Expected Results**:
- No 5xx errors
- p95 < 500ms
- All requests complete successfully

### Troubleshooting Performance Issues

**Issue: High latency**

1. **Check database pool exhaustion**:
   ```bash
   # On server
   docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
   SELECT count(*) as active_connections 
   FROM pg_stat_activity 
   WHERE datname = 'exam_platform';
   "
   # Should be < pool_size + max_overflow (20)
   ```

2. **Check slow SQL queries**:
   ```bash
   docker logs exam_platform_backend --tail=500 | grep "slow_sql"
   ```

3. **Check request timing**:
   ```bash
   docker logs exam_platform_backend --tail=500 | grep "total_ms" | grep -E "warn|error"
   ```

**Issue: Connection timeouts**

1. **Check Traefik connection limits**:
   ```bash
   docker logs exam_platform_traefik --tail=100 | grep -i "limit\|429"
   ```

2. **Check backend worker count**:
   ```bash
   docker exec exam_platform_backend ps aux | grep uvicorn | wc -l
   # Should match UVICORN_WORKERS + 1
   ```

3. **Check container resource usage**:
   ```bash
   docker stats exam_platform_backend --no-stream
   # Check CPU and memory usage
   ```

**Issue: Database connection errors**

1. **Verify pool configuration**:
   ```bash
   # Check engine.py has correct pool_size, max_overflow, pool_timeout
   docker exec exam_platform_backend cat app/db/engine.py | grep pool
   ```

2. **Check active connections**:
   ```bash
   docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
   SELECT count(*) FROM pg_stat_activity WHERE datname = 'exam_platform';
   "
   ```

3. **Check for connection leaks**:
   ```bash
   # Monitor connection count over time
   watch -n 1 'docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "SELECT count(*) FROM pg_stat_activity WHERE datname = '\''exam_platform'\'';"'
   ```

### Performance Monitoring Checklist

- [ ] Baseline latency measured (`/health` endpoint)
- [ ] Slow SQL queries logged (`>100ms` warn, `>300ms` error)
- [ ] Slow requests logged (`>500ms` warn, `>1500ms` error)
- [ ] Database pool size configured (10 base + 10 overflow)
- [ ] Redis timeouts configured (1s connect, 1s operation)
- [ ] Container limits set (CPU, memory, file descriptors)
- [ ] Traefik connection limits applied (100 inflight per IP)
- [ ] Uvicorn workers configured (5 default)
- [ ] Exam mode flag available (`EXAM_MODE=true/false`)

---

## Common Operations

### Algorithm Runtime Management

The platform provides a runtime kill switch system for managing algorithm versions. See [Algorithm Runtime Profiles & Kill Switch](../docs/algorithms.md#algorithm-runtime-profiles--kill-switch) in `docs/algorithms.md` for full details.

**Key Operations:**

1. **View Current Runtime Config:**
   ```bash
   curl -X GET http://localhost:8000/v1/admin/algorithms/runtime \
     -H "Authorization: Bearer <admin-token>"
   ```
   Response includes:
   - Active profile (V1_PRIMARY or V0_FALLBACK)
   - Per-module overrides (mastery, revision, difficulty, adaptive, mistakes, **irt**, **rank**, **graph_revision**)
   - Safe mode status (freeze_updates)
   - IRT effective state (shadow_enabled, active_allowed, frozen, override)
   - Rank effective state (mode, enabled_for_admin, enabled_for_student, frozen)
   - Graph revision effective state (mode, enabled_for_admin, enabled_for_student, frozen)

2. **Switch Algorithm Profile:**
   ```bash
   curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/switch \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <admin-token>" \
     -d '{
       "profile": "V0_FALLBACK",
       "overrides": {"irt": "v0"},
       "reason": "Rollback due to performance issues",
       "confirmation_phrase": "SWITCH TO V0_FALLBACK"
     }'
   ```
   **⚠️ POLICE MODE**: Requires typed confirmation phrase:
   - `"SWITCH TO V1_PRIMARY"` or `"SWITCH TO V0_FALLBACK"` for profile switches
   - `"APPLY OVERRIDES"` for override-only changes

3. **Freeze Updates (Emergency Safe Mode):**
   ```bash
   curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/freeze_updates \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <admin-token>" \
     -d '{
       "reason": "Emergency freeze due to data quality issues",
       "confirmation_phrase": "FREEZE UPDATES"
     }'
   ```
   **Effect:** All learning state writes are paused (including IRT calibration runs)

4. **Unfreeze Updates:**
   ```bash
   curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/unfreeze_updates \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <admin-token>" \
     -d '{
       "reason": "Data quality issues resolved",
       "confirmation_phrase": "UNFREEZE UPDATES"
     }'
   ```

**IRT-Specific Notes:**
- IRT module override: `"v0"` (disabled), `"v1"` (eligible if active), `"shadow"` (runs only)
- When `freeze_updates=true`, IRT calibration runs are blocked (status set to FAILED)
- IRT activation requires separate confirmation phrase: `"ACTIVATE IRT"` / `"DEACTIVATE IRT"`

**Rank-Specific Notes:**
- Rank module override: `"v0"` (disabled), `"v1"` (eligible if active), `"shadow"` (snapshots/runs only)
- When `freeze_updates=true`, rank snapshot computation is blocked (status set to `BLOCKED_FROZEN`)
- Rank activation requires separate confirmation phrase: `"ACTIVATE RANK"` / `"DEACTIVATE RANK"`

**Graph Revision-Specific Notes:**
- Graph revision module override: `"v0"` (disabled), `"v1"` (eligible if active), `"shadow"` (shadow plans/runs only)
- When `freeze_updates=true`, graph revision plan computation is blocked (returns None, not stored)
- Graph revision activation requires separate confirmation phrase: `"ACTIVATE GRAPH REVISION"` / `"DEACTIVATE GRAPH REVISION"`

---

### Database Operations

#### Backup Database

```bash
# Using Docker
docker-compose exec postgres pg_dump -U examplatform examplatform > backup_$(date +%Y%m%d).sql

# Or directly
pg_dump -U examplatform -h localhost examplatform > backup.sql
```

#### Restore Database

```bash
# Using Docker
docker-compose exec -T postgres psql -U examplatform examplatform < backup.sql

# Or directly
psql -U examplatform -h localhost examplatform < backup.sql
```

#### Reset Database

```bash
# WARNING: This deletes all data
docker-compose down -v
docker-compose up -d postgres
# Wait for postgres to be ready
curl -X POST http://localhost:8000/seed
```

#### Access Database Console

```bash
# Using Docker
docker-compose exec postgres psql -U examplatform examplatform

# Common queries
SELECT COUNT(*) FROM questions WHERE is_published = true;
SELECT COUNT(*) FROM attempt_sessions;
SELECT * FROM users;
```

---

### Service Management

#### Start All Services

```bash
docker-compose up -d
```

#### Stop All Services

```bash
docker-compose down
```

#### Restart Service

```bash
# Restart specific service
docker-compose restart backend
docker-compose restart frontend

# Restart all
docker-compose restart
```

#### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 backend
```

#### Check Service Status

```bash
# Service status
docker-compose ps

# Health checks
curl http://localhost:8000/health
curl http://localhost:3000
```

---

### User Management

#### Create Test User (Backend)

```python
# Access Python shell
docker-compose exec backend python

# In Python shell
from database import SessionLocal
from models import User

db = SessionLocal()
user = User(id="test-student", role="student")
db.add(user)
db.commit()
db.close()
```

#### List Users

```sql
-- In database console
SELECT id, role, created_at FROM users;
```

---

### IRT Calibration (Shadow)

IRT (Item Response Theory) calibration runs are **shadow/offline only**. They are never used for student-facing decisions unless `FEATURE_IRT_ACTIVE` is enabled.

**Runtime Framework:** IRT is governed by the algorithm runtime system. See [Algorithm Runtime Management](#algorithm-runtime-management) for details on profile switching, overrides, and freeze mode.

#### Trigger a calibration run

1. **Admin UI**: Go to **Admin → IRT (Shadow)**. Create a run via **POST /v1/admin/irt/runs** (use API docs at `/docs` or a REST client).
2. **API**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/irt/runs \
     -H "Authorization: Bearer <ADMIN_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "model_type": "IRT_2PL",
       "dataset_spec": {
         "time_min": "2024-01-01T00:00:00Z",
         "time_max": "2025-12-31T23:59:59Z",
         "split_strategy": "time",
         "split_config": { "train_ratio": 0.8 }
       },
       "seed": 42,
       "notes": "Optional run notes"
     }'
   ```
3. The run executes **synchronously** (create + calibrate). Monitor status via **GET /v1/admin/irt/runs** or the Admin IRT panel.

#### Where artifacts live

- **IRT artifacts**: `backend/artifacts/irt/<run_id>/`  
  - `summary.json`: Run summary, metrics, n_items, n_users.
- **Eval harness**: Each IRT run creates an **eval run** (suite `irt_2pl` or `irt_3pl`). Eval artifacts (e.g. reliability curve, report) follow the eval harness layout (see `docs/evaluation-harness.md`).

#### List runs and inspect metrics

- **GET** `/v1/admin/irt/runs?status=SUCCEEDED&model_type=IRT_2PL&limit=50`
- **GET** `/v1/admin/irt/runs/{id}` for full details and embedded metrics (logloss, Brier, ECE, stability, info curve).
- **GET** `/v1/admin/irt/runs/{id}/items?flag=low_discrimination` for flagged items.

### IRT Activation (Production Use)

**⚠️ CRITICAL**: IRT activation requires passing all 6 activation gates. Never activate IRT without proper evaluation.

**⚠️ POLICE MODE**: Activation and deactivation require typed confirmation phrases:
- **Activation**: `"ACTIVATE IRT"` (exact, case-insensitive)
- **Deactivation**: `"DEACTIVATE IRT"` (exact, case-insensitive)

These phrases must be provided in the `confirmation_phrase` field of the request body. Missing or incorrect phrases will result in a 400 error.

#### Step 1: Evaluate Activation Gates

After a calibration run succeeds, evaluate activation eligibility:

```bash
curl -X POST http://localhost:8000/api/v1/admin/irt/activation/evaluate \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "<calibration_run_id>",
    "policy_version": "v1"
  }'
```

**Response includes:**
- `eligible`: Boolean indicating if all gates passed
- `gates`: Array of gate results (name, passed, value, threshold, notes)
- `recommended_scope`: Recommended activation scope (usually "selection_only" initially)
- `recommended_model`: Recommended model type

**Check gate results:**
- All 6 gates must pass for eligibility
- Gate A: Data sufficiency (users, items, attempts)
- Gate B: Predictive superiority vs baseline
- Gate C: Calibration sanity (no parameter pathologies)
- Gate D: Parameter stability over time
- Gate E: Measurement precision (ability SE)
- Gate F: Coverage + fairness (subgroup checks)

#### Step 2: Activate (If Eligible)

**Only proceed if `eligible=true` and all gates passed.**

```bash
curl -X POST http://localhost:8000/api/v1/admin/irt/activation/activate \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "<calibration_run_id>",
    "scope": "selection_only",
    "model_type": "IRT_2PL",
    "reason": "All gates passed. Starting with selection_only for 2-week trial.",
    "confirmation_phrase": "ACTIVATE IRT"
  }'
```

**Scope options:**
- `"selection_only"`: IRT used for question selection only (recommended initial)
- `"scoring_only"`: IRT used for scoring only
- `"selection_and_scoring"`: IRT used for both (requires 2 consecutive weekly runs with improvements)

**Progressive rollout:**
1. Start with `"selection_only"` for 2 weeks
2. Monitor metrics and gate evaluations
3. Only promote to `"selection_and_scoring"` if:
   - Gate B improvements hold for 2 consecutive weekly runs
   - Gate D stability holds in both runs

#### Step 3: Deactivate (Kill-Switch)

**Always available for immediate rollback:**

```bash
curl -X POST http://localhost:8000/api/v1/admin/irt/activation/deactivate \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Performance regression detected. Rolling back to baseline.",
    "confirmation_phrase": "DEACTIVATE IRT"
  }'
```

**Effect:**
- Immediately sets `FEATURE_IRT_ACTIVE=false`
- Sets `FEATURE_IRT_SCOPE="none"`
- Creates audit event
- All student-facing endpoints fall back to baseline (BKT/FSRS/ELO/Adaptive)

#### Check Activation Status

```bash
curl -X GET http://localhost:8000/api/v1/admin/irt/activation/status \
  -H "Authorization: Bearer <admin_token>"
```

**Returns:**
- Current flags (active, scope, model, shadow)
- Latest decision (eligible, run_id, created_at)
- Last 10 activation events (audit trail)

#### Activation Audit Trail

All activation events are logged in `irt_activation_event`:
- `EVALUATED`: Gate evaluation performed
- `ACTIVATED`: IRT activated (includes confirmation phrase status in event details)
- `DEACTIVATED`: IRT deactivated (kill-switch, includes confirmation phrase status in event details)
- `ROLLED_BACK`: Previous activation rolled back

**Freeze Mode Impact:**
- When `freeze_updates=true` (see [Algorithm Runtime Management](#algorithm-runtime-management)), IRT calibration runs are blocked
- Runs will be set to FAILED status with error message: "Calibration blocked: freeze_updates mode is enabled. All learning state writes are paused."
- This prevents any IRT state mutations while in emergency safe mode

Each event includes:
- Previous and new state
- Run ID (if applicable)
- Policy version
- Reason
- Created by user ID
- Timestamp

**Query audit trail:**
```sql
SELECT event_type, created_at, reason, created_by_user_id
FROM irt_activation_event
ORDER BY created_at DESC
LIMIT 50;
```

#### Reproducibility

- Each run stores `dataset_spec` and `seed`. Same spec + same seed → same metrics/params within numerical tolerance.

---

### Rank Prediction (Shadow)

Rank prediction provides quantile-based percentile estimates for students within their cohort (e.g., year). Rank computations are **shadow/offline only** by default and are never used for student-facing decisions unless explicitly activated via runtime override and feature flags.

**Runtime Framework:** Rank is governed by the algorithm runtime system. See [Algorithm Runtime Management](#algorithm-runtime-management) for details on profile switching, overrides, and freeze mode.

#### Trigger a snapshot computation

1. **Admin UI**: Go to **Admin → Rank (Shadow)**. Create a run via **POST /v1/admin/rank/runs** (use API docs at `/docs` or a REST client).
2. **API**:
   ```bash
   curl -X POST http://localhost:8000/v1/admin/rank/runs \
     -H "Authorization: Bearer <ADMIN_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "cohort_key": "year:1",
       "dataset_spec": {
         "time_min": "2024-01-01T00:00:00Z",
         "time_max": "2025-12-31T23:59:59Z"
       },
       "notes": "Optional run notes"
     }'
   ```
3. The run executes **synchronously** (create + compute snapshots). Monitor status via **GET /v1/admin/rank/runs** or the Admin Rank panel.

#### Where snapshots live

- **Rank snapshots**: Stored in `rank_prediction_snapshot` table
  - `theta_proxy`: Ability proxy (Elo or mastery-weighted)
  - `predicted_percentile`: Percentile (0..1)
  - `band_low`, `band_high`: Uncertainty bands
  - `status`: `ok`, `insufficient_data`, `unstable`, `blocked_frozen`, `disabled`
- **Rank runs**: Stored in `rank_model_run` table
  - `metrics`: Coverage, stability, rank correlation
  - `status`: `QUEUED`, `RUNNING`, `DONE`, `FAILED`, `BLOCKED_FROZEN`, `DISABLED`

#### List runs and inspect snapshots

- **GET** `/v1/admin/rank/runs?status=DONE&cohort_key=year:1&limit=50`
- **GET** `/v1/admin/rank/runs/{id}` for full details and embedded metrics (coverage, stability, rank correlation).
- **GET** `/v1/admin/rank/snapshots?user_id=<uuid>&cohort_key=year:1&days=30` for user snapshots over time.

### Rank Activation (Production Use)

**⚠️ CRITICAL**: Rank activation requires passing all 3 activation gates. Never activate rank without proper evaluation.

**⚠️ POLICE MODE**: Activation and deactivation require typed confirmation phrases:
- **Activation**: `"ACTIVATE RANK"` (exact, case-insensitive)
- **Deactivation**: `"DEACTIVATE RANK"` (exact, case-insensitive)

These phrases must be provided in the `confirmation_phrase` field of the request body. Missing or incorrect phrases will result in a 400 error.

#### Step 1: Evaluate Activation Gates

After a rank run succeeds, evaluate activation eligibility:

```bash
curl -X GET "http://localhost:8000/v1/admin/rank/status?cohort_key=year:1" \
  -H "Authorization: Bearer <admin_token>"
```

**Response includes:**
- `eligible`: Boolean indicating if all gates passed
- `gates`: Array of gate results (name, passed, value, threshold, notes)
- Latest run summary with coverage and stability metrics

**Check gate results:**
- All 3 gates must pass for eligibility
- Gate A: Minimum cohort size (default: 100 users with `ok` status)
- Gate B: Coverage (default: ≥80% of users with `ok` status)
- Gate C: Stability (default: median abs percentile change ≤0.05 week-to-week)

#### Step 2: Activate (If Eligible)

**Only proceed if `eligible=true` and all gates passed.**

```bash
curl -X POST http://localhost:8000/v1/admin/rank/activate \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "cohort_key": "year:1",
    "reason": "All gates passed. Activating for analytics dashboards.",
    "confirmation_phrase": "ACTIVATE RANK"
  }'
```

**Effect:**
- Updates runtime config override `"rank": "v1"`
- Creates audit event in `rank_activation_event`
- Rank becomes available for admin analytics (still requires `rank.student_enabled` flag for student-facing endpoints)

**Note:** Even when activated, rank is intended for **analytics surfaces only**, not learning decisions (selection, scoring, difficulty updates).

#### Step 3: Deactivate (Kill-Switch)

**Always available for immediate rollback:**

```bash
curl -X POST http://localhost:8000/v1/admin/rank/deactivate \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Performance regression detected. Rolling back to shadow mode.",
    "confirmation_phrase": "DEACTIVATE RANK"
  }'
```

**Effect:**
- Immediately sets runtime override `"rank": "v0"`
- Creates audit event
- All rank computations disabled (no snapshots, no runs)

#### Check Activation Status

```bash
curl -X GET "http://localhost:8000/v1/admin/rank/status?cohort_key=year:1" \
  -H "Authorization: Bearer <admin_token>"
```

**Returns:**
- Current mode (v0, shadow, v1)
- Latest run summary (coverage, stability)
- Activation eligibility status
- Last activation event (if any)

#### Activation Audit Trail

All activation events are logged in `rank_activation_event`:
- `EVALUATED`: Gate evaluation performed
- `ACTIVATED`: Rank activated (includes confirmation phrase status in event details)
- `DEACTIVATED`: Rank deactivated (kill-switch, includes confirmation phrase status in event details)
- `ROLLED_BACK`: Previous activation rolled back

**Freeze Mode Impact:**
- When `freeze_updates=true` (see [Algorithm Runtime Management](#algorithm-runtime-management)), rank snapshot computation is blocked
- Snapshots will be set to `BLOCKED_FROZEN` status
- Runs will be set to `BLOCKED_FROZEN` status
- This prevents any rank state mutations while in emergency safe mode

Each event includes:
- Previous and new state
- Cohort key
- Reason
- Created by user ID
- Timestamp

**Query audit trail:**
```sql
SELECT event_type, created_at, reason, created_by_user_id, cohort_key
FROM rank_activation_event
ORDER BY created_at DESC
LIMIT 50;
```

#### Reproducibility

- Each snapshot stores `features_hash` for reproducibility
- Cohort key generation is deterministic (based on user's academic profile)
- Theta proxy computation follows a clear priority (Elo → mastery-weighted → zero)

---

### Graph-Aware Revision Planning (Shadow)

Graph-aware revision planning augments FSRS revision plans with prerequisite knowledge. Shadow plans are computed but **never affect student queues** unless explicitly activated via runtime override and feature flags.

**Runtime Framework:** Graph revision is governed by the algorithm runtime system. See [Algorithm Runtime Management](#algorithm-runtime-management) for details on profile switching, overrides, and freeze mode.

#### Prerequisite Edge Management

**Add prerequisite edge:**
```bash
curl -X POST http://localhost:8000/v1/admin/graph-revision/edges \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "from_theme_id": 1,
    "to_theme_id": 2,
    "weight": 1.0,
    "source": "manual",
    "confidence": null
  }'
```

**List edges:**
```bash
curl -X GET "http://localhost:8000/v1/admin/graph-revision/edges?is_active=true" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Update edge:**
```bash
curl -X PUT http://localhost:8000/v1/admin/graph-revision/edges/{edge_id} \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "weight": 0.8,
    "is_active": true
  }'
```

**Delete edge (soft delete):**
```bash
curl -X DELETE http://localhost:8000/v1/admin/graph-revision/edges/{edge_id} \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

#### Sync Prerequisites to Neo4j

**Trigger sync:**
```bash
curl -X POST http://localhost:8000/v1/admin/graph-revision/sync \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**List sync runs:**
```bash
curl -X GET http://localhost:8000/v1/admin/graph-revision/sync/runs \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Get sync run details:**
```bash
curl -X GET http://localhost:8000/v1/admin/graph-revision/sync/runs/{run_id} \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

#### Check Neo4j Health

```bash
curl -X GET http://localhost:8000/v1/admin/graph-revision/health \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Response includes:**
- `neo4j_available`: Boolean indicating Neo4j reachability
- `graph_stats`: Node count, edge count
- `cycle_check`: Cycle detection results
- `last_sync`: Last sync run details

#### View Shadow Plans

```bash
curl -X GET "http://localhost:8000/v1/admin/graph-revision/shadow-plans?user_id=<uuid>&days=7" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Response includes:**
- `baseline_count`: Number of baseline due themes
- `injected_count`: Number of prerequisite themes injected
- `plan_json`: Ordered list of plan items with explainability

### Graph Revision Activation (Production Use)

**⚠️ CRITICAL**: Graph revision activation requires passing all 3 activation gates. Never activate graph revision without proper evaluation.

**⚠️ POLICE MODE**: Activation and deactivation require typed confirmation phrases:
- **Activation**: `"ACTIVATE GRAPH REVISION"` (exact, case-insensitive)
- **Deactivation**: `"DEACTIVATE GRAPH REVISION"` (exact, case-insensitive)

These phrases must be provided in the `confirmation_phrase` field of the request body. Missing or incorrect phrases will result in a 400 error.

#### Step 1: Evaluate Activation Gates

Check activation eligibility:

```bash
curl -X GET http://localhost:8000/v1/admin/graph-revision/health \
  -H "Authorization: Bearer <admin_token>"
```

**Check gate results:**
- All 3 gates must pass for eligibility
- Gate A: Cycle check (no cycles detected)
- Gate B: Coverage (≥50% of themes have prerequisites)
- Gate C: Neo4j availability (currently available)

#### Step 2: Activate (If Eligible)

**Only proceed if all gates passed.**

```bash
curl -X POST http://localhost:8000/v1/admin/graph-revision/activate \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "All gates passed. Activating for prerequisite-aware revision planning.",
    "confirmation_phrase": "ACTIVATE GRAPH REVISION"
  }'
```

**Effect:**
- Updates runtime config override `"graph_revision": "v1"`
- Creates audit event in `graph_revision_activation_event`
- Graph revision becomes available for augmenting revision plans (still requires `graph_revision.active` flag for student-facing endpoints)

**Note:** Even when activated, graph revision **does not mutate FSRS state**; it only re-orders/selects items for today's plan, maintaining FSRS as the authoritative scheduler.

#### Step 3: Deactivate (Kill-Switch)

**Always available for immediate rollback:**

```bash
curl -X POST http://localhost:8000/v1/admin/graph-revision/deactivate \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Performance regression detected. Rolling back to baseline FSRS.",
    "confirmation_phrase": "DEACTIVATE GRAPH REVISION"
  }'
```

**Effect:**
- Immediately sets runtime override `"graph_revision": "v0"`
- Creates audit event
- All graph revision computations disabled (no shadow plans, no runs)

#### Activation Audit Trail

All activation events are logged in `graph_revision_activation_event`:
- `EVALUATED`: Gate evaluation performed
- `ACTIVATED`: Graph revision activated (includes confirmation phrase status in event details)
- `DEACTIVATED`: Graph revision deactivated (kill-switch, includes confirmation phrase status in event details)
- `ROLLED_BACK`: Previous activation rolled back

**Freeze Mode Impact:**
- When `freeze_updates=true` (see [Algorithm Runtime Management](#algorithm-runtime-management)), graph revision plan computation is blocked
- Plans will return `None` (not stored)
- Runs will be set to `BLOCKED_FROZEN` status
- This prevents any graph revision state mutations while in emergency safe mode

Each event includes:
- Previous and new state
- Reason
- Created by user ID
- Timestamp

**Query audit trail:**
```sql
SELECT event_type, created_at, reason, created_by_user_id
FROM graph_revision_activation_event
ORDER BY created_at DESC
LIMIT 50;
```

#### Reproducibility

- Prerequisite edge scoring is deterministic for given inputs and configuration
- Shadow plans store full explainability (reason codes, scores, source themes)
- Neo4j sync is idempotent (safe to run multiple times)

---

## Algorithm Runtime Kill Switch

### Overview

The algorithm kill switch allows instant, reversible switching between v1 algorithms (BKT/FSRS/ELO/Adaptive/Mistakes v1) and v0 algorithms (rules-based baseline) without disrupting active students.

**Key Features:**
- One-click admin toggle
- Reversible (can switch back and forth)
- Fully audited (all switches logged)
- Safe under load (sessions use snapshot config)
- No student disruption (state preserved via canonical tables)

### Current Runtime Configuration

**Check current profile:**
```bash
curl -X GET http://localhost:8000/v1/admin/algorithms/runtime \
  -H "Authorization: Bearer <admin_token>"
```

**Response includes:**
- `config.active_profile`: "V1_PRIMARY" or "V0_FALLBACK"
- `config.overrides`: Per-module overrides (if any)
- `config.safe_mode`: Freeze mode status
- `last_switch_events`: Last 10 switch events
- `bridge_job_health`: Bridge job status counts

### Switch Algorithm Profile

**Switch to V0_FALLBACK (fallback to baseline):**
```bash
curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/switch \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "V0_FALLBACK",
    "reason": "Performance regression detected, falling back to baseline"
  }'
```

**Switch back to V1_PRIMARY:**
```bash
curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/switch \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "V1_PRIMARY",
    "reason": "Issue resolved, returning to v1"
  }'
```

**Partial fallback (override specific modules):**
```bash
curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/switch \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "V1_PRIMARY",
    "overrides": {
      "adaptive": "v0"
    },
    "reason": "Adaptive bandit misbehaving, fallback to v0 rules"
  }'
```

### Emergency Freeze (Read-Only Mode)

**Enable freeze (no state mutations):**
```bash
curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/freeze_updates \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Emergency: Suspected data corruption, freezing all updates"
  }'
```

**Disable freeze:**
```bash
curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/unfreeze_updates \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Issue resolved, resuming normal operation"
  }'
```

### Session Continuity

**Critical Rule:** Sessions use the algorithm profile captured at creation time.

- Active sessions continue using their snapshot config
- New sessions after switch use new config
- No mid-session algorithm switching
- Learning updates during session use snapshot config

**Verify session snapshot:**
```sql
SELECT id, algo_profile_at_start, algo_overrides_at_start, created_at
FROM test_sessions
WHERE status = 'ACTIVE'
ORDER BY created_at DESC
LIMIT 10;
```

### Bridge Status

**Check bridge status for a user:**
```bash
curl -X GET "http://localhost:8000/v1/admin/algorithms/bridge/status?user_id=<uuid>" \
  -H "Authorization: Bearer <admin_token>"
```

**Check overall bridge health:**
```bash
curl -X GET http://localhost:8000/v1/admin/algorithms/bridge/status \
  -H "Authorization: Bearer <admin_token>"
```

### How Switching Works

1. **Admin triggers switch** → Profile updated in `algo_runtime_config`
2. **Audit event created** → Logged in `algo_switch_event`
3. **Active sessions unaffected** → Continue using snapshot config
4. **New sessions** → Use new profile
5. **Lazy bridging** → First request after switch triggers per-user bridge
6. **State preserved** → Canonical tables ensure no cold start

### Troubleshooting

**Issue: Students reporting "reset" after switch**
- Check if bridge jobs completed: `GET /v1/admin/algorithms/bridge/status`
- Verify canonical state tables populated: `SELECT * FROM user_mastery_state LIMIT 10;`
- Check bridge job logs for errors

**Issue: Switch not taking effect**
- Verify config updated: `GET /v1/admin/algorithms/runtime`
- Check if sessions are using snapshot (old sessions won't change)
- Verify router is being called (check logs)

**Issue: Performance degradation after switch**
- Check if safe mode enabled (freeze_updates)
- Verify bridge jobs not running (check `algo_state_bridge.status`)
- Monitor canonical state table sizes

---

## Algorithm Kill Switch - ALGO_BRIDGE_SPEC_v1

### Overview

The algorithm kill switch allows instant, reversible switching between v1 algorithms (BKT/FSRS/ELO/Bandit) and v0 algorithms (rule-based baseline) **without disrupting active students**.

**Key Features:**
- **Session Continuity**: Active sessions use snapshot config (no mid-session switching)
- **State Preservation**: `due_at` and `mastery_score` preserved across switches
- **Non-Trivial Initialization**: v1 algorithms initialize from canonical state, not default priors
- **Config-Driven**: All mappings follow ALGO_BRIDGE_SPEC_v1 (stored in `algo_bridge_config`)

### Current Runtime Configuration

**Check current profile:**
```bash
curl -X GET http://localhost:8000/v1/admin/algorithms/runtime \
  -H "Authorization: Bearer <admin_token>"
```

**Response includes:**
- `config.active_profile`: "V1_PRIMARY" or "V0_FALLBACK"
- `config.overrides`: Per-module overrides (if any)
- `config.safe_mode`: Freeze mode status
- `last_switch_events`: Last 10 switch events
- `bridge_job_health`: Bridge job status counts

### Switch to V0_FALLBACK

**Switch profile:**
```bash
curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/switch \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "V0_FALLBACK",
    "reason": "Performance regression detected, falling back to baseline"
  }'
```

**What Happens:**
1. Profile switched instantly in `algo_runtime_config`
2. Audit event created in `algo_switch_event`
3. Active sessions continue using snapshot (no change)
4. New sessions use V0_FALLBACK config
5. Lazy bridging triggered on first request per user

### Return to V1_PRIMARY

**Switch back:**
```bash
curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/switch \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "V1_PRIMARY",
    "reason": "Issue resolved, returning to v1"
  }'
```

**What Happens:**
1. Profile switched instantly
2. Active sessions continue using snapshot
3. New sessions use V1_PRIMARY config
4. Lazy bridging initializes BKT/FSRS/Bandit from canonical state

### Partial Fallback (Per-Module Overrides)

**Override specific modules:**
```bash
curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/switch \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "V1_PRIMARY",
    "overrides": {
      "adaptive": "v0"
    },
    "reason": "Adaptive bandit misbehaving, fallback to v0 rules"
  }'
```

### Emergency Freeze (Read-Only Mode)

**Enable freeze:**
```bash
curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/freeze_updates \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Emergency: Suspected data corruption, freezing all updates"
  }'
```

**Disable freeze:**
```bash
curl -X POST http://localhost:8000/v1/admin/algorithms/runtime/unfreeze_updates \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Issue resolved, resuming normal operation"
  }'
```

### Verify No Disruption

**Check session snapshots:**
```sql
SELECT id, algo_profile_at_start, algo_overrides_at_start, created_at, status
FROM test_sessions
WHERE status = 'ACTIVE'
ORDER BY created_at DESC
LIMIT 10;
```

**Check bridge status:**
```bash
curl -X GET "http://localhost:8000/v1/admin/algorithms/bridge/status?user_id=<uuid>" \
  -H "Authorization: Bearer <admin_token>"
```

**Verify canonical state:**
```sql
-- Check mastery continuity
SELECT user_id, theme_id, mastery_score, mastery_model, mastery_updated_at
FROM user_mastery_state
WHERE user_id = '<user_id>'
ORDER BY mastery_updated_at DESC
LIMIT 10;

-- Check revision continuity
SELECT user_id, theme_id, due_at, v0_interval_days, stability, difficulty
FROM user_revision_state
WHERE user_id = '<user_id>'
ORDER BY updated_at DESC
LIMIT 10;
```

### Bridge Configuration

**View bridge config:**
```sql
SELECT policy_version, config_json
FROM algo_bridge_config
WHERE policy_version = 'ALGO_BRIDGE_SPEC_v1';
```

**Update bridge config (if needed):**
```sql
UPDATE algo_bridge_config
SET config_json = jsonb_set(
    config_json,
    '{MASTERY_RECENCY_TAU_DAYS}',
    '30'
)
WHERE policy_version = 'ALGO_BRIDGE_SPEC_v1';
```

### Troubleshooting

**Issue: Students reporting "reset" after switch**
- Check bridge status: `GET /v1/admin/algorithms/bridge/status?user_id=<uuid>`
- Verify canonical state tables populated
- Check bridge job logs for errors
- Ensure `user_theme_stats` is maintained from `attempt_events`

**Issue: Switch not taking effect**
- Verify config updated: `GET /v1/admin/algorithms/runtime`
- Check if sessions are using snapshot (old sessions won't change)
- Verify router is being called (check logs)

**Issue: Performance degradation after switch**
- Check if safe mode enabled (freeze_updates)
- Verify bridge jobs not running (check `algo_state_bridge.status`)
- Monitor canonical state table sizes

**Issue: Bridge failing**
- Check `algo_state_bridge.details_json` for error messages
- Verify `algo_bridge_config` exists and has valid config
- Check database locks (bridge uses SELECT FOR UPDATE)

---

## Troubleshooting

### Service Won't Start

#### Backend Won't Start

**Symptoms:**
- Container exits immediately
- Health check fails
- Port 8000 not accessible

**Diagnosis:**
```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Database not ready
# 2. Port 8000 already in use
# 3. Missing environment variables
# 4. Python dependencies not installed
```

**Solutions:**

1. **Database Connection Error:**
   ```bash
   # Wait for postgres to be ready
   docker-compose up -d postgres
   sleep 5
   docker-compose up -d backend
   ```

2. **Port Already in Use:**
   ```bash
   # Find process using port 8000
   netstat -ano | findstr :8000  # Windows
   lsof -i :8000  # Mac/Linux
   
   # Kill process or change port in docker-compose.yml
   ```

3. **Missing Dependencies:**
   ```bash
   # Rebuild with no cache
   docker-compose build --no-cache backend
   docker-compose up -d backend
   ```

---

#### Frontend Won't Start

**Symptoms:**
- Container exits immediately
- Port 3000 not accessible
- Build errors

**Diagnosis:**
```bash
# Check logs
docker-compose logs frontend

# Common issues:
# 1. Node modules not installed
# 2. Port 3000 already in use
# 3. Build errors
# 4. API URL not configured
```

**Solutions:**

1. **Node Modules Missing:**
   ```bash
   # Rebuild with no cache
   docker-compose build --no-cache frontend
   docker-compose up -d frontend
   ```

2. **Build Errors:**
   ```bash
   # Check for TypeScript errors
   cd frontend
   npm run build
   
   # Fix errors, then restart
   docker-compose up -d --build frontend
   ```

3. **API Connection Error:**
   ```bash
   # Verify backend is running
   curl http://localhost:8000/health
   
   # Check NEXT_PUBLIC_API_URL in frontend/.env.local
   ```

---

#### Database Connection Issues

**Symptoms:**
- Backend can't connect to database
- "Connection refused" errors
- Timeout errors

**Diagnosis:**
```bash
# Check postgres is running
docker-compose ps postgres

# Check postgres logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready -U examplatform
```

**Solutions:**

1. **Postgres Not Running:**
   ```bash
   docker-compose up -d postgres
   # Wait 10 seconds for initialization
   ```

2. **Wrong Credentials:**
   ```bash
   # Check docker-compose.yml for DATABASE_URL
   # Verify username/password match
   ```

3. **Database Doesn't Exist:**
   ```bash
   # Create database
   docker-compose exec postgres psql -U examplatform -c "CREATE DATABASE examplatform;"
   ```

---

### Performance Issues

#### Slow API Responses

**Symptoms:**
- API takes >2 seconds to respond
- Timeout errors
- High CPU usage

**Diagnosis:**
```bash
# Check backend logs for slow queries
docker-compose logs backend | grep "slow"

# Check database performance
docker-compose exec postgres psql -U examplatform -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query
  FROM pg_stat_activity
  WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '1 second';
"
```

**Solutions:**

1. **Database Query Optimization:**
   - Add indexes (see data-model.md)
   - Review slow query log
   - Optimize N+1 queries

2. **Resource Limits:**
   ```yaml
   # In docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 2G
   ```

3. **Connection Pool:**
   - Increase database connection pool size
   - Check for connection leaks

---

#### High Memory Usage

**Symptoms:**
- Container memory usage >80%
- Out of memory errors
- Service restarts

**Diagnosis:**
```bash
# Check memory usage
docker stats

# Check for memory leaks
docker-compose logs backend | grep -i "memory"
```

**Solutions:**

1. **Increase Memory Limit:**
   ```yaml
   # docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             memory: 4G
   ```

2. **Optimize Code:**
   - Review for memory leaks
   - Limit result set sizes
   - Use pagination

---

### Data Issues

#### Missing Questions

**Symptoms:**
- Students can't see questions
- Question count is zero

**Diagnosis:**
```sql
-- Check question count
SELECT COUNT(*) FROM questions;
SELECT COUNT(*) FROM questions WHERE is_published = true;

-- Check themes
SELECT COUNT(*) FROM themes;
```

**Solutions:**

1. **Reseed Database:**
   ```bash
   curl -X POST http://localhost:8000/seed
   ```

2. **Check Publishing Status:**
   ```sql
   -- List unpublished questions
   SELECT id, question_text, is_published FROM questions WHERE is_published = false;
   ```

---

#### User Can't Login

**Symptoms:**
- Login fails
- "Invalid credentials" error
- User not found

**Diagnosis:**
```bash
# Check if user exists
curl -H "Authorization: Bearer <your_jwt_token>" http://localhost:8000/v1/sessions

# Check backend logs
docker-compose logs backend | grep -i "user"
```

**Solutions:**

1. **Verify User Exists:**
   ```sql
   SELECT * FROM users WHERE id = 'student-1';
   ```

2. **Reseed Users:**
   ```bash
   curl -X POST http://localhost:8000/seed
   ```

3. **Check Demo Credentials:**
   - Email: `student@demo.com`
   - Password: `demo123`

---

## Incident Response

### Service Down

#### Backend API Down

**Severity:** Critical

**Steps:**
1. Check service status: `docker-compose ps backend`
2. Check logs: `docker-compose logs --tail=50 backend`
3. Check health endpoint: `curl http://localhost:8000/health`
4. Restart service: `docker-compose restart backend`
5. If still down, rebuild: `docker-compose up -d --build backend`
6. Check database connectivity
7. Escalate if issue persists

**Rollback:**
```bash
# Revert to previous version
git checkout <previous-commit>
docker-compose up -d --build backend
```

---

#### Frontend Down

**Severity:** High

**Steps:**
1. Check service status: `docker-compose ps frontend`
2. Check logs: `docker-compose logs --tail=50 frontend`
3. Check if accessible: `curl http://localhost:3000`
4. Restart service: `docker-compose restart frontend`
5. If build errors, check TypeScript: `cd frontend && npm run build`
6. Rebuild if needed: `docker-compose up -d --build frontend`

---

#### Database Down

**Severity:** Critical

**Steps:**
1. Check service status: `docker-compose ps postgres`
2. Check logs: `docker-compose logs --tail=50 postgres`
3. Check disk space: `df -h` (if host)
4. Check postgres health: `docker-compose exec postgres pg_isready`
5. Restart: `docker-compose restart postgres`
6. If data corruption suspected, restore from backup
7. Check for disk full errors

**Data Recovery:**
```bash
# Restore from backup
docker-compose exec -T postgres psql -U examplatform examplatform < backup.sql
```

---

### Data Loss

**Severity:** Critical

**Steps:**
1. Stop writes if possible
2. Assess scope of data loss
3. Check if backup exists
4. Restore from most recent backup
5. Verify data integrity
6. Investigate root cause
7. Document incident

**Prevention:**
- Regular automated backups
- Test restore procedures
- Monitor disk space
- Use transaction logs

---

## Maintenance Tasks

### Daily Tasks

- [ ] Check service health
- [ ] Review error logs
- [ ] Monitor resource usage
- [ ] Check backup completion

### Weekly Tasks

- [ ] Review performance metrics
- [ ] Check disk space
- [ ] Update dependencies (security patches)
- [ ] Review and rotate logs

### Monthly Tasks

- [ ] Database optimization (VACUUM, ANALYZE)
- [ ] Security audit
- [ ] Dependency updates
- [ ] Capacity planning review
- [ ] Backup restoration test

---

### Database Maintenance

#### Vacuum and Analyze

```sql
-- Vacuum to reclaim space
VACUUM;

-- Analyze for query optimization
ANALYZE;

-- Full vacuum (requires exclusive lock)
VACUUM FULL;
```

#### Index Maintenance

```sql
-- Reindex
REINDEX DATABASE examplatform;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

---

### Log Rotation

#### Application Logs

```bash
# Rotate logs (if using file-based logging)
logrotate /etc/logrotate.d/examprep

# Or manually
mv app.log app.log.$(date +%Y%m%d)
touch app.log
```

#### Docker Logs

```bash
# Limit log size in docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Emergency Contacts

### On-Call Rotation

**Primary:** [To be defined]  
**Secondary:** [To be defined]  
**Escalation:** [To be defined]

### External Services

**Database Hosting:** [If applicable]  
**Cloud Provider:** [If applicable]  
**Monitoring Service:** [If applicable]

---

## Quick Reference

### Common Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart service
docker-compose restart <service>

# Rebuild service
docker-compose up -d --build <service>

# Access database
docker-compose exec postgres psql -U examplatform examplatform

# Backup database
docker-compose exec postgres pg_dump -U examplatform examplatform > backup.sql

# Restore database
docker-compose exec -T postgres psql -U examplatform examplatform < backup.sql

# Seed database
curl -X POST http://localhost:8000/seed

# Check health
curl http://localhost:8000/health
```

### Service Ports

- Frontend: 3000
- Backend: 8000
- PostgreSQL: 5432

### Environment Variables

**Backend:**
- `DATABASE_URL`: PostgreSQL connection string
- `CORS_ORIGINS`: Allowed CORS origins

**Frontend:**
- `NEXT_PUBLIC_API_URL`: Backend API URL

---

## Appendix

### Useful SQL Queries

```sql
-- Count published questions
SELECT COUNT(*) FROM questions WHERE is_published = true;

-- List active sessions
SELECT id, user_id, started_at FROM attempt_sessions WHERE is_submitted = false;

-- User performance summary
SELECT 
  user_id,
  COUNT(*) as total_sessions,
  AVG(score) as avg_score
FROM attempt_sessions
WHERE is_submitted = true
GROUP BY user_id;

-- Most answered questions
SELECT 
  question_id,
  COUNT(*) as attempt_count,
  SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_count
FROM attempt_answers
GROUP BY question_id
ORDER BY attempt_count DESC
LIMIT 10;
```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "Checking services..."

# Backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
  echo "✓ Backend is healthy"
else
  echo "✗ Backend is down"
fi

# Frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
  echo "✓ Frontend is accessible"
else
  echo "✗ Frontend is down"
fi
```

---

## CMS Smoke Test: OpenAPI Verification

### Accessing OpenAPI Docs

**Swagger UI:** `http://localhost:8000/docs`  
**ReDoc:** `http://localhost:8000/redoc`  
**OpenAPI JSON:** `http://localhost:8000/openapi.json`

**Note:** OpenAPI docs are only available when `ENV != "prod"`.

### Required Endpoints in OpenAPI

The following CMS endpoints must appear in the OpenAPI documentation:

#### Questions CMS (`/v1/admin/questions`)
- `GET /v1/admin/questions` - List questions
- `POST /v1/admin/questions` - Create question
- `GET /v1/admin/questions/{question_id}` - Get question
- `PUT /v1/admin/questions/{question_id}` - Update question
- `DELETE /v1/admin/questions/{question_id}` - Delete question
- `POST /v1/admin/questions/{question_id}/submit` - Submit for review
- `POST /v1/admin/questions/{question_id}/approve` - Approve question
- `POST /v1/admin/questions/{question_id}/reject` - Reject question
- `POST /v1/admin/questions/{question_id}/publish` - Publish question
- `POST /v1/admin/questions/{question_id}/unpublish` - Unpublish question
- `GET /v1/admin/questions/{question_id}/versions` - List versions
- `GET /v1/admin/questions/{question_id}/versions/{version_id}` - Get version

#### Media (`/v1/admin/media`)
- `POST /v1/admin/media` - Upload media
- `GET /v1/admin/media/{media_id}` - Get media
- `POST /v1/admin/media/questions/{question_id}/attach` - Attach media
- `DELETE /v1/admin/media/questions/{question_id}/detach/{media_id}` - Detach media

#### Audit (`/v1/admin/audit`) - Dev Only
- `GET /v1/admin/audit` - Query audit log

### Example Request Bodies

#### Create Question
```json
{
  "stem": "What is 2+2?",
  "option_a": "3",
  "option_b": "4",
  "option_c": "5",
  "option_d": "6",
  "option_e": "7",
  "correct_index": 1,
  "explanation_md": "2+2 equals 4",
  "year_id": 1,
  "block_id": 1,
  "theme_id": 1,
  "difficulty": "easy",
  "cognitive_level": "recall"
}
```

#### Update Question
```json
{
  "stem": "Updated question stem",
  "explanation_md": "Updated explanation"
}
```

#### Reject Question
```json
{
  "reason": "Needs more explanation and better options"
}
```

#### Attach Media
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "STEM"
}
```

### Verification Checklist

When checking OpenAPI docs, verify:

1. ✅ All endpoints listed above are present
2. ✅ Request/response schemas match the examples
3. ✅ Authentication requirement is shown (lock icon)
4. ✅ Required vs optional fields are clearly marked
5. ✅ Error response schemas are documented (400, 403, 404, 422)
6. ✅ Enum values are shown (QuestionStatus, MediaRole, ChangeKind)
7. ✅ UUID format is correctly specified for IDs

### Testing via OpenAPI UI

1. Click "Authorize" button
2. Enter Bearer token: `Bearer <your_access_token>`
3. Try "Try it out" on each endpoint
4. Verify responses match expected schemas

# Database
if docker-compose exec -T postgres pg_isready -U examplatform > /dev/null 2>&1; then
  echo "✓ Database is ready"
else
  echo "✗ Database is down"
fi
```

---

## CDN Verification

### Overview

The platform uses Cloudflare CDN in "static-only shield" mode. This section provides verification steps and rollback procedures.

**Key Rules:**
- API endpoints (`/v1/*`, `/api/*`): **NEVER cached** (always bypass)
- Authenticated routes (`/student/*`, `/admin/*`): **NEVER cached** (always bypass)
- Static assets (`/_next/static/*`): Cached at edge (1 year)
- Public pages (`/`, `/login`, `/signup`): Short cache (5 minutes)

### Verification Checklist

After deploying CDN configuration, verify cache behavior:

#### 1. Verify API Bypass

```bash
# Test API health endpoint
curl -I https://api.<your-domain>/v1/health
```

**Expected headers:**
```
Cache-Control: no-store
Pragma: no-cache
Expires: 0
CF-Cache-Status: BYPASS
X-Origin: api
X-Request-ID: <uuid>
```

**If `CF-Cache-Status: HIT` appears:** ⚠️ **CRITICAL** - API is being cached. Disable CDN immediately and check Cache Rules.

#### 2. Verify Static Assets Cache

```bash
# Test Next.js static asset
curl -I https://<your-domain>/_next/static/<somefile>.js
```

**Expected headers:**
```
Cache-Control: public, max-age=31536000, immutable
CF-Cache-Status: HIT (after first request)
X-Origin: frontend
```

**First request:** `CF-Cache-Status: MISS` (expected)
**Subsequent requests:** `CF-Cache-Status: HIT` (expected)

#### 3. Verify Public Pages Cache

```bash
# Test landing page
curl -I https://<your-domain>/
```

**Expected headers:**
```
Cache-Control: public, max-age=300
CF-Cache-Status: HIT (after first request, within 5 minutes)
X-Origin: frontend
```

#### 4. Verify Authenticated Routes Bypass

```bash
# Test student dashboard (should bypass even if authenticated)
curl -I https://<your-domain>/student/dashboard
```

**Expected headers:**
```
Cache-Control: no-store
Pragma: no-cache
Expires: 0
CF-Cache-Status: BYPASS
X-Origin: frontend
```

#### 5. Verify Debug Headers

All responses should include:
- `X-Origin`: `"api"` (FastAPI) or `"frontend"` (Next.js)
- `X-Request-ID`: Request tracking ID (if available)
- `X-App-Version`: Git SHA first 8 chars (if `GIT_SHA` or `BUILD_ID` env var set)

### Automated Verification Script

```bash
#!/bin/bash
# CDN Verification Script

DOMAIN="<your-domain>"
API_DOMAIN="api.<your-domain>"

echo "=== CDN Verification ==="

# 1. API Bypass
echo "1. Testing API bypass..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -I "https://${API_DOMAIN}/v1/health")
API_CACHE=$(curl -s -I "https://${API_DOMAIN}/v1/health" | grep -i "CF-Cache-Status" | cut -d' ' -f2 | tr -d '\r')
if [ "$API_CACHE" = "BYPASS" ]; then
  echo "  ✅ API bypass working (CF-Cache-Status: BYPASS)"
else
  echo "  ❌ API NOT bypassing cache! (CF-Cache-Status: $API_CACHE)"
  echo "  ⚠️  CRITICAL: Disable CDN immediately"
fi

# 2. Static Assets Cache
echo "2. Testing static assets cache..."
STATIC_CACHE=$(curl -s -I "https://${DOMAIN}/_next/static/chunks/main.js" 2>/dev/null | grep -i "CF-Cache-Status" | cut -d' ' -f2 | tr -d '\r')
if [ "$STATIC_CACHE" = "HIT" ] || [ "$STATIC_CACHE" = "MISS" ]; then
  echo "  ✅ Static assets cache working (CF-Cache-Status: $STATIC_CACHE)"
else
  echo "  ⚠️  Static assets cache issue (CF-Cache-Status: $STATIC_CACHE)"
fi

# 3. Public Pages Cache
echo "3. Testing public pages cache..."
PUBLIC_CACHE=$(curl -s -I "https://${DOMAIN}/" | grep -i "CF-Cache-Status" | cut -d' ' -f2 | tr -d '\r')
if [ "$PUBLIC_CACHE" = "HIT" ] || [ "$PUBLIC_CACHE" = "MISS" ]; then
  echo "  ✅ Public pages cache working (CF-Cache-Status: $PUBLIC_CACHE)"
else
  echo "  ⚠️  Public pages cache issue (CF-Cache-Status: $PUBLIC_CACHE)"
fi

# 4. Authenticated Routes Bypass
echo "4. Testing authenticated routes bypass..."
AUTH_CACHE=$(curl -s -I "https://${DOMAIN}/student/dashboard" | grep -i "CF-Cache-Status" | cut -d' ' -f2 | tr -d '\r')
if [ "$AUTH_CACHE" = "BYPASS" ]; then
  echo "  ✅ Authenticated routes bypass working (CF-Cache-Status: BYPASS)"
else
  echo "  ❌ Authenticated routes NOT bypassing! (CF-Cache-Status: $AUTH_CACHE)"
  echo "  ⚠️  CRITICAL: Check Cache Rules"
fi

echo "=== Verification Complete ==="
```

### Rollback Procedures

#### Emergency Rollback (Disable CDN Completely)

**When to use:** API responses are being cached, or authenticated content is showing wrong user data.

**Steps:**
1. Log in to Cloudflare Dashboard
2. Go to **DNS** → **Records**
3. For each proxied record (🟠 orange cloud):
   - Click the **orange cloud** to turn it **grey** (⚪ DNS only)
4. **Verify:** DNS now resolves directly to origin (bypasses Cloudflare)
5. **Test:** `curl -I https://<domain>/` should show origin headers directly

**Time to effect:** 1-2 minutes (DNS propagation)

#### Partial Rollback (Disable Caching Only)

**When to use:** CDN is working but caching behavior is incorrect.

**Steps:**
1. Log in to Cloudflare Dashboard
2. Go to **Caching** → **Configuration**
3. Set **Caching Level:** Bypass
4. **Verify:** All requests bypass cache (but still go through Cloudflare for DDoS protection)

**Time to effect:** Immediate

#### Purge Cache

**When to use:** Static assets changed, or need to force fresh content.

**Steps:**
1. Log in to Cloudflare Dashboard
2. Go to **Caching** → **Purge Cache**
3. Choose one:
   - **Purge Everything** (removes all cached content)
   - **Custom Purge** (enter specific URLs)
4. Click **Purge**

**Time to effect:** 1-2 minutes

### Troubleshooting

#### Issue: API responses showing `CF-Cache-Status: HIT`

**Symptoms:** API endpoints are being cached

**Immediate Actions:**
1. **Disable CDN** (grey cloud on DNS records)
2. Verify Cache Rules: Priority 1 rule must bypass `/api/` and `/v1/`
3. Check origin headers: Should include `Cache-Control: no-store`
4. Purge cache
5. Re-enable CDN only after verification

#### Issue: Authenticated content showing wrong user data

**Symptoms:** User A sees User B's data

**CRITICAL SECURITY ISSUE**

**Immediate Actions:**
1. **Disable CDN immediately** (grey cloud)
2. Verify Cache Rules: `/student/*` and `/admin/*` must bypass
3. Check origin headers: Should include `Cache-Control: no-store`
4. Purge all cache
5. Investigate root cause before re-enabling

#### Issue: Static assets not caching

**Symptoms:** `CF-Cache-Status: MISS` on `/_next/static/*`

**Resolution:**
1. Verify Cache Rule 3 is active and matches `/_next/static/`
2. Check origin headers: Should include `Cache-Control: public, max-age=31536000, immutable`
3. First request is always MISS (expected)
4. Wait for second request to verify HIT

### Monitoring

**Key Metrics to Monitor:**
- **Cache Hit Ratio:** Should be 30-50% overall (mostly static assets)
- **Bandwidth Saved:** Should show significant savings
- **Origin Requests:** Should decrease (especially for static assets)
- **Error Rate:** Should remain stable (no increase)

**Cloudflare Analytics:**
- Go to **Analytics** → **Performance**
- Monitor cache hit ratio, bandwidth saved, origin requests

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2024-12-30 | Initial runbook created | System |
| 2025-01-25 | Added CDN verification and rollback procedures | System |

