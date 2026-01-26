# Production Hardening Summary

## Overview

This document summarizes the production hardening pass focused on **zero-lag, predictable latency** under exam-time load spikes. All changes are **tuning and guardrails only** - no product behavior or API changes.

## Implementation Date

January 2026

## Hardening Layers

### 1. Traefik Edge Layer

**Timeouts** (protect against slow clients):
- Read timeout: 15s
- Write timeout: 15s
- Idle timeout: 60s

**Connection Limits**:
- Inflight request limit: 100 concurrent per IP
- Applied to: `api` and `api-staging` routers
- Prevents backend overload from connection storms

**Files Modified**:
- `infra/traefik/traefik.yml` - Added timeout configuration
- `infra/docker/compose/docker-compose.prod.yml` - Added `conn-limit` middleware and applied to routers

### 2. FastAPI Application Layer

**Worker Model**:
- Uvicorn workers: `(2 * CPU cores) + 1` formula
- Default: 5 workers (for 1.5 CPU container)
- Configurable via `UVICORN_WORKERS` environment variable

**Concurrency Limits**:
- `--limit-concurrency=200`: Max concurrent requests per worker
- `--limit-max-requests=10000`: Graceful worker recycling
- `--timeout-keep-alive=5`: Keep-alive timeout

**Files Modified**:
- `backend/Dockerfile` - Updated CMD to use workers and limits
- `infra/docker/compose/docker-compose.prod.yml` - Added environment variables

### 3. PostgreSQL Database Layer

**Connection Pool** (SQLAlchemy):
- `pool_size=10`: Base pool size (increased from 5)
- `max_overflow=10`: Additional connections beyond pool_size
- `pool_timeout=30`: Seconds to wait for connection
- `pool_pre_ping=True`: Verify connections before use

**Shared Buffers**:
- Set to 25% of container memory limit
- For 2GB limit: `shared_buffers=512MB`
- Configured via `POSTGRES_SHARED_BUFFERS` environment variable

**Index Audit**:
All critical indexes verified:
- ✅ `test_sessions(user_id, created_at)` - User attempt history
- ✅ `session_answers(session_id)` - Answer lookups
- ✅ `questions(block_id, theme_id)` - Question filtering
- ✅ `revision_queue(user_id, due_at, status)` - Revision scheduling
- ✅ `user_theme_mastery(user_id, theme_id)` - Mastery lookups
- ✅ `attempt_events(user_id, event_ts)` - Analytics queries

**Files Modified**:
- `backend/app/db/engine.py` - Updated pool configuration
- `infra/docker/compose/docker-compose.prod.yml` - Added Postgres memory limits and shared_buffers

### 4. Redis Cache Layer

**Timeouts** (fast fail):
- `socket_connect_timeout=1`: Fast fail on connect
- `socket_timeout=1`: Fast fail on operations
- Prevents slow Redis from blocking requests

**Graceful Degradation**:
- Rate limiting: Fail-open if Redis unavailable
- Token blacklist: Falls back to DB checks
- Circuit breaker pattern: Never blocks requests

**Files Modified**:
- `backend/app/core/redis_client.py` - Updated timeouts (5s → 1s)

### 5. Container Resource Limits

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

**Files Modified**:
- `infra/docker/compose/docker-compose.prod.yml` - Added `deploy.resources` and `ulimits` to all services

### 6. Exam-Time Mode

**Purpose**: Disable heavy operations during exam spikes.

**Configuration**:
- Environment variable: `EXAM_MODE=true/false`
- When enabled: Disables heavy analytics, admin bulk jobs, background recalculations

**Files Modified**:
- `backend/app/core/config.py` - Added `EXAM_MODE` setting
- `infra/docker/compose/docker-compose.prod.yml` - Added environment variable

### 7. Idempotency Improvements

**Session Submit Endpoint**:
- Made idempotent: Safe to call multiple times
- Returns existing result if already submitted
- Prevents duplicate submissions during network retries

**Files Modified**:
- `backend/app/services/session_engine.py` - Updated `submit_session` to be idempotent
- `backend/app/api/v1/endpoints/sessions.py` - Updated endpoint to handle idempotency

## Performance Targets

**Baseline Latency** (normal load):
- Health check: `<50ms` (p95)
- Session create: `<200ms` (p95)
- Answer submit: `<100ms` (p95)
- Session submit: `<300ms` (p95)

**Exam-Time Load** (50 concurrent users):
- No 5xx errors
- p95 latency: `<500ms` (API endpoints)
- No database connection exhaustion
- No cascading failures

## Observability

**Request Duration**:
- Logged in `X-Response-Time-ms` header
- Slow request warnings: `>500ms` (warn), `>1500ms` (error)

**Database Query Duration**:
- Logged in `X-DB-Time-ms` header
- Slow SQL warnings: `>100ms` (warn), `>300ms` (error)
- Top 5 slow queries tracked per request

**Query Count**:
- Logged in `X-DB-Queries` header
- Helps identify N+1 query issues

## Environment Variables

**New Variables** (add to `.env` or server environment):
```bash
# Uvicorn worker configuration
UVICORN_WORKERS=5
UVICORN_TIMEOUT_KEEP_ALIVE=5
UVICORN_LIMIT_CONCURRENCY=200
UVICORN_LIMIT_MAX_REQUESTS=10000

# Exam-time mode
EXAM_MODE=false

# PostgreSQL shared_buffers
POSTGRES_SHARED_BUFFERS=512MB
```

## Verification Commands

**Check Worker Count**:
```bash
docker exec exam_platform_backend ps aux | grep uvicorn | wc -l
# Should be UVICORN_WORKERS + 1
```

**Check Database Pool**:
```bash
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE datname = 'exam_platform';
"
# Should be < pool_size + max_overflow (20)
```

**Check Container Limits**:
```bash
docker stats exam_platform_backend --no-stream
docker stats exam_platform_postgres --no-stream
```

**Check Slow Queries**:
```bash
docker logs exam_platform_backend --tail=500 | grep "slow_sql"
```

**Baseline Latency**:
```bash
curl -w "%{time_total}\n" -o /dev/null -s https://api.<DOMAIN>/health
```

## Files Modified

### Configuration Files
1. `infra/traefik/traefik.yml` - Added timeouts
2. `infra/docker/compose/docker-compose.prod.yml` - Added connection limits, container limits, environment variables
3. `backend/Dockerfile` - Updated to use workers and limits
4. `.env.example` - Added new environment variables

### Application Code
5. `backend/app/db/engine.py` - Updated pool configuration
6. `backend/app/core/redis_client.py` - Updated timeouts
7. `backend/app/core/config.py` - Added `EXAM_MODE` setting
8. `backend/app/services/session_engine.py` - Made submit idempotent
9. `backend/app/api/v1/endpoints/sessions.py` - Updated submit endpoint

### Documentation
10. `docs/runbook.md` - Added "Production Performance Hardening" section
11. `docs/PRODUCTION_HARDENING_SUMMARY.md` - This file

## Next Steps

1. **Deploy and Monitor**:
   - Deploy changes to production
   - Monitor baseline latency
   - Verify worker count and pool sizes

2. **Load Testing**:
   - Run concurrent load tests (50 users)
   - Verify p95 latency targets
   - Check for connection exhaustion

3. **Exam-Time Mode**:
   - Test `EXAM_MODE=true` during low-traffic period
   - Verify heavy operations are disabled
   - Document which operations are affected

4. **Ongoing Monitoring**:
   - Track slow SQL queries
   - Monitor request duration trends
   - Alert on connection pool exhaustion

## Related Documentation

- `docs/runbook.md` - "Production Performance Hardening" section
- `docs/performance.md` - Performance monitoring and optimization
- `docs/observability.md` - Observability and logging
