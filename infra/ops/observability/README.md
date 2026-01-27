# OpenTelemetry Observability

This directory contains configuration and documentation for OpenTelemetry tracing infrastructure.

## Overview

The platform uses OpenTelemetry (OTel) for distributed tracing:
- **FastAPI backend** instruments requests and exports traces via OTLP
- **OpenTelemetry Collector** receives traces and forwards them to Tempo
- **Grafana Tempo** stores and serves trace data

## Architecture

```
FastAPI App → OTLP (HTTP) → OpenTelemetry Collector → OTLP (gRPC) → Grafana Tempo
```

## Services

### OpenTelemetry Collector

- **Service name**: `otel-collector`
- **Ports**:
  - `4317` (gRPC) - OTLP receiver
  - `4318` (HTTP) - OTLP receiver
- **Config**: `infra/ops/otel/otel-collector.yaml`

The collector receives traces from the FastAPI app and batches them before forwarding to Tempo.

### Grafana Tempo

- **Service name**: `tempo`
- **Ports**:
  - `3200` (HTTP) - Query API and UI
  - `4317` (gRPC) - OTLP receiver
  - `4318` (HTTP) - OTLP receiver
- **Config**: `infra/ops/tempo/tempo.yaml`

Tempo stores traces and provides a query API. In production, you'll typically connect Grafana to Tempo for visualization.

## Starting Services

To start the observability stack with docker-compose:

```bash
cd infra/docker/compose
docker compose -f docker-compose.dev.yml up -d otel-collector tempo
```

Or start all services:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

## Verification

### 1. Check Services Are Running

```bash
docker compose -f docker-compose.dev.yml ps
```

You should see `exam_platform_otel_collector` and `exam_platform_tempo` in the list.

### 2. Verify Traces Are Being Generated

Make a request to the health endpoint:

```bash
curl http://localhost:8000/health
```

### 3. Check Tempo UI

Tempo provides a simple UI at:
- http://localhost:3200

You can search for traces by:
- Service name: `Medical Exam Platform API`
- Trace ID (from `X-Request-ID` header in responses)

### 4. Query Tempo API

Query traces via the Tempo API:

```bash
# Search for traces
curl "http://localhost:3200/api/search?limit=10"

# Get specific trace by ID
curl "http://localhost:3200/api/traces/{trace_id}"
```

## Configuration

### Backend Environment Variables

The FastAPI backend uses these environment variables (set in docker-compose):

- `OTEL_SERVICE_NAME` - Service name in traces (default: "Medical Exam Platform API")
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OTLP collector endpoint (default: "http://otel-collector:4318")
- `OTEL_TRACES_SAMPLER` - Sampling strategy (default: "parentbased_traceidratio")
- `OTEL_TRACES_SAMPLER_ARG` - Sampling ratio (default: "0.1" = 10% in production)
- `OTEL_RESOURCE_ATTRIBUTES` - Resource attributes like `deployment.environment=prod`
- `OTEL_SERVICE_VERSION` - Service version (default: "1.0.0")

### Sampling

In production, traces are sampled at 10% (`OTEL_TRACES_SAMPLER_ARG=0.1`) to reduce overhead. In development, you may want to set this to `1.0` (100%) for debugging.

The `parentbased_traceidratio` sampler:
- If a request has a parent trace (from upstream service), it follows the parent's sampling decision
- If no parent exists, it samples based on the ratio (10% by default)

### PII Safety

The instrumentation is configured to avoid PII (Personally Identifiable Information) in span attributes:
- Only includes `user.id` if it's a UUID or numeric ID (not email/name)
- Request IDs are included (safe, generated UUIDs)
- No request/response bodies are captured
- No authentication tokens are captured

## Connecting Grafana

To visualize traces in Grafana:

1. **Add Tempo Data Source**:
   - URL: `http://tempo:3200` (from within docker network)
   - Or `http://localhost:3200` (if Grafana runs on host)

2. **Configure Trace Query**:
   - Use service name: `Medical Exam Platform API`
   - Search by trace ID or time range

3. **Explore Traces**:
   - Use Grafana's Explore view with Tempo data source
   - Query by service name, tags, or trace ID

## Troubleshooting

### No Traces Appearing

1. **Check collector logs**:
   ```bash
   docker logs exam_platform_otel_collector
   ```

2. **Check backend logs** for OTel errors:
   ```bash
   docker logs exam_platform_backend
   ```

3. **Verify environment variables** are set correctly in docker-compose

4. **Check network connectivity**:
   ```bash
   docker exec exam_platform_backend ping otel-collector
   ```

### High Memory Usage

If Tempo uses too much memory:
- Reduce `block_retention` in `tempo.yaml`
- Increase sampling ratio (sample fewer traces)
- Adjust `ingestion_rate_limit_bytes` in Tempo config

## Production Considerations

1. **Sampling**: Keep sampling at 10% or lower in production
2. **Retention**: Configure appropriate retention in Tempo based on storage
3. **Security**: In production, use TLS for OTLP connections
4. **Scaling**: Consider running Tempo and Collector as separate services with proper resource limits
5. **Monitoring**: Monitor the collector and Tempo services themselves

## Grafana Dashboards

Grafana provides visualization for both metrics (Prometheus) and traces (Tempo).

### Access

- **URL**: http://localhost:3001 (when port is exposed)
- **Default credentials**:
  - Username: `admin`
  - Password: Set via `GRAFANA_ADMIN_PASSWORD` environment variable (default: `admin`)
- **Internal access**: Grafana is accessible from within the Docker network at `http://grafana:3000`

### Changing Admin Password

Set the `GRAFANA_ADMIN_PASSWORD` environment variable in your `.env` file or docker-compose:

```bash
# In .env file
GRAFANA_ADMIN_PASSWORD=your_secure_password_here
```

**Important**: Change the default password in production!

### Provisioned Dashboards

Three starter dashboards are automatically provisioned:

1. **Traefik Edge Overview** (`traefik-edge-overview`)
   - RPS by entrypoint
   - Total RPS gauge
   - Latency p95 by entrypoint
   - 4xx/5xx error rate
   - Top 10 routers by RPS

2. **FastAPI API Overview** (`fastapi-api-overview`)
   - RPS by HTTP method
   - Total RPS gauge
   - Latency p95 by route
   - 4xx/5xx error rate by route
   - Top 10 slowest routes (p95 latency)
   - Top 10 routes by RPS

3. **Data Layer Basics** (`data-layer-basics`)
   - Container status (Backend, Prometheus, Traefik)
   - All scrape targets status
   - Notes on PostgreSQL/Redis exporters (not yet configured)

### Dashboard Location

Dashboards are stored in:
- **Config**: `infra/ops/grafana/dashboards/*.json`
- **Provisioning**: `infra/ops/grafana/provisioning/dashboards/dashboards.yml`

Dashboards are automatically loaded on Grafana startup. To add new dashboards:
1. Create a JSON file in `infra/ops/grafana/dashboards/`
2. Restart Grafana or wait for auto-reload (10s interval)

### Data Sources

Prometheus datasource is automatically provisioned:
- **Config**: `infra/ops/grafana/provisioning/datasources/datasource.yml`
- **URL**: `http://prometheus:9090` (internal network)

To add Tempo as a datasource for trace visualization:
1. Go to Configuration → Data Sources in Grafana UI
2. Add Tempo datasource with URL: `http://tempo:3200`

## Manual Tracing for Key Flows

Manual OpenTelemetry spans have been added to key business flows:

### Instrumented Flows

1. **auth.login** - Login authentication flow
   - Location: `backend/app/api/v1/endpoints/auth.py` (login function)
   - Attributes:
     - `auth.email_normalized` (normalized email, no PII)
     - `auth.ip_address`
     - `user.id` (UUID only, safe)
     - `user.role`
     - `auth.session_id` (on success)
     - `auth.mfa_required` (if MFA is enabled)
     - `http.request_id` (correlated from middleware)

2. **session.start** - Session creation flow
   - Location: `backend/app/services/session_engine.py` (create_session function)
   - Attributes:
     - `session.id`
     - `user.id`
     - `session.mode`
     - `session.year`
     - `session.blocks_count`
     - `session.themes_count`
     - `session.question_count`
     - `session.duration_seconds`
     - `session.exam_mode`
     - `session.algo_profile`
     - `session.algo_policy_version`
     - `session.total_questions`

3. **attempt.submit** - Session submission flow
   - Location: `backend/app/services/session_engine.py` (submit_session function)
   - Attributes:
     - `session.id`
     - `user.id`
     - `attempt.auto_expired`
     - `attempt.exam_mode`
     - `attempt.algo_profile`
     - `attempt.algo_policy_version`
     - `attempt.score_correct`
     - `attempt.score_total`
     - `attempt.score_pct`
     - `attempt.answers_count`
     - `attempt.already_submitted` (if idempotent call)

### Error Handling

All spans include error handling:
- Exceptions are recorded using `span.record_exception()`
- Spans are marked as ERROR status
- Error codes are captured (if available from exception)
- Error messages are sanitized (truncated to 200 chars, no PII)

### Request ID Correlation

Request IDs are automatically correlated:
- Middleware (`app/observability/otel.py`) sets `http.request_id` on the root span
- All child spans (auth.login, session.start, attempt.submit) are part of the same trace
- Request ID is accessible via `request.state.request_id` in endpoints

### Verification

To verify traces are being generated:

1. **Make requests to instrumented endpoints:**
   ```bash
   # Login
   curl -X POST http://localhost:8000/v1/auth/login \
     -H "Content-Type: application/json" \
     -H "X-Request-ID: test-request-123" \
     -d '{"email":"test@example.com","password":"password"}'

   # Create session (requires auth token)
   curl -X POST http://localhost:8000/v1/sessions \
     -H "Authorization: Bearer <token>" \
     -H "X-Request-ID: test-request-456" \
     -d '{"year":1,"blocks":["block1"],"mode":"practice","count":10}'

   # Submit session (requires auth token)
   curl -X POST http://localhost:8000/v1/sessions/<session_id>/submit \
     -H "Authorization: Bearer <token>" \
     -H "X-Request-ID: test-request-789"
   ```

2. **Check Tempo for traces:**
   ```bash
   # Search for traces by service name
   curl "http://localhost:3200/api/search?service=Medical%20Exam%20Platform%20API&limit=10"

   # Search by span name
   curl "http://localhost:3200/api/search?tags=span.name%3Dauth.login&limit=10"
   ```

3. **View traces in Tempo UI:**
   - Open http://localhost:3200
   - Search for service: "Medical Exam Platform API"
   - Filter by span name: "auth.login", "session.start", or "attempt.submit"
   - Verify span attributes are present and contain expected values

4. **Verify request_id correlation:**
   - Find a trace with span name "auth.login"
   - Check that the root span has `http.request_id` attribute
   - Verify child spans are part of the same trace

## Structured Logging

The application uses structured JSON logging with OpenTelemetry trace correlation.

### Log Format

All logs are output as JSON (one line per event) to stdout/stderr (container-friendly).

**Standard Log Format:**
```json
{
  "event": "request.start",
  "timestamp": "2026-01-27T10:30:45.123456Z",
  "level": "info",
  "logger": "app.middleware.request_timing",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "service_name": "Medical Exam Platform API",
  "environment": "dev",
  "method": "GET",
  "path": "/v1/health",
  "route": "/v1/health"
}
```

**Request Lifecycle Logs:**
- `request.start` - Logged at request start with method, path, route
- `request.end` - Logged at request end with duration_ms, status_code, db_query_count, db_total_ms

**Audit Logs:**
- Separate audit logger channel for sensitive actions
- Includes: actor_id, actor_role, action, target_id
- All fields are redacted for sensitive keys

### Correlation Fields

All logs include correlation fields:
- `request_id` - Request ID from X-Request-ID header or generated UUID
- `trace_id` - OpenTelemetry trace ID (if trace is active)
- `span_id` - OpenTelemetry span ID (if trace is active)
- `service_name` - Service name from SERVICE_NAME env var
- `environment` - Environment from ENV env var

### Request ID Binding

Request ID is automatically bound to structlog context for all logs within a request:
- Set by `RequestTimingMiddleware` at request start
- Available in all log statements within the request
- Cleared at request end

### Audit Logging

Sensitive actions are logged via the audit logger:

```python
from app.observability.logging import audit_log

# Log admin action
audit_log(
    event="admin.user_deleted",
    actor_id=str(user.id),
    actor_role="ADMIN",
    action="delete_user",
    target_id=str(target_user.id),
    reason="policy_violation",
)
```

Audit logs automatically:
- Include correlation fields (request_id, trace_id, span_id)
- Redact sensitive keys (password, token, secret, etc.)
- Use WARNING level for visibility

### Redaction

Sensitive data is automatically redacted from log fields:
- Keys containing: password, token, authorization, cookie, secret, api_key, etc.
- Values are replaced with `[REDACTED]`
- Applied recursively to nested dictionaries and lists

### Querying Logs

**By Request ID:**
```bash
docker compose logs backend | grep '"request_id":"550e8400-e29b-41d4-a716-446655440000"'
```

**By Trace ID:**
```bash
docker compose logs backend | grep '"trace_id":"4bf92f3577b34da6a3ce929d0e0e4736"'
```

**By Event Type:**
```bash
docker compose logs backend | grep '"event":"request.start"'
docker compose logs backend | grep '"event":"request.end"'
```

**Audit Logs Only:**
```bash
docker compose logs backend | grep '"audit":true'
```

**Using jq (if available):**
```bash
# Filter by request_id
docker compose logs backend | jq 'select(.request_id == "550e8400-e29b-41d4-a716-446655440000")'

# Filter by trace_id
docker compose logs backend | jq 'select(.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736")'

# Filter audit logs
docker compose logs backend | jq 'select(.audit == true)'

# Filter by level
docker compose logs backend | jq 'select(.level == "error")'
```

### Sample Log Lines

**Request Start:**
```json
{"event": "request.start", "timestamp": "2026-01-27T10:30:45.123456Z", "level": "info", "logger": "app.middleware.request_timing", "request_id": "550e8400-e29b-41d4-a716-446655440000", "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "span_id": "00f067aa0ba902b7", "service_name": "Medical Exam Platform API", "environment": "dev", "method": "GET", "path": "/v1/health", "route": "/v1/health"}
```

**Request End:**
```json
{"event": "request.end", "timestamp": "2026-01-27T10:30:45.234567Z", "level": "info", "logger": "app.middleware.request_timing", "request_id": "550e8400-e29b-41d4-a716-446655440000", "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "span_id": "00f067aa0ba902b7", "service_name": "Medical Exam Platform API", "environment": "dev", "method": "GET", "path": "/v1/health", "route": "/v1/health", "status_code": 200, "duration_ms": 12, "db_query_count": 0, "db_total_ms": 0}
```

**Audit Log (Login Failure):**
```json
{"event": "auth_login_failed", "timestamp": "2026-01-27T10:30:50.123456Z", "level": "warning", "logger": "audit", "request_id": "660e8400-e29b-41d4-a716-446655440001", "trace_id": "5cf92f3577b34da6a3ce929d0e0e4737", "span_id": "11f067aa0ba902b8", "service_name": "Medical Exam Platform API", "environment": "dev", "audit": true, "action": "auth_login_failed", "outcome": "deny", "reason_code": "UNAUTHORIZED", "ip_address": "192.168.1.100", "user_agent": "Mozilla/5.0..."}
```

**Audit Log (Admin Action):**
```json
{"event": "admin.user_deleted", "timestamp": "2026-01-27T10:31:00.123456Z", "level": "warning", "logger": "audit", "request_id": "770e8400-e29b-41d4-a716-446655440002", "trace_id": "6df92f3577b34da6a3ce929d0e0e4738", "span_id": "22f067aa0ba902b9", "service_name": "Medical Exam Platform API", "environment": "dev", "audit": true, "actor_id": "123e4567-e89b-12d3-a456-426614174000", "actor_role": "ADMIN", "action": "delete_user", "target_id": "223e4567-e89b-12d3-a456-426614174001", "reason": "policy_violation"}
```

### Configuration

**Environment Variables:**
- `LOG_LEVEL` - Log level (DEBUG, INFO, WARNING, ERROR) - default: INFO
- `SERVICE_NAME` - Service name in logs - default: "Medical Exam Platform API"
- `ENV` - Environment (dev, staging, prod, test) - default: dev

**Uvicorn Logs:**
- Uvicorn access logs are disabled (set to WARNING level)
- Request lifecycle is logged via `RequestTimingMiddleware` instead
- Uvicorn server logs remain at INFO level

### PII Safety

- No PII in logs: Only UUIDs/numeric IDs, no emails/names/phones
- Automatic redaction: Sensitive keys are redacted before logging
- Safe user ID extraction: Only UUID/numeric IDs are included
- Error messages: Truncated and sanitized

## Verification Script

A verification script is provided to test the entire observability stack:

**Linux/Mac:**
```bash
./infra/scripts/verify-observability.sh
```

**Windows (PowerShell):**
```powershell
.\infra\scripts\verify-observability.ps1
```

The script verifies:
- Services are running (otel-collector, tempo, prometheus, grafana)
- Traces are being generated and appear in Tempo
- Prometheus targets are UP (backend, postgres, redis, traefik)
- Backend metrics endpoint is accessible
- Grafana is accessible with dashboards loaded
- Structured logging with correlation fields (request_id, trace_id, span_id)

## Database Exporters

PostgreSQL and Redis exporters are configured to expose metrics to Prometheus:

**PostgreSQL Exporter:**
- Service: `postgres-exporter`
- Port: `9187` (default)
- Metrics: Connection count, query performance, database size, transaction rates
- Config: Uses `DATA_SOURCE_NAME` environment variable

**Redis Exporter:**
- Service: `redis-exporter`
- Port: `9121` (default)
- Metrics: Memory usage, connected clients, commands per second, hit/miss ratio
- Config: Connects to `redis:6379` via `REDIS_ADDR` environment variable

Both exporters are automatically scraped by Prometheus and metrics appear in the Data Layer dashboard.

## Files

- `infra/ops/otel/otel-collector.yaml` - OpenTelemetry Collector configuration
- `infra/ops/tempo/tempo.yaml` - Grafana Tempo configuration
- `infra/ops/prometheus/prometheus.yml` - Prometheus configuration
- `infra/ops/grafana/provisioning/datasources/datasource.yml` - Grafana datasources (Prometheus + Tempo)
- `infra/ops/grafana/provisioning/dashboards/dashboards.yml` - Dashboard provisioning config
- `infra/ops/grafana/dashboards/*.json` - Dashboard definitions
- `backend/app/observability/otel.py` - Python OTel instrumentation code
- `backend/app/observability/tracing.py` - Tracing utilities for manual spans
- `backend/app/observability/logging.py` - Structured JSON logging with trace correlation
- `infra/scripts/verify-observability.sh` - Verification script (Linux/Mac)
- `infra/scripts/verify-observability.ps1` - Verification script (Windows)

## Operational Runbooks

For operational procedures and incident response, see the [Runbooks](../runbooks/) directory:

- [00-QuickStart.md](../runbooks/00-QuickStart.md) - Quick status checks and restarts
- [01-Incident-Checklist.md](../runbooks/01-Incident-Checklist.md) - Incident triage and response
- [06-Observability.md](../runbooks/06-Observability.md) - How to use Grafana, Prometheus, Tempo, and logs for diagnosis
- [08-Cloudflare.md](../runbooks/08-Cloudflare.md) - Cloudflare analytics integration and log analysis
