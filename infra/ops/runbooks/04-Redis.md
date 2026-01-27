# Redis Runbook

**Purpose**: Procedures for Redis troubleshooting, inspection, and when to flush.

## Prerequisites

- Access to staging server via SSH
- Redis container running

## When to Flush Redis

### ✅ Safe to Flush

- **Cache data only**: If Redis is used only for caching (session data, API responses)
- **Non-critical data**: Data that can be regenerated
- **Staging environment**: Always safe in staging
- **After deployment**: If cache invalidation is needed
- **Memory pressure**: If Redis is using too much memory and cache can be regenerated

### ❌ Do NOT Flush

- **Session storage**: If Redis stores active user sessions (users will be logged out)
- **Critical state**: If Redis stores critical application state
- **Production during peak hours**: Avoid flushing during high traffic
- **Without backup**: If data cannot be regenerated

## Flush Redis

### Flush All Data

```bash
# SSH to staging server
ssh <STAGING_USER>@<STAGING_HOST>

# Navigate to deployment directory
cd ~/exam-platform-staging

# Flush all keys (⚠️ Use with caution)
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli FLUSHALL

# Or flush current database only
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli FLUSHDB
```

### Flush Specific Keys

```bash
# Flush keys matching a pattern
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli --scan --pattern "session:*" | xargs redis-cli DEL

# Example: Flush all cache keys
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli --scan --pattern "cache:*" | xargs redis-cli DEL
```

## Keyspace Inspection

### List All Keys

```bash
# List all keys (use with caution on large databases)
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli KEYS "*"

# Count total keys
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli DBSIZE

# List keys matching pattern
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli KEYS "session:*"
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli KEYS "cache:*"
```

### Inspect Specific Key

```bash
# Get key type
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli TYPE "session:abc123"

# Get key value (string)
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli GET "session:abc123"

# Get key value (hash)
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli HGETALL "session:abc123"

# Get key TTL (time to live)
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli TTL "session:abc123"
# Returns: -1 (no expiry), -2 (key doesn't exist), or seconds until expiry
```

### Keyspace Statistics

```bash
# Get keyspace info
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli INFO keyspace

# Get memory info
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli INFO memory

# Get all info
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli INFO
```

## Memory Management

### Check Memory Usage

```bash
# Current memory usage
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli INFO memory | grep used_memory_human
# Output: used_memory_human:256.00M

# Memory usage by key pattern
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli --bigkeys
```

### Set Memory Limits

```bash
# Check current maxmemory setting
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli CONFIG GET maxmemory

# Set maxmemory (if not set in docker-compose)
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli CONFIG SET maxmemory 256mb

# Check eviction policy
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli CONFIG GET maxmemory-policy
# Common policies: noeviction, allkeys-lru, volatile-lru
```

## Connection Troubleshooting

### Check Connections

```bash
# List connected clients
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli CLIENT LIST

# Count connections
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli INFO clients | grep connected_clients

# Check connection from backend
docker compose -f docker-compose.staging.yml exec backend_staging python -c "from app.core.redis_client import is_redis_available; print('Redis OK' if is_redis_available() else 'Redis DOWN')"
```

### Kill Connections

```bash
# Kill specific client (use client ID from CLIENT LIST)
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli CLIENT KILL <client_id>

# Kill all clients from specific IP
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli CLIENT KILL ip:<ip_address>
```

## Performance Troubleshooting

### Check Slow Commands

```bash
# Enable slow log (if not already enabled)
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli CONFIG SET slowlog-log-slower-than 10000  # 10ms

# View slow log
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli SLOWLOG GET 10

# Clear slow log
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli SLOWLOG RESET
```

### Monitor Commands in Real-Time

```bash
# Monitor all commands (use Ctrl+C to stop)
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli MONITOR

# Monitor specific commands only
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli MONITOR | grep -E "(GET|SET|DEL)"
```

### Check Command Statistics

```bash
# Command statistics
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli INFO commandstats

# Reset statistics
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli CONFIG RESETSTAT
```

## Health Checks

### Basic Health Check

```bash
# Ping Redis
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli PING
# Expected: PONG

# Check if Redis is available from backend
docker compose -f docker-compose.staging.yml exec backend_staging python -c "from app.core.redis_client import is_redis_available; print('Redis OK' if is_redis_available() else 'Redis DOWN')"
```

### Check Redis in Readiness Endpoint

```bash
# Check backend readiness (includes Redis check)
curl -s https://<STAGING_DOMAIN>/api/v1/ready | jq '.checks.redis'
# Expected: {"status":"ok"} or {"status":"degraded","message":"..."}
```

## Restart Redis

### Graceful Restart

```bash
# Stop Redis
docker compose -f docker-compose.staging.yml stop redis_staging

# Start Redis
docker compose -f docker-compose.staging.yml start redis_staging

# Or restart
docker compose -f docker-compose.staging.yml restart redis_staging

# Wait for Redis to be ready
sleep 5

# Verify
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli PING
```

### Force Restart (if Redis is hung)

```bash
# Force stop
docker compose -f docker-compose.staging.yml kill redis_staging

# Start
docker compose -f docker-compose.staging.yml start redis_staging

# Verify
sleep 5
docker compose -f docker-compose.staging.yml exec redis_staging redis-cli PING
```

## Verification Checklist

After any Redis intervention:

1. **Redis is responding**:
   ```bash
   docker compose -f docker-compose.staging.yml exec redis_staging redis-cli PING
   # Expected: PONG
   ```

2. **Backend can connect to Redis**:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend_staging python -c "from app.core.redis_client import is_redis_available; assert is_redis_available(), 'Redis not available'"
   ```

3. **Readiness check includes Redis**:
   ```bash
   curl -s https://<STAGING_DOMAIN>/api/v1/ready | jq -r '.checks.redis.status'
   # Expected: "ok" or "degraded" (not "down" if Redis is optional)
   ```

4. **Memory usage is reasonable**:
   ```bash
   docker compose -f docker-compose.staging.yml exec redis_staging redis-cli INFO memory | grep used_memory_human
   # Expected: Within configured limits
   ```

5. **No connection errors in backend logs**:
   ```bash
   docker compose -f docker-compose.staging.yml logs --since=5m backend_staging | grep -i "redis" | grep -i error
   # Expected: No output
   ```

## Related Runbooks

- [01-Incident-Checklist.md](./01-Incident-Checklist.md) - Incident triage
- [00-QuickStart.md](./00-QuickStart.md) - Quick health checks
- [03-Database.md](./03-Database.md) - Database troubleshooting
