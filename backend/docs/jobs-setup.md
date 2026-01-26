# Job System Setup

## Overview

The job system runs scheduled tasks (e.g., revision queue regeneration at 2am) using a CLI-based approach that can be triggered via cron.

## Migration

Before running jobs, ensure the database is up to date. **Use Docker only** (no virtual environments):

```bash
# From project root, with stack running
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend alembic upgrade head
```

## Crontab Setup

### Docker/Container (Recommended)

If running in a container, add to your docker-compose.yml or use a cron container:

```yaml
services:
  cron:
    image: your-backend-image
    command: >
      sh -c "
      echo '0 2 * * * cd /app && python -m app.jobs.run revision_queue_regen' | crontab -
      crond -f
      "
```

## Manual Execution

For testing or manual runs (**Docker only**):

```bash
# From project root, with stack running
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend python -m app.jobs.run revision_queue_regen
```

## Job Locking

Jobs use database-based locking to prevent concurrent execution:
- Lock duration: 120 minutes (configurable via `JOB_LOCK_DURATION_MINUTES`)
- If a job is already running, subsequent attempts will skip with a warning

## Monitoring

Check job status via admin API:

```bash
GET /v1/admin/queues/stats
```

This returns the last job run status, including:
- Status (QUEUED, RUNNING, SUCCEEDED, FAILED)
- Start/finish times
- Statistics (processed_users, due_items, etc.)
- Error messages (if failed)

## Troubleshooting

### Job not running

1. Check cron/container logs
2. Verify backend container can reach Postgres
3. Check database connection
4. Verify job lock is not stuck (check `job_lock` table)

### Job stuck

If a job appears stuck (status = RUNNING but no recent activity):

```sql
-- Check lock expiration
SELECT * FROM job_lock WHERE locked_until < NOW();

-- Manually release lock (if needed)
UPDATE job_lock SET locked_until = NOW() - INTERVAL '1 minute' WHERE job_key = 'revision_queue_regen';
```

### Job failing

Check `job_run` table for error details:

```sql
SELECT error_text, stats_json FROM job_run 
WHERE job_key = 'revision_queue_regen' 
ORDER BY created_at DESC 
LIMIT 1;
```
