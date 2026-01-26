# Performance Budgets & Anti‑Lag Guardrails

This doc defines **locked performance budgets** and the guardrails implemented in the backend to keep the **student UX fast** as traffic and data scale.

## Budgets (p95)

### Student hot paths
- **GET** `/v1/sessions/{id}` (player state): **< 400ms**
- **POST** `/v1/sessions/{id}/answer`: **< 250ms**
- **GET** `/v1/student/revision`: **< 300ms**
- **GET** `/v1/analytics/overview`: **< 500ms**

### Admin
- **GET** `/v1/admin/questions` (first page): **< 1000ms**

## Thresholds (logging severity)

### Slow request
- **warn**: > **500ms**
- **error**: > **1500ms**

### Slow SQL
- **warn**: > **100ms**
- **error**: > **300ms**

## What we enforce

### Response-time + DB headers (every request)
- `X-Request-ID`
- `X-Response-Time-ms`
- `X-DB-Queries`
- `X-DB-Time-ms`

### Slow request / slow SQL detection
- Slow requests and slow SQL are logged with the **same `request_id`** so you can correlate “slow endpoint” ↔ “slow query”.
- In production we avoid verbose DB logs; we **only log slow SQL**, while still tracking query counts/timing for response headers and sampling.

### Hot-path payload shaping
- Admin list endpoints are paginated by default and capped to protect performance.
- Admin questions list returns **snippets** only; full bodies/explanations are fetched via the detail endpoint.

### Minimal caching (fail-open)
- Syllabus reads (years/blocks/themes) cache for **6h** and are invalidated on admin syllabus mutations.
- Student revision dashboard aggregation caches for **60s** (keyed by user + date).

## Index audit (high ROI)

These indexes should exist to protect p95 latency for common access patterns:

### Attempts / events
- `attempts (user_id, attempted_at DESC)`
- `attempts (session_id)`
- `attempts (question_id)`
- `attempts (theme_id)` (if the column exists)

### Sessions
- `sessions (user_id, created_at DESC)`

### Revision queue
- `revision_queue (user_id, due_at)`
- `revision_queue (user_id, status)`

### Questions
- `questions (status)`
- `questions (theme_id, status)`

### Optional: text search
- Trigram index on stem (GIN) is only added if **`pg_trgm`** is enabled; otherwise defer.

## Safe migration notes

- Prefer `CREATE INDEX CONCURRENTLY` on large tables to avoid long exclusive locks.
- Alembic “concurrently” indexes must run outside a transaction (or via autocommit blocks).

