# Observability Runbook

**Purpose**: How to use Grafana, Prometheus, Tempo, and logs to diagnose issues.

## Prerequisites

- Access to Grafana (http://localhost:3001 or configured URL)
- Access to Prometheus (http://localhost:9090 or configured URL)
- Access to Tempo (http://localhost:3200 or configured URL)
- Understanding of request_id and trace_id correlation

## Where to Look

### Grafana Dashboards

**Access**: http://localhost:3001 (or configured URL)

**Key Dashboards:**

1. **Traefik Edge Overview** (`traefik-edge-overview`)
   - RPS by entrypoint
   - Latency p95 by entrypoint
   - 4xx/5xx error rate
   - Top 10 routers by RPS

2. **FastAPI API Overview** (`fastapi-api-overview`)
   - RPS by HTTP method
   - Latency p95 by route
   - 4xx/5xx error rate by route
   - Top 10 slowest routes

3. **Data Layer Basics** (`data-layer-basics`)
   - Container status
   - Prometheus scrape targets status
   - Database/Redis metrics (if exporters configured)

**How to Use:**

```bash
# Access Grafana
open http://localhost:3001
# Or: curl http://localhost:3001

# Login (default: admin/admin, change in production!)
# Navigate to Dashboards → Browse
# Select dashboard from list
```

### Prometheus

**Access**: http://localhost:9090 (or configured URL)

**Key Queries:**

```promql
# Error rate (5xx)
rate(http_requests_total{status=~"5.."}[5m])

# Request rate
rate(http_requests_total[5m])

# Latency p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Database query time
rate(db_query_duration_seconds_sum[5m]) / rate(db_query_duration_seconds_count[5m])

# Redis operations
rate(redis_commands_total[5m])
```

**How to Use:**

```bash
# Access Prometheus
open http://localhost:9090
# Or: curl http://localhost:9090

# Navigate to Graph
# Enter query in query box
# Click Execute
# View results in graph or table
```

### Tempo (Distributed Tracing)

**Access**: http://localhost:3200 (or configured URL)

**Key Searches:**

```bash
# Search by service name
curl "http://localhost:3200/api/search?service=Medical%20Exam%20Platform%20API&limit=10"

# Search by trace ID
curl "http://localhost:3200/api/traces/<trace_id>"

# Search by span name
curl "http://localhost:3200/api/search?tags=span.name%3Dauth.login&limit=10"
```

**How to Use:**

```bash
# Access Tempo UI
open http://localhost:3200
# Or: curl http://localhost:3200

# Search for traces
# Use service name: "Medical Exam Platform API"
# Filter by span name: "auth.login", "session.start", "attempt.submit"
# View trace timeline and spans
```

### Logs

**Access**: Docker Compose logs or log aggregation system

**Key Commands:**

```bash
# Backend logs
docker compose logs -f backend_staging

# Frontend logs
docker compose logs -f frontend_staging

# All logs
docker compose logs -f
```

## Correlation Using request_id / trace_id

### Get request_id from Response

```bash
# Make request and capture request_id from header
curl -v https://<STAGING_DOMAIN>/api/v1/health 2>&1 | grep -i "x-request-id"
# Or from response body (if included)
curl -s https://<STAGING_DOMAIN>/api/v1/ready | jq -r '.request_id'
```

### Search Logs by request_id

```bash
# Search backend logs by request_id
docker compose logs backend_staging | grep '"request_id":"<request_id>"'

# Search with jq (if available)
docker compose logs backend_staging | jq 'select(.request_id == "<request_id>")'
```

### Search Logs by trace_id

```bash
# Search backend logs by trace_id
docker compose logs backend_staging | grep '"trace_id":"<trace_id>"'

# Search with jq
docker compose logs backend_staging | jq 'select(.trace_id == "<trace_id>")'
```

### Get trace_id from Logs

```bash
# Extract trace_id from logs for a specific request_id
docker compose logs backend_staging | grep '"request_id":"<request_id>"' | jq -r '.trace_id' | head -1
```

### View Trace in Tempo

```bash
# Get trace_id from logs
TRACE_ID=$(docker compose logs backend_staging | grep '"request_id":"<request_id>"' | jq -r '.trace_id' | head -1)

# View trace in Tempo
open "http://localhost:3200/trace/${TRACE_ID}"
# Or query via API
curl "http://localhost:3200/api/traces/${TRACE_ID}"
```

## Common Investigation Workflows

### Workflow 1: High Error Rate

1. **Check Grafana Dashboard**:
   - Open "FastAPI API Overview"
   - Check "4xx/5xx error rate by route"
   - Identify routes with high error rate

2. **Check Prometheus**:
   ```promql
   rate(http_requests_total{status=~"5.."}[5m]) by (route)
   ```

3. **Check Logs**:
   ```bash
   docker compose logs --since=10m backend_staging | grep -i error | tail -50
   ```

4. **Correlate with Traces**:
   - Get request_id from error logs
   - Get trace_id from logs
   - View trace in Tempo to see full request flow

### Workflow 2: Slow Response Times

1. **Check Grafana Dashboard**:
   - Open "FastAPI API Overview"
   - Check "Top 10 slowest routes (p95 latency)"
   - Identify slow routes

2. **Check Prometheus**:
   ```promql
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) by (route)
   ```

3. **Check Database Query Time**:
   ```promql
   rate(db_query_duration_seconds_sum[5m]) / rate(db_query_duration_seconds_count[5m])
   ```

4. **View Traces**:
   - Search Tempo for slow routes
   - Check span durations
   - Identify bottlenecks (DB queries, external API calls, etc.)

### Workflow 3: Authentication Issues

1. **Check Logs**:
   ```bash
   docker compose logs --since=10m backend_staging | grep -i "auth\|login" | tail -50
   ```

2. **Check Audit Logs**:
   ```bash
   docker compose logs --since=10m backend_staging | jq 'select(.audit == true and (.event | contains("auth")))'
   ```

3. **View Traces**:
   - Search Tempo for "auth.login" spans
   - Check span attributes for error details
   - Correlate with request_id

### Workflow 4: Database Connection Issues

1. **Check Prometheus**:
   ```promql
   up{job="postgres-exporter"}
   ```

2. **Check Logs**:
   ```bash
   docker compose logs --since=10m backend_staging | grep -i "database\|connection\|pool" | tail -50
   ```

3. **Check Database Metrics**:
   ```promql
   pg_stat_database_numbackends{datname="exam_platform_staging"}
   ```

4. **Check Readiness Endpoint**:
   ```bash
   curl -s https://<STAGING_DOMAIN>/api/v1/ready | jq '.checks.db'
   ```

## Log Query Examples

### By Event Type

```bash
# Request start events
docker compose logs backend_staging | jq 'select(.event == "request.start")'

# Request end events
docker compose logs backend_staging | jq 'select(.event == "request.end")'

# Audit events
docker compose logs backend_staging | jq 'select(.audit == true)'
```

### By Level

```bash
# Error level logs
docker compose logs backend_staging | jq 'select(.level == "error")'

# Warning level logs
docker compose logs backend_staging | jq 'select(.level == "warning")'
```

### By Time Range

```bash
# Last 10 minutes
docker compose logs --since=10m backend_staging

# Last hour
docker compose logs --since=1h backend_staging

# Specific time range (requires log aggregation system)
```

### By Route

```bash
# Specific route
docker compose logs backend_staging | jq 'select(.route == "/v1/auth/login")'

# All auth routes
docker compose logs backend_staging | jq 'select(.route | startswith("/v1/auth"))'
```

## Verification Checklist

After investigating an issue:

1. **Identified root cause**:
   - [ ] Error message identified
   - [ ] Affected routes identified
   - [ ] Time range identified
   - [ ] User impact assessed

2. **Correlated data**:
   - [ ] Logs reviewed
   - [ ] Metrics checked
   - [ ] Traces viewed
   - [ ] request_id/trace_id used for correlation

3. **Documented findings**:
   - [ ] Root cause documented
   - [ ] Affected components identified
   - [ ] Timeline established
   - [ ] Next steps defined

## Related Runbooks

- [01-Incident-Checklist.md](./01-Incident-Checklist.md) - Incident triage
- [00-QuickStart.md](./00-QuickStart.md) - Quick health checks
- [03-Database.md](./03-Database.md) - Database troubleshooting
- [04-Redis.md](./04-Redis.md) - Redis troubleshooting
