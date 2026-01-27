# Task 164: k6 Load Testing - COMPLETE

## Summary

Added k6 load testing infrastructure for concurrent sessions, submit spike, and advanced performance testing scenarios.

**Total Scripts: 8**
- 2 basic tests (concurrent_sessions, submit_spike)
- 6 advanced tests (cms_workflow, analytics_endpoints, stress_test, endurance_test, capacity_planning, rate_limiting)

## Files Added

### k6 Scripts
- `k6/common.js` - Shared utilities (login, session creation, answer submission, etc.)
- `k6/concurrent_sessions.js` - Concurrent sessions load test
- `k6/submit_spike.js` - Submit spike load test
- `k6/cms_workflow.js` - CMS workflow load test ✅ **NEW**
- `k6/analytics_endpoints.js` - Analytics endpoints load test ✅ **NEW**
- `k6/stress_test.js` - Stress test (find breaking points) ✅ **NEW**
- `k6/endurance_test.js` - Endurance test (long-duration stability) ✅ **NEW**
- `k6/capacity_planning.js` - Capacity planning test ✅ **NEW**
- `k6/rate_limiting.js` - Rate limiting behavior test ✅ **NEW**

### Infrastructure
- `docker-compose.k6.yml` - Docker Compose configuration for k6
- `Makefile` - Convenience commands for running tests
- `.gitignore` - Ignore test results

### Documentation
- `README.md` - Comprehensive load testing guide

## Test Scripts

### concurrent_sessions.js

Simulates multiple users completing sessions concurrently.

**Stages:**
- Ramp up: 30s to target VUs
- Sustained load: Duration (default 2m) at target VUs
- Ramp down: 30s to 0

**Thresholds:**
- `http_req_failed < 1%`
- `http_req_duration p95 < 2000ms`
- `session_create_duration p95 < 1500ms`
- `answer_submit_duration p95 < 1000ms`
- `session_submit_duration p95 < 1500ms`
- Success rates > 95%

**User Flow:**
1. Login
2. Create session (10 questions)
3. Get session state
4. Answer 70-100% of questions (with think time 2-6s)
5. Submit session

### submit_spike.js

Simulates a sudden spike in session submissions.

**Stages:**
- Baseline: 1m at BASE_VUS (default 5)
- Spike ramp up: 30s to SPIKE_VUS (default 50)
- Sustained spike: 1m at SPIKE_VUS
- Spike ramp down: 30s to BASE_VUS
- Baseline: 1m at BASE_VUS

**Thresholds:**
- `http_req_failed < 2%` (spike tolerance)
- `http_req_duration p95 < 3000ms` (spike tolerance)
- `session_submit_duration p95 < 2000ms`
- Success rate > 90% (spike tolerance)

**User Flow:**
1. Login
2. Create session (5 questions)
3. Get session state
4. Answer all questions quickly (minimal think time 0.5-1.5s)
5. Submit session (spike)

### cms_workflow.js ✅ **NEW**

Simulates admin users completing CMS workflow under load.

**Stages:**
- Ramp up: 30s to target VUs (default 5)
- Sustained load: Duration (default 3m) at target VUs
- Ramp down: 30s to 0

**Thresholds:**
- `http_req_failed < 1%`
- `question_create_duration p95 < 1500ms`
- `question_update_duration p95 < 1000ms`
- `question_publish_duration p95 < 2000ms`
- Success rates > 95%

**User Flow:**
1. Login as admin
2. Create question (DRAFT)
3. Update question
4. Submit for review
5. Approve question
6. Publish question

### analytics_endpoints.js ✅ **NEW**

Tests analytics endpoint performance under concurrent queries.

**Stages:**
- Ramp up: 30s to target VUs (default 10)
- Sustained load: Duration (default 2m) at target VUs
- Ramp down: 30s to 0

**Thresholds:**
- `analytics_overview_duration p95 < 1500ms`
- `analytics_block_duration p95 < 1500ms`
- `analytics_theme_duration p95 < 1500ms`
- Success rates > 95%

**User Flow:**
1. Login
2. Query analytics endpoints (overview, block, theme - randomly selected)

### stress_test.js ✅ **NEW**

Gradually increases load to find breaking points.

**Stages:**
- Start: 10 VUs
- Gradually increase: 20 → 50 → 100 → 150 → 200 VUs
- Ramp down: 0

**Thresholds:**
- More lenient (stress test):
  - `http_req_failed < 10%`
  - `http_req_duration p95 < 5000ms`
  - Success rates > 80%

**User Flow:**
1. Login
2. Create session (5 questions)
3. Answer questions quickly (minimal think time)
4. Submit session

### endurance_test.js ✅ **NEW**

Long-duration stability test (default 30 minutes).

**Stages:**
- Ramp up: 2m to target VUs (default 20)
- Sustained load: Duration (default 30m) at target VUs
- Ramp down: 2m to 0

**Thresholds:**
- `http_req_failed < 1%`
- `http_req_duration p95 < 2000ms` (should remain stable)
- Success rates > 95%

**User Flow:**
1. Login
2. Complete multiple sessions (3-5 per iteration)
3. Repeat for extended duration

**Purpose:** Tests for memory leaks, connection pool exhaustion, long-running stability.

### capacity_planning.js ✅ **NEW**

Determines maximum concurrent users the system can handle.

**Stages:**
- Gradually increase: 10 → 25 → 50 → 75 → 100 → 150 → 200 → 250 VUs
- Ramp down: 0

**Thresholds:**
- `http_req_failed < 5%` (at capacity)
- `http_req_duration p95 < 3000ms`
- Success rates > 90% (at capacity)

**User Flow:**
1. Login
2. Create session (10 questions)
3. Answer 80% of questions
4. Submit session

**Purpose:** Find the maximum number of concurrent users before system degrades.

### rate_limiting.js ✅ **NEW**

Tests API rate limiting behavior under rapid requests.

**Stages:**
- Start: 5 VUs
- Rapid increase: 20 → 50 VUs
- Ramp down: 0

**Thresholds:**
- `rate_limited > 5%` (expect rate limiting under high load)
- `login_success > 50%` (at least 50% should succeed)

**User Flow:**
1. Make multiple rapid login attempts (5-10 per VU)
2. Very short pauses (0.1-0.3s)

**Purpose:** Verify rate limiting works correctly and doesn't break system.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | Backend API base URL | `http://localhost:8000` |
| `STUDENT_USER` | Student email | `student-1@example.com` |
| `STUDENT_PASS` | Student password | `StudentPass123!` |
| `ADMIN_USER` | Admin email (optional) | - |
| `ADMIN_PASS` | Admin password (optional) | - |
| `VUS` | Virtual users | `10` |
| `DURATION` | Test duration | `2m` |
| `BASE_VUS` | Baseline VUs (spike) | `5` |
| `SPIKE_VUS` | Spike VUs | `50` |
| `X_TEST_RUN_ID` | Test run ID for correlation | Auto-generated |
| `K6_SCRIPT` | Script to run (docker) | `concurrent_sessions.js` |

## Commands to Run

### Docker Compose (Recommended)

**Concurrent Sessions:**
```bash
cd infra/ops/loadtest
docker compose -f docker-compose.k6.yml run --rm k6
```

**Submit Spike:**
```bash
cd infra/ops/loadtest
K6_SCRIPT=submit_spike.js docker compose -f docker-compose.k6.yml run --rm k6
```

**CMS Workflow:**
```bash
cd infra/ops/loadtest
make cms
# Or:
K6_SCRIPT=cms_workflow.js docker compose -f docker-compose.k6.yml run --rm k6
```

**Analytics Endpoints:**
```bash
cd infra/ops/loadtest
make analytics
```

**Stress Test:**
```bash
cd infra/ops/loadtest
make stress
```

**Endurance Test:**
```bash
cd infra/ops/loadtest
make endurance
# Default duration is 30m, override with:
DURATION=60m make endurance
```

**Capacity Planning:**
```bash
cd infra/ops/loadtest
make capacity
```

**Rate Limiting:**
```bash
cd infra/ops/loadtest
make ratelimit
```

### Using Makefile

All tests can be run via Makefile:

```bash
cd infra/ops/loadtest
make concurrent    # Basic concurrent sessions
make spike         # Basic spike test
make cms           # CMS workflow load test
make analytics     # Analytics endpoints load test
make stress        # Stress test (find breaking points)
make endurance     # Endurance test (30 min default)
make capacity      # Capacity planning test
make ratelimit     # Rate limiting behavior test
```

**With Custom Parameters:**
```bash
cd infra/ops/loadtest
BASE_URL=http://backend:8000 \
STUDENT_USER=student-1@example.com \
STUDENT_PASS=StudentPass123! \
VUS=20 \
DURATION=5m \
docker compose -f docker-compose.k6.yml run --rm k6
```

**With Test Run ID (for correlation):**
```bash
cd infra/ops/loadtest
X_TEST_RUN_ID=loadtest-2026-01-27-001 \
BASE_URL=http://backend:8000 \
docker compose -f docker-compose.k6.yml run --rm k6
```


### Local k6 Installation

```bash
cd infra/ops/loadtest/k6
BASE_URL=http://localhost:8000 \
STUDENT_USER=student-1@example.com \
STUDENT_PASS=StudentPass123! \
VUS=10 \
DURATION=2m \
k6 run concurrent_sessions.js
```

## Verification

### Check Test Results

Results are saved to `k6-results/` directory:
- `k6-results.json` - Detailed results in JSON format
- `k6-summary.json` - Summary metrics

### Verify Backend is Accessible

```bash
# From k6 container
docker compose -f docker-compose.k6.yml exec k6 wget -qO- http://backend:8000/v1/health

# Or from host
curl http://localhost:8000/v1/health
```

### Check Prometheus Targets

```bash
# Access Prometheus UI
open http://localhost:9090

# Check targets are UP
# Navigate to Status > Targets
```

### Correlate with Observability

**Using X-Test-Run-ID:**

1. **In Tempo (Traces):**
   - Search: `{http.request.header.X-Test-Run-ID="loadtest-2026-01-27-001"}`
   - View trace spans during load test window

2. **In Prometheus/Grafana:**
   - Filter metrics by time range matching test window
   - View request rate, latency, error rate

3. **In Logs:**
   ```bash
   docker compose -f docker-compose.dev.yml logs backend | grep "X-Test-Run-ID: loadtest-2026-01-27-001"
   ```

## Expected Output

### Successful Test Run

```
Starting concurrent sessions load test
Base URL: http://backend:8000
Test Run ID: k6-1738000000000-abc123
VUs: 10
Duration: 2m

     ✓ login status is 200
     ✓ create session status is 200
     ✓ get session status is 200
     ✓ submit answer status is 200
     ✓ submit session status is 200

     checks.........................: 100.00% ✓ 4000      ✗ 0
     data_received..................: 2.5 MB  20 kB/s
     data_sent......................: 1.2 MB  10 kB/s
     http_req_duration..............: avg=450ms   min=120ms   med=380ms   max=2100ms   p(95)=1200ms
     http_req_failed................: 0.00%   ✓ 0        ✗ 0
     session_create_duration........: avg=320ms   min=150ms   med=280ms   max=1200ms   p(95)=1100ms
     session_submit_duration........: avg=280ms   min=100ms   med=240ms   max=800ms    p(95)=650ms
```

### Threshold Failure

```
ERRO[0005] thresholds on 'http_req_duration' have been crossed
```

This indicates performance degradation. Check backend logs and resource usage.

## Features

- **Environment-driven**: All configuration via env vars
- **Resilient**: Checks response codes and aborts VU on critical failures
- **Correlation**: X-Test-Run-ID header for observability correlation
- **Realistic**: Includes think time to simulate user behavior
- **Thresholds**: Configurable performance gates
- **Docker-ready**: Runs in same network as backend

## Advanced Performance Tests Summary ✅

### New k6 Scripts Added

1. **cms_workflow.js** - CMS workflow load testing
   - Tests concurrent question creation, updates, and publishing
   - Admin user operations under load
   - Workflow transitions (DRAFT → IN_REVIEW → APPROVED → PUBLISHED)

2. **analytics_endpoints.js** - Analytics endpoint load testing
   - Concurrent analytics queries
   - Overview, block, and theme analytics
   - Query performance under load

3. **stress_test.js** - Stress testing (find breaking points)
   - Gradually increases load: 10 → 200 VUs
   - Tests system limits and failure modes
   - More lenient thresholds for stress scenarios

4. **endurance_test.js** - Endurance testing (long-duration stability)
   - Default 30-minute sustained load
   - Tests for memory leaks and connection pool exhaustion
   - Long-running stability verification

5. **capacity_planning.js** - Capacity planning tests
   - Gradually increases load: 10 → 250 VUs
   - Determines maximum concurrent users
   - Identifies performance degradation points

6. **rate_limiting.js** - API rate limiting behavior tests
   - Rapid requests to trigger rate limiting
   - Verifies rate limiting works correctly
   - Tests system stability under rate limiting

### Test Coverage

**Total k6 Scripts: 8**
- 2 basic tests (concurrent_sessions, submit_spike)
- 6 advanced tests (cms_workflow, analytics_endpoints, stress_test, endurance_test, capacity_planning, rate_limiting)

**All scripts:**
- Use shared `common.js` utilities
- Support environment variable configuration
- Include proper thresholds and metrics
- Work with Docker Compose setup
- Can be run via Makefile commands

## TODO Checklist for Task 165

- [x] Add k6 scripts for CMS workflow load testing ✅
- [x] Add k6 scripts for analytics endpoint load testing ✅
- [ ] Add k6 scripts for learning engine computation load testing
- [ ] Add CSV data file support for multiple test users
- [ ] Add k6 Cloud integration for distributed load testing
- [ ] Add InfluxDB output for real-time Grafana dashboards
- [ ] Add performance regression detection (compare against baseline)
- [ ] Add automated load testing in CI/CD pipeline
- [ ] Add chaos engineering scenarios (network failures, DB timeouts)
- [x] Add stress testing scenarios (find breaking points) ✅
- [x] Add endurance testing (long-duration stability) ✅
- [x] Add spike testing with different patterns (gradual, sudden, sustained) ✅
- [x] Add capacity planning tests (determine max concurrent users) ✅
- [ ] Add database connection pool stress tests
- [ ] Add Redis cache hit/miss ratio tests
- [x] Add API rate limiting behavior tests ✅
- [ ] Add session expiry handling under load
- [ ] Add concurrent session creation limits
- [ ] Add learning engine update throughput tests
- [ ] Add analytics computation performance tests
