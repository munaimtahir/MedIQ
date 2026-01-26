# Exam-Day Runbook

**Purpose**: Step-by-step procedures for exam day operations

**Last Updated**: January 2026

---

## Pre-Exam Checklist (24 Hours Before)

### Infrastructure
- [ ] Verify all services are healthy: `docker compose -f infra/docker/compose/docker-compose.prod.yml ps`
- [ ] Check database backups are current
- [ ] Verify Traefik certificates are valid (not expiring soon)
- [ ] Confirm DNS records are correct
- [ ] Test staging environment (if available)

### Configuration
- [ ] Set `EXAM_MODE=true` in production environment
- [ ] Verify `EXAM_MODE` is respected by application
- [ ] Disable any cron jobs or scheduled tasks
- [ ] Verify rate limits are appropriate
- [ ] Check container resource limits are set

### Monitoring
- [ ] Verify observability tools are working
- [ ] Test alerting (if configured)
- [ ] Confirm log aggregation is functioning
- [ ] Check dashboard access (Traefik, if needed)

### Communication
- [ ] Notify team of exam schedule
- [ ] Confirm on-call rotation
- [ ] Share emergency contacts
- [ ] Prepare status page (if public)

---

## Exam-Day Freeze (1 Hour Before)

### Enable Exam Mode
```bash
# Set EXAM_MODE=true
export EXAM_MODE=true

# Restart backend to apply
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d backend

# Verify
docker exec exam_platform_backend printenv EXAM_MODE
# Should output: true
```

### Disable Background Jobs
```bash
# Check for running background processes
docker exec exam_platform_backend ps aux | grep -E "(cron|celery|worker)"

# If any found, stop them (method depends on your setup)
# Example: docker exec exam_platform_backend pkill -f "celery"
```

### Verify Critical Endpoints
```bash
# Health check
curl https://api.<DOMAIN>/health

# Readiness check
curl https://api.<DOMAIN>/v1/ready

# Both should return 200 OK
```

### Final System Check
```bash
# Database connections
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE datname = 'exam_platform';
"
# Should be < 20 (pool_size + max_overflow)

# Container resources
docker stats --no-stream

# Traefik routers
docker logs exam_platform_traefik --tail=50 | grep -i router
```

---

## During Exam

### Monitoring

**Key Metrics to Watch**:
- Request latency (p95 should be < 500ms)
- Error rates (should be < 1%)
- Database connection pool usage (should be < 80%)
- Container CPU/memory usage
- Redis connection status

**Commands**:
```bash
# Real-time container stats
docker stats

# Recent errors
docker logs exam_platform_backend --tail=100 | grep -E "error|ERROR|5[0-9]{2}"

# Slow requests
docker logs exam_platform_backend --tail=100 | grep "total_ms" | grep -E ">500|>1500"

# Database pool
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
SELECT count(*) as connections 
FROM pg_stat_activity 
WHERE datname = 'exam_platform';
"
```

### Common Issues

#### High Latency
1. Check database connection pool: `docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'exam_platform';"`
2. Check slow queries: `docker logs exam_platform_backend --tail=500 | grep "slow_sql"`
3. Check container resources: `docker stats --no-stream`
4. If pool exhausted: Consider temporarily increasing `pool_size` (requires restart)

#### High Error Rate
1. Check logs: `docker logs exam_platform_backend --tail=200 | grep -E "error|ERROR"`
2. Check Traefik: `docker logs exam_platform_traefik --tail=100`
3. Verify Redis: `docker exec exam_platform_redis redis-cli ping`
4. Check database: `docker exec exam_platform_postgres pg_isready -U exam_user`

#### Redis Failure
- **Expected**: Rate limiting temporarily bypassed, auth still works
- **Action**: Monitor logs for warnings, Redis will auto-recover
- **If persistent**: Restart Redis: `docker compose -f infra/docker/compose/docker-compose.prod.yml restart redis`

#### Backend Worker Failure
- **Expected**: Other workers continue serving traffic
- **Action**: Monitor for recovery, restart if needed: `docker compose -f infra/docker/compose/docker-compose.prod.yml restart backend`

---

## Post-Exam

### Data Integrity Verification

```bash
# Run integrity checks
./infra/scripts/exam-rehearsal/verify-data-integrity.sh prod

# Review output for any issues
```

### Disable Exam Mode

```bash
# Set EXAM_MODE=false
export EXAM_MODE=false

# Restart backend
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d backend

# Re-enable background jobs (if applicable)
# [Your method to re-enable jobs]
```

### Capture Metrics

```bash
# Capture final metrics
./infra/scripts/exam-rehearsal/capture-metrics.sh ./exam-metrics-$(date +%Y%m%d)
```

### Post-Mortem

1. Review error logs
2. Analyze slow queries
3. Check data integrity results
4. Document any issues
5. Update runbook with lessons learned

---

## Emergency Procedures

### Full System Restart

**⚠️ WARNING**: Only if absolutely necessary

```bash
# Stop all services
docker compose -f infra/docker/compose/docker-compose.prod.yml down

# Start infrastructure first
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d postgres redis traefik

# Wait for health checks
sleep 30

# Start application services
docker compose -f infra/docker/compose/docker-compose.prod.yml \
  up -d backend frontend

# Verify
curl https://api.<DOMAIN>/health
curl https://api.<DOMAIN>/v1/ready
```

### Database Issues

**If database is unresponsive**:
1. Check container: `docker ps | grep postgres`
2. Check logs: `docker logs exam_platform_postgres --tail=100`
3. Check disk space: `docker exec exam_platform_postgres df -h`
4. If needed, restart: `docker compose -f infra/docker/compose/docker-compose.prod.yml restart postgres`

**If data corruption suspected**:
1. **STOP**: Do not make changes
2. Capture logs: `docker logs exam_platform_postgres > postgres_logs_$(date +%Y%m%d_%H%M%S).log`
3. Contact database administrator
4. Consider restoring from backup if critical

### Rollback Plan

**If critical issue requires rollback**:

1. **Stop accepting new sessions** (if possible via feature flag)
2. **Allow existing sessions to complete** (do not interrupt)
3. **After all sessions complete**:
   ```bash
   # Revert to previous deployment
   git checkout <previous-stable-tag>
   docker compose -f infra/docker/compose/docker-compose.prod.yml \
     up -d --build backend frontend
   ```
4. **Verify**: `curl https://api.<DOMAIN>/health`

---

## Emergency Contacts

### On-Call Rotation
- **Primary**: [Name] - [Phone] - [Email]
- **Secondary**: [Name] - [Phone] - [Email]
- **Database Admin**: [Name] - [Phone] - [Email]
- **Infrastructure**: [Name] - [Phone] - [Email]

### Escalation Path
1. **Level 1**: On-call engineer (handles common issues)
2. **Level 2**: Team lead (for complex issues)
3. **Level 3**: CTO/Principal Engineer (for critical failures)

---

## Recovery Verification

After any incident or restart:

1. **Health Checks**:
   ```bash
   curl https://api.<DOMAIN>/health
   curl https://api.<DOMAIN>/v1/ready
   ```

2. **Data Integrity**:
   ```bash
   ./infra/scripts/exam-rehearsal/verify-data-integrity.sh prod
   ```

3. **Session Continuity**:
   - Verify students can resume sessions
   - Check no answers were lost
   - Confirm submissions are recorded

4. **Observability**:
   - Check logs for errors
   - Verify metrics are being captured
   - Confirm request IDs are traceable

---

## Lessons Learned Template

After each exam, document:

- **Date**: [Date]
- **Issues Encountered**: [List]
- **Resolution**: [How resolved]
- **Prevention**: [How to prevent in future]
- **Runbook Updates**: [What to add/change]

---

## Related Documentation

- `docs/PRODUCTION_HARDENING_SUMMARY.md` - Performance hardening details
- `docs/runbook.md` - General operations runbook
- `infra/scripts/exam-rehearsal/` - Rehearsal scripts
- `docs/observability.md` - Observability and logging
