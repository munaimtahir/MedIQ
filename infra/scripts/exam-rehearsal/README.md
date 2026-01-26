# Exam-Day Rehearsal Scripts

This directory contains scripts and tools for conducting a full exam-day rehearsal, including load testing, failure injection, and data integrity verification.

## Overview

The exam-day rehearsal simulates realistic peak exam load (300-500 concurrent students) and verifies:
- No data loss
- No session corruption
- Graceful degradation under stress
- Automatic recovery
- Observability

## Prerequisites

1. **k6** (for load testing):
   ```bash
   # Install k6: https://k6.io/docs/getting-started/installation/
   # Windows: choco install k6
   # macOS: brew install k6
   # Linux: See k6 docs
   ```

2. **Docker Compose** (for failure injection):
   - Services must be running via `docker-compose.prod.yml`

3. **Authentication Token**:
   - Obtain a valid JWT token for load testing
   - Set as `AUTH_TOKEN` environment variable

4. **Staging Environment** (recommended):
   - Use staging for rehearsal, not production
   - Ensure staging mirrors production configuration

## Scripts

### Load Testing

#### `load-test-sessions.js`
Simulates session creation burst (300-400 users starting sessions within 5 minutes).

**Usage**:
```bash
export API_URL="https://api-staging.example.com"
export AUTH_TOKEN="your-jwt-token"
k6 run --vus 400 --duration 5m load-test-sessions.js
```

**Metrics**:
- Session creation success rate
- p50/p95/p99 latency
- Error rates

#### `load-test-answers.js`
Simulates steady answer submissions during exam (300 users over 30 minutes).

**Usage**:
```bash
export API_URL="https://api-staging.example.com"
export AUTH_TOKEN="your-jwt-token"
export SESSION_IDS="session-id-1,session-id-2,..."  # Optional: use existing sessions
k6 run --vus 300 --duration 30m load-test-answers.js
```

**Metrics**:
- Answer submission success rate
- p50/p95/p99 latency
- Error rates

#### `load-test-submit.js`
Simulates final submit spike (400 users submitting in last 10 minutes).

**Usage**:
```bash
export API_URL="https://api-staging.example.com"
export AUTH_TOKEN="your-jwt-token"
export SESSION_IDS="session-id-1,session-id-2,..."  # Required: sessions to submit
k6 run --vus 400 --duration 10m load-test-submit.js
```

**Metrics**:
- Submit success rate
- Double-submit handling (idempotency)
- p50/p95/p99 latency

### Failure Injection

#### `failure-injection.sh`
Injects various failure scenarios during load testing.

**Usage**:
```bash
# Redis failure (60 seconds)
./failure-injection.sh redis-stop          # Production
./failure-injection.sh redis-staging-stop  # Staging

# Backend worker restart
./failure-injection.sh backend-restart          # Production
./failure-injection.sh backend-staging-restart  # Staging

# Full backend restart
./failure-injection.sh full-backend-restart

# Network delay (experimental, requires tc/netem)
./failure-injection.sh network-delay

# Help
./failure-injection.sh help
```

**Expected Behavior**:
- Redis failure: Rate limits bypassed, auth works, warnings logged
- Backend restart: Other workers serve traffic, no lost answers
- Network delay: Traefik timeouts protect backend, clients retry

### Verification

#### `verify-exam-mode.sh`
Verifies that `EXAM_MODE=true` disables heavy operations.

**Usage**:
```bash
./verify-exam-mode.sh staging https://api-staging.example.com
./verify-exam-mode.sh prod https://api.example.com
```

**Checks**:
- EXAM_MODE environment variable
- Background job processes
- EXAM_MODE usage in logs
- Critical endpoints accessibility

#### `verify-data-integrity.sh`
Runs SQL checks to verify no data loss or corruption.

**Usage**:
```bash
./verify-data-integrity.sh staging
./verify-data-integrity.sh prod
```

**Checks**:
- Orphaned answers
- Duplicate submits
- Missing answers
- Unscored sessions
- Answer/question mismatches
- Orphaned events
- Inconsistent status
- Duplicate mastery updates

#### `capture-metrics.sh`
Captures observability metrics during/after rehearsal.

**Usage**:
```bash
./capture-metrics.sh ./rehearsal-metrics
```

**Captures**:
- Database connection pool usage
- Slow queries
- Slow requests
- Error rates
- Redis statistics
- Container resource usage
- Traefik metrics
- Session statistics
- Request ID samples

### Orchestration

#### `run-rehearsal.sh`
Orchestrates all phases of the rehearsal.

**Usage**:
```bash
./run-rehearsal.sh staging https://api-staging.example.com [auth-token]
```

**Phases**:
1. Pre-Exam Freeze (EXAM_MODE verification)
2. Load Generation (manual k6 runs)
3. Failure Injection (interactive)
4. Data Integrity Verification
5. Observability Review
6. Recovery Drill

**Output**: Generates rehearsal report in `reports/rehearsal_report_YYYYMMDD_HHMMSS.md`

## Workflow

### Full Rehearsal

1. **Prepare**:
   ```bash
   # Ensure staging is running
   docker compose -f infra/docker/compose/docker-compose.prod.yml ps
   
   # Get authentication token
   export AUTH_TOKEN="your-jwt-token"
   export API_URL="https://api-staging.example.com"
   ```

2. **Run Orchestrated Rehearsal**:
   ```bash
   cd infra/scripts/exam-rehearsal
   ./run-rehearsal.sh staging "$API_URL" "$AUTH_TOKEN"
   ```

3. **Manual Load Tests** (if not using orchestration):
   ```bash
   # Session creation
   k6 run --vus 400 --duration 5m load-test-sessions.js
   
   # Answer submissions (in parallel terminal)
   k6 run --vus 300 --duration 30m load-test-answers.js
   
   # Submit spike (after collecting session IDs)
   export SESSION_IDS="id1,id2,id3,..."
   k6 run --vus 400 --duration 10m load-test-submit.js
   ```

4. **Inject Failures** (during load):
   ```bash
   # In separate terminal, while load is running
   ./failure-injection.sh redis-staging-stop
   # Wait 60 seconds, observe behavior
   ```

5. **Verify Data Integrity**:
   ```bash
   ./verify-data-integrity.sh staging
   ```

6. **Capture Metrics**:
   ```bash
   ./capture-metrics.sh ./rehearsal-metrics-$(date +%Y%m%d)
   ```

7. **Review Report**:
   - Open `reports/rehearsal_report_*.md`
   - Complete GO/NO-GO checklist
   - Address any blockers

## Expected Results

### Performance Targets

- **p95 latency**: < 500ms (API endpoints)
- **Error rate**: < 1%
- **Database pool**: < 80% usage
- **Zero data loss**: All sessions and answers preserved
- **Idempotency**: Double-submits handled correctly

### Failure Scenarios

- **Redis failure**: Graceful degradation, no crashes
- **Backend restart**: Seamless failover, no lost data
- **Network delay**: Timeouts protect backend, clients retry

### Data Integrity

- Zero orphaned answers
- Zero duplicate submits
- Zero missing answers
- All sessions properly scored

## Troubleshooting

### k6 Installation Issues

**Windows**: Use Chocolatey or download from k6.io
**macOS**: Use Homebrew
**Linux**: Follow k6 installation guide

### Authentication Token

```bash
# Get token via API
curl -X POST https://api-staging.example.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'
```

### Script Permissions

On Linux/macOS:
```bash
chmod +x *.sh
```

On Windows (Git Bash):
```bash
# Scripts should work as-is
```

### Database Connection

If verification scripts fail:
```bash
# Check container name
docker ps | grep postgres

# Check environment variables
docker exec exam_platform_postgres_staging printenv | grep POSTGRES
```

## Related Documentation

- `docs/EXAM_DAY_RUNBOOK.md` - Exam day procedures
- `docs/EXAM_REHEARSAL_REPORT_TEMPLATE.md` - Report template
- `docs/PRODUCTION_HARDENING_SUMMARY.md` - Performance hardening
- `docs/runbook.md` - General operations

## Notes

- **Always use staging** for full rehearsal
- **Never run load tests against production** without explicit approval
- **Document all findings** in rehearsal report
- **Address blockers** before exam day
- **Update runbook** with lessons learned
