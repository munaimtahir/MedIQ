# k6 Load Testing

Load testing scripts for the exam platform using [k6](https://k6.io/).

## Overview

This directory contains k6 scripts for testing system behavior under load:

**Basic Tests:**
- **concurrent_sessions.js**: Simulates multiple users creating sessions, answering questions, and submitting concurrently
- **submit_spike.js**: Simulates a sudden spike in session submissions (e.g., exam deadline)

**Advanced Tests:**
- **cms_workflow.js**: Tests CMS workflow (create, update, submit, approve, publish questions) under load ✅ **NEW**
- **analytics_endpoints.js**: Tests analytics endpoint performance under concurrent queries ✅ **NEW**
- **stress_test.js**: Gradually increases load to find breaking points ✅ **NEW**
- **endurance_test.js**: Long-duration stability test (30+ minutes) ✅ **NEW**
- **capacity_planning.js**: Determines maximum concurrent users the system can handle ✅ **NEW**
- **rate_limiting.js**: Tests API rate limiting behavior under rapid requests ✅ **NEW**

## Prerequisites

- Docker and Docker Compose
- Backend service running (via docker-compose.dev.yml)
- Test user credentials (student account)

## Quick Start

### Using Docker Compose (Recommended)

1. **Ensure backend is running:**
   ```bash
   cd infra/docker/compose
   docker compose -f docker-compose.dev.yml up -d
   ```

2. **Run concurrent sessions test:**
   ```bash
   cd infra/ops/loadtest
   docker compose -f docker-compose.k6.yml run --rm k6
   ```

3. **Run submit spike test:**
   ```bash
   cd infra/ops/loadtest
   K6_SCRIPT=submit_spike.js docker compose -f docker-compose.k6.yml run --rm k6
   ```

4. **Or use Makefile:**
   ```bash
   cd infra/ops/loadtest
   make concurrent    # Basic concurrent sessions test
   make spike          # Basic spike test
   make cms            # CMS workflow load test
   make analytics      # Analytics endpoints load test
   make stress         # Stress test (find breaking points)
   make endurance      # Endurance test (30 min default)
   make capacity       # Capacity planning test
   make ratelimit      # Rate limiting behavior test
   ```

### Using k6 Locally

1. **Install k6:**
   ```bash
   # macOS
   brew install k6
   
   # Linux
   sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
   echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
   sudo apt-get update
   sudo apt-get install k6
   
   # Windows
   choco install k6
   ```

2. **Set environment variables:**
   ```bash
   export BASE_URL=http://localhost:8000
   export STUDENT_USER=student-1@example.com
   export STUDENT_PASS=StudentPass123!
   export VUS=10
   export DURATION=2m
   ```

3. **Run test:**
   ```bash
   cd infra/ops/loadtest/k6
   k6 run concurrent_sessions.js
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | Backend API base URL | `http://localhost:8000` |
| `STUDENT_USER` | Student email for testing | `student-1@example.com` |
| `STUDENT_PASS` | Student password | `StudentPass123!` |
| `ADMIN_USER` | Admin email (optional) | - |
| `ADMIN_PASS` | Admin password (optional) | - |
| `VUS` | Virtual users (concurrent sessions) | `10` |
| `DURATION` | Test duration | `2m` |
| `BASE_VUS` | Baseline VUs (spike test) | `5` |
| `SPIKE_VUS` | Spike VUs (spike test) | `50` |
| `X_TEST_RUN_ID` | Test run ID for correlation | Auto-generated |
| `K6_SCRIPT` | Script to run (docker only) | `concurrent_sessions.js` |

### Test Scripts

#### concurrent_sessions.js

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

**Usage:**
```bash
VUS=20 DURATION=5m k6 run concurrent_sessions.js
```

#### submit_spike.js

Simulates a sudden spike in session submissions.

**Stages:**
- Baseline: 1m at BASE_VUS
- Spike ramp up: 30s to SPIKE_VUS
- Sustained spike: 1m at SPIKE_VUS
- Spike ramp down: 30s to BASE_VUS
- Baseline: 1m at BASE_VUS

**Thresholds:**
- `http_req_failed < 2%` (spike tolerance)
- `http_req_duration p95 < 3000ms` (spike tolerance)
- `session_submit_duration p95 < 2000ms`
- Success rate > 90% (spike tolerance)

**Usage:**
```bash
BASE_VUS=5 SPIKE_VUS=100 k6 run submit_spike.js
```

## Interpreting Results

### Key Metrics

- **http_req_failed**: Percentage of failed requests (should be < 1-2%)
- **http_req_duration**: Request latency (p95 should be < 2-3s)
- **session_create_duration**: Time to create session (p95 < 1.5s)
- **answer_submit_duration**: Time to submit answer (p95 < 1s)
- **session_submit_duration**: Time to submit session (p95 < 1.5-2s)

### Example Output

```
✓ login status is 200
✓ create session status is 200
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

### Threshold Failures

If thresholds fail, k6 will exit with non-zero code:

```
ERRO[0005] thresholds on 'http_req_duration' have been crossed
```

This indicates performance degradation. Check:
- Backend logs for errors
- Database connection pool exhaustion
- Redis connection issues
- Resource limits (CPU, memory)

## Correlation with Observability

### Using X-Test-Run-ID

The test run ID is automatically included in all requests as `X-Test-Run-ID` header. Use this to correlate:

1. **In Prometheus/Grafana:**
   - Filter metrics by `X-Test-Run-ID` label (if instrumented)
   - View request rate and latency during test window

2. **In Tempo (Traces):**
   - Search traces with attribute `http.request.header.X-Test-Run-ID = <test_run_id>`
   - Analyze trace spans during load test

3. **In Logs:**
   ```bash
   # Find all logs for a test run
   docker compose logs backend | grep "X-Test-Run-ID: k6-1234567890"
   ```

### Example Correlation

```bash
# 1. Start test with known run ID
X_TEST_RUN_ID=loadtest-2026-01-27-001 docker compose -f docker-compose.k6.yml up

# 2. Query Prometheus for metrics during test window
# (In Grafana, filter by time range and test_run_id if available)

# 3. Search Tempo for traces
# (In Grafana Explore, search: {http.request.header.X-Test-Run-ID="loadtest-2026-01-27-001"})

# 4. Check logs
docker compose logs backend | grep "loadtest-2026-01-27-001"
```

## Advanced Usage

### Custom Test Scenarios

Create custom scripts based on `common.js`:

```javascript
import { login, createSession, submitAnswer, submitSession } from './common.js';

export default function () {
    const token = login(getBaseUrl(), email, password);
    // ... custom scenario
}
```

### Multiple User Pools

For more realistic testing, use CSV data files:

```javascript
import papaparse from 'https://jslib.k6.io/papaparse/5.1.1/index.js';
import { SharedArray } from 'k6/data';

const users = new SharedArray('users', function () {
    return papaparse.parse(open('./users.csv'), { header: true }).data;
});

export default function () {
    const user = users[__VU % users.length];
    const token = login(getBaseUrl(), user.email, user.password);
    // ...
}
```

### Output Formats

k6 supports multiple output formats:

```bash
# JSON output
k6 run --out json=results.json concurrent_sessions.js

# InfluxDB output (for Grafana)
k6 run --out influxdb=http://influxdb:8086/k6 concurrent_sessions.js

# Cloud output (k6 Cloud)
k6 cloud concurrent_sessions.js
```

## Troubleshooting

### Backend Not Accessible

**Error:** `Backend health check failed`

**Solution:**
- Ensure backend is running: `docker compose -f docker-compose.dev.yml ps`
- Check BASE_URL matches backend service name/port
- Verify network connectivity: `docker compose -f docker-compose.k6.yml exec k6 ping backend`

### Authentication Failures

**Error:** `Login failed: 401`

**Solution:**
- Verify STUDENT_USER and STUDENT_PASS are correct
- Check user exists and is active in database
- Ensure email is verified

### Threshold Failures

**Error:** `thresholds have been crossed`

**Solution:**
- Increase threshold values if acceptable for your use case
- Check backend resource usage (CPU, memory, DB connections)
- Review backend logs for errors or slow queries
- Consider scaling backend resources

### High Failure Rate

**Error:** `http_req_failed > 1%`

**Solution:**
- Reduce VUS (virtual users)
- Increase DURATION to spread load
- Check database connection pool size
- Review rate limiting configuration
- Check for backend errors in logs

## Best Practices

1. **Start Small**: Begin with low VUS (5-10) and short duration (1m)
2. **Gradual Increase**: Gradually increase load to find breaking points
3. **Monitor Resources**: Watch CPU, memory, DB connections during tests
4. **Correlate Metrics**: Use X-Test-Run-ID to correlate with observability stack
5. **Test Regularly**: Run load tests as part of CI/CD or before releases
6. **Document Baselines**: Record baseline metrics for comparison

## Example Commands

### Basic Concurrent Sessions Test
```bash
cd infra/ops/loadtest
BASE_URL=http://backend:8000 \
STUDENT_USER=student-1@example.com \
STUDENT_PASS=StudentPass123! \
VUS=20 \
DURATION=5m \
docker compose -f docker-compose.k6.yml run --rm k6
```

### Submit Spike Test
```bash
cd infra/ops/loadtest
BASE_URL=http://backend:8000 \
STUDENT_USER=student-1@example.com \
STUDENT_PASS=StudentPass123! \
BASE_VUS=5 \
SPIKE_VUS=100 \
K6_SCRIPT=submit_spike.js \
docker compose -f docker-compose.k6.yml run --rm k6
```

### With Custom Test Run ID (for correlation)
```bash
cd infra/ops/loadtest
X_TEST_RUN_ID=loadtest-2026-01-27-001 \
BASE_URL=http://backend:8000 \
docker compose -f docker-compose.k6.yml run --rm k6
```

## Advanced Test Scenarios

### CMS Workflow Load Test

Tests CMS system under concurrent admin operations:

```bash
cd infra/ops/loadtest
ADMIN_USER=admin-1@example.com \
ADMIN_PASS=AdminPass123! \
make cms
```

**What it tests:**
- Concurrent question creation
- Question updates
- Workflow transitions (submit → approve → publish)
- CMS endpoint performance

### Analytics Endpoints Load Test

Tests analytics computation under concurrent queries:

```bash
cd infra/ops/loadtest
make analytics
```

**What it tests:**
- Analytics overview endpoint
- Block-specific analytics
- Theme-specific analytics
- Query performance under load

### Stress Test

Finds system breaking points by gradually increasing load:

```bash
cd infra/ops/loadtest
make stress
```

**What it tests:**
- Maximum concurrent users
- System failure modes
- Error handling under stress
- Recovery behavior

### Endurance Test

Long-duration stability test (default 30 minutes):

```bash
cd infra/ops/loadtest
make endurance
# Or with custom duration:
DURATION=60m make endurance
```

**What it tests:**
- Memory leaks
- Connection pool exhaustion
- Long-running stability
- Resource cleanup

### Capacity Planning Test

Determines maximum concurrent users:

```bash
cd infra/ops/loadtest
make capacity
```

**What it tests:**
- System capacity limits
- Performance degradation points
- Optimal concurrent user count

### Rate Limiting Test

Tests API rate limiting behavior:

```bash
cd infra/ops/loadtest
make ratelimit
```

**What it tests:**
- Rate limiting triggers correctly
- System stability under rate limiting
- Error handling for rate-limited requests

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
- [ ] Add stress testing scenarios (find breaking points)
- [ ] Add endurance testing (long-duration stability)
- [ ] Add spike testing with different patterns (gradual, sudden, sustained)
- [ ] Add capacity planning tests (determine max concurrent users)
- [ ] Add database connection pool stress tests
- [ ] Add Redis cache hit/miss ratio tests
- [ ] Add API rate limiting behavior tests
- [ ] Add session expiry handling under load
- [ ] Add concurrent session creation limits
- [ ] Add learning engine update throughput tests
- [ ] Add analytics computation performance tests
