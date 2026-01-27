# Database Runbook

**Purpose**: Procedures for database migrations, backups, restores, and troubleshooting.

## Prerequisites

- Access to staging server via SSH
- Database credentials (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
- Backup storage location (if applicable)

## Migrations

### Run Migrations

```bash
# SSH to staging server
ssh <STAGING_USER>@<STAGING_HOST>

# Navigate to deployment directory
cd ~/exam-platform-staging

# Run migrations via backend container
docker compose -f docker-compose.staging.yml run --rm backend_staging alembic upgrade head

# Verify migration completed
docker compose -f docker-compose.staging.yml run --rm backend_staging alembic current
```

### Check Migration Status

```bash
# Check current migration version
docker compose -f docker-compose.staging.yml exec backend_staging alembic current

# List all migrations
docker compose -f docker-compose.staging.yml exec backend_staging alembic history

# Check pending migrations
docker compose -f docker-compose.staging.yml exec backend_staging alembic heads
```

### Rollback Migration

**⚠️ WARNING**: Only rollback if migration is designed to be reversible and you've tested it.

```bash
# Rollback one migration
docker compose -f docker-compose.staging.yml exec backend_staging alembic downgrade -1

# Rollback to specific revision
docker compose -f docker-compose.staging.yml exec backend_staging alembic downgrade <revision_id>

# Verify rollback
docker compose -f docker-compose.staging.yml exec backend_staging alembic current
```

## Backups

### Manual Backup

```bash
# Connect to postgres container
docker compose -f docker-compose.staging.yml exec postgres_staging bash

# Create backup (inside container)
pg_dump -U <POSTGRES_USER> -d <POSTGRES_DB> -F c -f /tmp/backup_$(date +%Y%m%d_%H%M%S).dump

# Copy backup to host (from host, not container)
docker compose -f docker-compose.staging.yml cp postgres_staging:/tmp/backup_*.dump ./backups/

# Or use docker exec to create backup directly on host
docker compose -f docker-compose.staging.yml exec -T postgres_staging pg_dump -U <POSTGRES_USER> <POSTGRES_DB> > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Automated Backup Script

```bash
#!/bin/bash
set -e

BACKUP_DIR="~/exam-platform-staging/backups"
POSTGRES_USER="${POSTGRES_USER_STAGING:-exam_user_staging}"
POSTGRES_DB="${POSTGRES_DB_STAGING:-exam_platform_staging}"
COMPOSE_FILE="docker-compose.staging.yml"

mkdir -p ${BACKUP_DIR}

# Create backup
BACKUP_FILE="${BACKUP_DIR}/backup_$(date +%Y%m%d_%H%M%S).sql"
docker compose -f ${COMPOSE_FILE} exec -T postgres_staging pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > ${BACKUP_FILE}

# Compress backup
gzip ${BACKUP_FILE}

# Remove backups older than 30 days
find ${BACKUP_DIR} -name "backup_*.sql.gz" -mtime +30 -delete

echo "Backup created: ${BACKUP_FILE}.gz"
```

### Verify Backup

```bash
# Check backup file exists and has content
ls -lh backups/backup_*.sql.gz

# Test restore to temporary database (optional, for verification)
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> -c "CREATE DATABASE test_restore;"
docker compose -f docker-compose.staging.yml exec -T postgres_staging psql -U <POSTGRES_USER> test_restore < backups/backup_YYYYMMDD_HHMMSS.sql
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> -c "DROP DATABASE test_restore;"
```

## Restore

### Restore from Backup

**⚠️ WARNING**: Restore will overwrite existing data. Always backup current state first.

```bash
# 1. Backup current state first!
docker compose -f docker-compose.staging.yml exec -T postgres_staging pg_dump -U <POSTGRES_USER> <POSTGRES_DB> > backup_before_restore_$(date +%Y%m%d_%H%M%S).sql

# 2. Stop backend to prevent writes
docker compose -f docker-compose.staging.yml stop backend_staging

# 3. Drop and recreate database (or restore to new database)
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> -c "DROP DATABASE IF EXISTS <POSTGRES_DB>;"
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> -c "CREATE DATABASE <POSTGRES_DB>;"

# 4. Restore from backup
# If backup is compressed:
gunzip -c backups/backup_YYYYMMDD_HHMMSS.sql.gz | docker compose -f docker-compose.staging.yml exec -T postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB>

# If backup is not compressed:
docker compose -f docker-compose.staging.yml exec -T postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> < backups/backup_YYYYMMDD_HHMMSS.sql

# 5. Verify restore
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"

# 6. Start backend
docker compose -f docker-compose.staging.yml start backend_staging

# 7. Verify backend can connect
sleep 10
curl -I https://<STAGING_DOMAIN>/api/v1/health
```

## Connection Troubleshooting

### Check Database Connectivity

```bash
# From backend container
docker compose -f docker-compose.staging.yml exec backend_staging python -c "from app.db.session import SessionLocal; db = SessionLocal(); db.execute('SELECT 1'); print('DB connection OK')"

# Direct connection test
docker compose -f docker-compose.staging.yml exec backend_staging ping postgres_staging
```

### Check Active Connections

```bash
# List active connections
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE datname = '<POSTGRES_DB>';"

# List all connections with details
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT pid, usename, application_name, client_addr, state, query FROM pg_stat_activity WHERE datname = '<POSTGRES_DB>';"
```

### Check Connection Limits

```bash
# Check max connections setting
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SHOW max_connections;"

# Check current connection count
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT count(*) FROM pg_stat_activity;"

# Check connection pool settings (if using SQLAlchemy)
# Check backend logs for connection pool errors
docker compose -f docker-compose.staging.yml logs backend_staging | grep -i "connection\|pool"
```

### Kill Idle Connections

```bash
# Kill idle connections older than 5 minutes
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '<POSTGRES_DB>' AND state = 'idle' AND state_change < now() - interval '5 minutes';"
```

### Check Locks

```bash
# List active locks
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT pid, locktype, relation::regclass, mode, granted FROM pg_locks WHERE NOT granted;"

# List blocking queries
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT blocked_locks.pid AS blocked_pid, blocking_locks.pid AS blocking_pid, blocked_activity.query AS blocked_query, blocking_activity.query AS blocking_query FROM pg_catalog.pg_locks blocked_locks JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid AND blocking_locks.pid != blocked_locks.pid JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid WHERE NOT blocked_locks.granted;"
```

## Performance Troubleshooting

### Check Slow Queries

```bash
# Enable slow query logging (if not already enabled)
# Check postgresql.conf or environment variables

# Check query performance
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%' ORDER BY duration DESC;"
```

### Check Database Size

```bash
# Database size
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT pg_size_pretty(pg_database_size('<POSTGRES_DB>'));"

# Table sizes
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

### Check Index Usage

```bash
# Index usage statistics
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes ORDER BY idx_scan;"
```

## Verification Checklist

After any database intervention:

1. **Database is accessible**:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend_staging python -c "from app.db.session import SessionLocal; db = SessionLocal(); db.execute('SELECT 1'); print('OK')"
   ```

2. **Backend can connect**:
   ```bash
   curl -s https://<STAGING_DOMAIN>/api/v1/ready | jq -r '.checks.db.status'
   # Expected: "ok"
   ```

3. **No connection pool errors**:
   ```bash
   docker compose -f docker-compose.staging.yml logs --since=5m backend_staging | grep -i "connection\|pool" | grep -i error
   # Expected: No output
   ```

4. **Active connections are reasonable**:
   ```bash
   docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname = '<POSTGRES_DB>';"
   # Expected: < 50 (adjust based on your connection pool settings)
   ```

5. **No long-running queries**:
   ```bash
   docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '1 minute';"
   # Expected: 0 or very low
   ```

## Related Runbooks

- [01-Incident-Checklist.md](./01-Incident-Checklist.md) - Incident triage
- [02-Rollback.md](./02-Rollback.md) - Rollback procedures
- [00-QuickStart.md](./00-QuickStart.md) - Quick health checks
