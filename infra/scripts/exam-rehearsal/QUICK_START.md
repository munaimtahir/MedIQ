# Exam-Day Rehearsal Quick Start

## Prerequisites

1. **k6 installed**: https://k6.io/docs/getting-started/installation/
2. **Staging environment running**
3. **Authentication token** (JWT)

## 5-Minute Quick Test

```bash
# 1. Set environment
export API_URL="https://api-staging.example.com"
export AUTH_TOKEN="your-jwt-token"

# 2. Enable EXAM_MODE
export EXAM_MODE=true
docker compose -f infra/docker/compose/docker-compose.prod.yml up -d backend_staging

# 3. Verify EXAM_MODE
cd infra/scripts/exam-rehearsal
./verify-exam-mode.sh staging "$API_URL"

# 4. Run quick load test (5 minutes, 100 users)
k6 run --vus 100 --duration 5m load-test-sessions.js

# 5. Check results
./capture-metrics.sh ./quick-test-metrics
```

## Full Rehearsal (Recommended)

```bash
# Run orchestrated rehearsal
./run-rehearsal.sh staging "$API_URL" "$AUTH_TOKEN"

# Follow prompts for:
# - Load tests (manual k6 runs)
# - Failure injection
# - Data integrity verification
```

## Manual Load Tests

```bash
# Terminal 1: Session creation
k6 run --vus 400 --duration 5m load-test-sessions.js

# Terminal 2: Answer submissions (after sessions created)
export SESSION_IDS="id1,id2,id3,..."  # From Terminal 1 output
k6 run --vus 300 --duration 30m load-test-answers.js

# Terminal 3: Submit spike (final 10 minutes)
k6 run --vus 400 --duration 10m load-test-submit.js
```

## Failure Injection (During Load)

```bash
# In separate terminal, while load is running:
./failure-injection.sh redis-staging-stop
# Wait 60 seconds, observe behavior
```

## Verification

```bash
# Data integrity
./verify-data-integrity.sh staging

# Metrics
./capture-metrics.sh ./rehearsal-metrics-$(date +%Y%m%d)
```

## Expected Output

- **k6**: Success rate > 99%, p95 < 500ms
- **Data integrity**: Zero issues found
- **Metrics**: All within acceptable ranges

## Troubleshooting

**k6 not found**: Install from https://k6.io/docs/getting-started/installation/
**Auth token expired**: Get new token via login endpoint
**Scripts not executable**: On Linux/macOS: `chmod +x *.sh`

## Next Steps

1. Review `docs/EXAM_DAY_RUNBOOK.md` for exam day procedures
2. Complete `docs/EXAM_REHEARSAL_REPORT_TEMPLATE.md` with results
3. Make GO/NO-GO decision based on findings
