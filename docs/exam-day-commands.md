# Exam-Day Command Reference

**Quick command cheat sheet for incident response during exam periods.**

---

## 🐳 Docker Commands

### Container Status
```bash
# List all containers and status
docker compose -f infra/docker/compose/docker-compose.prod.yml ps

# Check specific service
docker ps | grep exam_platform

# Container health (if healthcheck configured)
docker inspect exam_platform_backend | jq '.[0].State.Health'
```

### Logs
```bash
# Backend logs (last 100 lines)
docker logs exam_platform_backend --tail=100

# Backend logs (follow)
docker logs exam_platform_backend -f

# Backend logs (last 10 minutes, errors only)
docker logs exam_platform_backend --since 10m | grep -i "error\|exception\|500"

# Traefik logs (access log)
docker logs exam_platform_traefik --tail=100

# Traefik logs (errors)
docker logs exam_platform_traefik --tail=100 | grep -i "error"

# Postgres logs
docker logs exam_platform_postgres --tail=100

# Redis logs
docker logs exam_platform_redis --tail=100

# All services (last 50 lines each)
docker compose -f infra/docker/compose/docker-compose.prod.yml logs --tail=50
```

### Container Management
```bash
# Restart backend (if needed)
docker restart exam_platform_backend

# Restart all services
docker compose -f infra/docker/compose/docker-compose.prod.yml restart

# Restart specific service
docker compose -f infra/docker/compose/docker-compose.prod.yml restart backend

# View resource usage
docker stats exam_platform_backend exam_platform_postgres exam_platform_redis
```

---

## 🗄️ Database Commands

### Connection & Health
```bash
# Test DB connection
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "SELECT 1;"

# Check active connections
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
  SELECT count(*) as total, state, wait_event_type 
  FROM pg_stat_activity 
  WHERE datname = 'exam_platform' 
  GROUP BY state, wait_event_type;"

# Check connection limit
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
  SHOW max_connections;"
```

### Performance Diagnostics
```bash
# Long-running queries (>5 seconds)
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
  SELECT pid, now() - query_start AS duration, state, wait_event_type, query 
  FROM pg_stat_activity 
  WHERE state = 'active' 
    AND now() - query_start > interval '5 seconds'
  ORDER BY duration DESC;"

# Kill specific query (use with caution)
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
  SELECT pg_terminate_backend(<pid>);"

# Table sizes (identify large tables)
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
  SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
  LIMIT 10;"

# Index usage (identify unused indexes)
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
  SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
  FROM pg_stat_user_indexes
  WHERE idx_scan = 0
  ORDER BY pg_relation_size(indexrelid) DESC
  LIMIT 10;"
```

### System Flags Check
```bash
# Check EXAM_MODE
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
  SELECT key, value, updated_at, updated_by, reason 
  FROM system_flags 
  WHERE key = 'EXAM_MODE';"

# Check FREEZE_UPDATES
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
  SELECT key, value, updated_at, updated_by, reason 
  FROM system_flags 
  WHERE key = 'FREEZE_UPDATES';"

# All system flags
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
  SELECT * FROM system_flags;"
```

### Algorithm Runtime Config
```bash
# Check current profile
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
  SELECT active_profile, config_json->'safe_mode' as safe_mode, changed_at, changed_by_user_id
  FROM algo_runtime_config
  ORDER BY changed_at DESC
  LIMIT 1;"
```

---

## 🔴 Redis Commands

### Health & Status
```bash
# Ping test
docker exec exam_platform_redis redis-cli PING
# Expected: PONG

# Info (summary)
docker exec exam_platform_redis redis-cli INFO

# Memory usage
docker exec exam_platform_redis redis-cli INFO memory | grep used_memory_human

# Latency test
docker exec exam_platform_redis redis-cli --latency
# Press Ctrl+C after a few seconds

# Connected clients
docker exec exam_platform_redis redis-cli CLIENT LIST
```

### Key Inspection
```bash
# Count keys
docker exec exam_platform_redis redis-cli DBSIZE

# List all keys (use with caution on large datasets)
docker exec exam_platform_redis redis-cli KEYS "*"

# List rate limit keys
docker exec exam_platform_redis redis-cli KEYS "rl:*"

# Get specific key
docker exec exam_platform_redis redis-cli GET "rl:login:ip:192.168.1.1:60"

# TTL of key
docker exec exam_platform_redis redis-cli TTL "rl:login:ip:192.168.1.1:60"
```

### Maintenance
```bash
# Flush all (use with extreme caution - clears all data)
docker exec exam_platform_redis redis-cli FLUSHALL

# Restart Redis
docker restart exam_platform_redis
```

---

## 🌐 HTTP Health Checks

### Basic Health
```bash
# Simple health check (no auth required)
curl -s https://api.<DOMAIN>/v1/health
# Expected: {"status":"ok"}

# Readiness check (checks DB, Redis)
curl -s https://api.<DOMAIN>/v1/ready | jq
# Expected: {"status":"ok","checks":{"db":{"status":"ok"},"redis":{"status":"ok"}},...}
```

### Metrics (Admin Only)
```bash
# Get metrics (requires admin token)
curl -s -H "Authorization: Bearer <ADMIN_TOKEN>" \
  https://api.<DOMAIN>/v1/admin/observability/metrics | jq

# Check latency p95
curl -s -H "Authorization: Bearer <ADMIN_TOKEN>" \
  https://api.<DOMAIN>/v1/admin/observability/metrics | jq '.latency_p95'

# Check error counts
curl -s -H "Authorization: Bearer <ADMIN_TOKEN>" \
  https://api.<DOMAIN>/v1/admin/observability/metrics | jq '.error_counts'
```

### System Info (Admin Only)
```bash
# System information
curl -s -H "Authorization: Bearer <ADMIN_TOKEN>" \
  https://api.<DOMAIN>/v1/admin/system/info | jq

# Exam mode state
curl -s -H "Authorization: Bearer <ADMIN_TOKEN>" \
  https://api.<DOMAIN>/v1/admin/system/exam-mode | jq
```

---

## 🎛️ Kill Switch Commands

### Enable EXAM_MODE
```bash
curl -X POST https://api.<DOMAIN>/v1/admin/system/exam-mode \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "reason": "Exam day - enabling exam mode",
    "confirmation_phrase": "ENABLE EXAM MODE"
  }'
```

### Disable EXAM_MODE
```bash
curl -X POST https://api.<DOMAIN>/v1/admin/system/exam-mode \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false,
    "reason": "Exam completed - disabling exam mode",
    "confirmation_phrase": "DISABLE EXAM MODE"
  }'
```

### Enable FREEZE_UPDATES
```bash
curl -X POST https://api.<DOMAIN>/v1/admin/algorithms/runtime/freeze_updates \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Exam instability - freezing learning updates",
    "confirmation_phrase": "FREEZE UPDATES"
  }'
```

### Disable FREEZE_UPDATES
```bash
curl -X POST https://api.<DOMAIN>/v1/admin/algorithms/runtime/unfreeze_updates \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Stability restored - unfreezing updates",
    "confirmation_phrase": "UNFREEZE UPDATES"
  }'
```

### Switch to FALLBACK Profile
```bash
curl -X POST https://api.<DOMAIN>/v1/admin/algorithms/runtime/switch \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "V0_FALLBACK",
    "reason": "Critical algorithm issue - switching to fallback",
    "confirmation_phrase": "SWITCH TO FALLBACK PROFILE",
    "overrides": {}
  }'
```

### Switch back to PRIMARY Profile
```bash
curl -X POST https://api.<DOMAIN>/v1/admin/algorithms/runtime/switch \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "V1_PRIMARY",
    "reason": "Issue resolved - switching back to primary",
    "confirmation_phrase": "SWITCH TO PRIMARY PROFILE",
    "overrides": {}
  }'
```

**Note:** Profile switches may require two-person approval if police mode is enabled. Check admin freeze status first.

---

## 📊 Traefik Logs

### Access Logs
```bash
# Recent access logs (last 100 lines)
docker exec exam_platform_traefik tail -100 /var/log/traefik/access.log

# Access logs (errors only)
docker exec exam_platform_traefik tail -100 /var/log/traefik/access.log | \
  jq 'select(.StatusCode >= 500)'

# Access logs (5xx errors, last hour)
docker exec exam_platform_traefik tail -1000 /var/log/traefik/access.log | \
  jq 'select(.StatusCode >= 500) | {time: .RequestTime, status: .StatusCode, path: .RequestPath}'

# Count 5xx errors (last 1000 lines)
docker exec exam_platform_traefik tail -1000 /var/log/traefik/access.log | \
  jq 'select(.StatusCode >= 500) | .StatusCode' | sort | uniq -c
```

### Traefik Dashboard (via SSH tunnel)
```bash
# Create SSH tunnel to Traefik dashboard (localhost:8080)
ssh -L 8080:localhost:8080 user@<server>

# Then access: http://localhost:8080
```

---

## 🔍 Quick Diagnostics

### Full System Check
```bash
#!/bin/bash
# Quick health check script

echo "=== Container Status ==="
docker compose -f infra/docker/compose/docker-compose.prod.yml ps

echo -e "\n=== Health Endpoints ==="
curl -s https://api.<DOMAIN>/v1/health | jq
curl -s https://api.<DOMAIN>/v1/ready | jq

echo -e "\n=== Database Connections ==="
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname = 'exam_platform';"

echo -e "\n=== Redis Status ==="
docker exec exam_platform_redis redis-cli PING

echo -e "\n=== System Flags ==="
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c \
  "SELECT key, value, updated_at FROM system_flags;"
```

---

## 📝 Notes

- **Replace `<DOMAIN>`** with your actual domain (e.g., `example.com`)
- **Replace `<ADMIN_TOKEN>`** with a valid admin JWT token
- **All timestamps** in logs are UTC unless specified
- **jq** is recommended for JSON parsing (install: `apt-get install jq` or `brew install jq`)
- **SSH access** required for some commands (database, Redis, Traefik logs)

---

**See also:** `docs/incident-1pager.md` for incident response procedures
