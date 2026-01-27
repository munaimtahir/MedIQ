# Incident Checklist

**Purpose**: Structured triage and response for production incidents.

## Severity Levels

### SEV-1: Critical (Service Down)
- **Definition**: Complete service outage, no users can access the platform
- **Response Time**: Immediate (within 15 minutes)
- **Examples**:
  - All endpoints returning 5xx errors
  - Database completely unavailable
  - Frontend not loading
  - Authentication completely broken

### SEV-2: High (Degraded Service)
- **Definition**: Significant functionality impaired, affecting many users
- **Response Time**: Within 1 hour
- **Examples**:
  - Slow response times (>5s p95)
  - Intermittent 5xx errors (>1% error rate)
  - Database connection pool exhausted
  - Redis unavailable (if required)
  - Specific features broken (sessions, submissions)

### SEV-3: Low (Minor Issues)
- **Definition**: Minor issues, workarounds available, limited user impact
- **Response Time**: Within 4 hours
- **Examples**:
  - Non-critical endpoints slow
  - Minor UI issues
  - Non-blocking feature bugs
  - Observability gaps

## Immediate Triage Steps

### Step 1: Assess Impact (2 minutes)

```bash
# Check service status
docker compose ps

# Check health endpoints
curl -I https://<STAGING_DOMAIN>/api/v1/health
curl -I https://<STAGING_DOMAIN>/

# Check error rate (if Prometheus available)
# Query: rate(http_requests_total{status=~"5.."}[5m])
```

**Questions to answer:**
- [ ] Is the service completely down or degraded?
- [ ] What percentage of users are affected?
- [ ] Is there a workaround available?
- [ ] When did the issue start? (check logs timestamps)

### Step 2: Check Recent Changes (2 minutes)

```bash
# Check recent deployments
docker compose ps --format "table {{.Name}}\t{{.Image}}\t{{.Status}}"

# Check recent logs for deployment markers
docker compose logs --since=1h backend_staging | grep -i "deploy\|migration\|upgrade"

# Check GitHub Actions (if accessible)
# Look for recent workflow runs in .github/workflows/staging.yml
```

**Questions to answer:**
- [ ] Was there a recent deployment?
- [ ] Was there a database migration?
- [ ] Was there a configuration change?
- [ ] Was there a dependency update?

### Step 3: Check Logs (3 minutes)

```bash
# Backend errors (last 10 minutes)
docker compose logs --since=10m backend_staging | grep -iE "(error|exception|traceback|failed)" | tail -50

# Frontend errors (last 10 minutes)
docker compose logs --since=10m frontend_staging | grep -iE "(error|exception|traceback|failed)" | tail -50

# Traefik errors (last 10 minutes)
docker compose logs --since=10m traefik | grep -iE "(error|exception|traceback|failed)" | tail -50

# Database errors
docker compose logs --since=10m postgres_staging | grep -iE "(error|exception|traceback|failed)" | tail -50
```

**Questions to answer:**
- [ ] What is the most common error message?
- [ ] Is there a stack trace?
- [ ] Are errors correlated with a specific endpoint?
- [ ] Are errors correlated with a specific user/request pattern?

### Step 4: Check Dependencies (3 minutes)

```bash
# Database connectivity
docker compose exec backend_staging python -c "from app.db.session import SessionLocal; db = SessionLocal(); db.execute('SELECT 1'); print('DB OK')"

# Redis connectivity (if enabled)
docker compose exec backend_staging python -c "from app.core.redis_client import is_redis_available; print('Redis OK' if is_redis_available() else 'Redis DOWN')"

# Check database connections
docker compose exec postgres_staging psql -U <POSTGRES_USER> -d <POSTGRES_DB> -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory
docker compose exec redis_staging redis-cli INFO memory | grep used_memory_human
```

**Questions to answer:**
- [ ] Is the database accessible?
- [ ] Is Redis accessible (if required)?
- [ ] Are connection pools exhausted?
- [ ] Are there resource constraints (CPU, memory, disk)?

## Decision Tree

### Mitigate vs Rollback vs Hotfix

```
┌─────────────────────────────────────────────────────────┐
│                    Incident Detected                     │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                              │
   ┌────▼────┐                   ┌─────▼─────┐
   │ Recent  │                   │ No Recent │
   │Deployment│                   │ Deployment│
   └────┬────┘                   └─────┬─────┘
        │                              │
   ┌────▼──────────────────────────────▼────┐
   │         Can we identify root cause?     │
   └────┬────────────────────────────────┬───┘
        │                                │
   ┌────▼────┐                      ┌────▼────┐
   │   Yes   │                      │   No   │
   └────┬────┘                      └────┬────┘
        │                                │
   ┌────▼────────────────────────────────▼────┐
   │     Is fix < 15 minutes?                │
   └────┬────────────────────────────────┬───┘
        │                                │
   ┌────▼────┐                      ┌────▼────┐
   │   Yes   │                      │   No   │
   └────┬────┘                      └────┬────┘
        │                                │
   ┌────▼────┐                      ┌────▼────┐
   │ Hotfix  │                      │ Rollback │
   └─────────┘                      └──────────┘
```

### Decision Criteria

**Rollback if:**
- Recent deployment (< 2 hours ago)
- Issue started immediately after deployment
- Root cause unclear or fix will take > 15 minutes
- SEV-1 or SEV-2 severity

**Mitigate if:**
- No recent deployment
- Root cause identified
- Quick fix available (< 15 minutes)
- Can be fixed without code changes (config, restart, etc.)

**Hotfix if:**
- Root cause identified
- Fix is simple and low-risk
- Can be deployed quickly (< 15 minutes)
- SEV-3 or low-impact SEV-2

## Immediate Actions by Severity

### SEV-1 Actions

1. **Declare incident** (notify team, create incident channel)
2. **Assess**: Follow triage steps above (5 minutes)
3. **Decide**: Rollback if recent deployment, else mitigate
4. **Execute**: Rollback or mitigation (see [02-Rollback.md](./02-Rollback.md))
5. **Verify**: Run verification checklist (5 minutes)
6. **Communicate**: Update status page/users

### SEV-2 Actions

1. **Assess**: Follow triage steps above (10 minutes)
2. **Decide**: Mitigate or rollback based on decision tree
3. **Execute**: Apply fix
4. **Verify**: Run verification checklist
5. **Monitor**: Watch metrics for 30 minutes

### SEV-3 Actions

1. **Assess**: Follow triage steps (15 minutes)
2. **Document**: Create ticket with findings
3. **Plan**: Schedule fix in next sprint
4. **Monitor**: Add to watchlist

## Verification Checklist

After any intervention:

1. **Containers are running**:
   ```bash
   docker compose ps | grep -E "(Up|healthy)"
   ```

2. **Health endpoints return 200**:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://<STAGING_DOMAIN>/api/v1/health
   curl -s -o /dev/null -w "%{http_code}" https://<STAGING_DOMAIN>/
   ```

3. **Readiness check passes**:
   ```bash
   curl -s https://<STAGING_DOMAIN>/api/v1/ready | jq -r '.status'
   # Expected: "ok" or "degraded" (not "down")
   ```

4. **Error rate is acceptable** (< 1%):
   ```bash
   # Check Prometheus or logs
   docker compose logs --since=5m backend_staging | grep -c "ERROR" || echo "0"
   ```

5. **No critical errors in last 5 minutes**:
   ```bash
   docker compose logs --since=5m backend_staging | grep -iE "(traceback|exception|critical)" | wc -l
   # Expected: 0 or very low
   ```

## Escalation

### When to Escalate

- SEV-1 not resolved within 30 minutes
- Root cause unclear after 1 hour of investigation
- Data loss or security breach suspected
- Multiple services affected
- External dependencies (database, CDN) are down

### Escalation Path

1. **On-call engineer** (first responder)
2. **Team lead** (if not resolved in 30 minutes)
3. **Engineering manager** (if not resolved in 1 hour)
4. **CTO/VP Engineering** (if SEV-1 persists > 2 hours)

## Post-Incident

### Immediate (within 1 hour)

- [ ] Service restored and verified
- [ ] Incident declared resolved
- [ ] Users notified (if applicable)
- [ ] Initial root cause documented

### Follow-up (within 24 hours)

- [ ] Post-mortem scheduled
- [ ] Root cause analysis completed
- [ ] Action items created
- [ ] Runbooks updated (if gaps found)

## Related Runbooks

- [02-Rollback.md](./02-Rollback.md) - Rollback procedures
- [03-Database.md](./03-Database.md) - Database troubleshooting
- [04-Redis.md](./04-Redis.md) - Redis troubleshooting
- [05-Traefik.md](./05-Traefik.md) - Traefik troubleshooting
- [06-Observability.md](./06-Observability.md) - Observability tools
- [07-Security.md](./07-Security.md) - Security incidents
