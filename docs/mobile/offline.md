# Mobile Offline Support

This document describes the offline caching and sync system for mobile clients.

**Status**: Implemented (Task 173)  
**Last Updated**: 2026-01-28

---

## Table of Contents

1. [Overview](#overview)
2. [Offline Data Model](#offline-data-model)
3. [Test Package System](#test-package-system)
4. [Sync Algorithm](#sync-algorithm)
5. [Failure Scenarios & Recovery](#failure-scenarios--recovery)
6. [API Reference](#api-reference)

---

## Overview

Mobile clients can:

1. **Download test content** for offline use via Test Packages
2. **Queue attempts locally** and sync them safely when online

### Key Features

- **Immutable Packages**: Test packages are versioned and immutable once published
- **Idempotent Sync**: Batch sync prevents duplicate scoring
- **Offline Session Mapping**: Client-generated sessions map to server sessions deterministically
- **ETag Caching**: Efficient package downloads with conditional requests

---

## Offline Data Model

### Test Package

A **Test Package** is an immutable, versioned collection of questions for offline use.

**Structure**:
```json
{
  "package_id": "uuid",
  "name": "Year 1 Block A Questions",
  "scope": "BLOCK",
  "scope_data": {
    "year_id": 1,
    "block_id": 2
  },
  "version": 1,
  "version_hash": "sha256-hash",
  "questions": [
    {
      "question_id": "uuid",
      "stem": "...",
      "option_a": "...",
      "option_b": "...",
      "option_c": "...",
      "option_d": "...",
      "option_e": "...",
      "correct_index": 2,
      "explanation_md": "...",
      "year_id": 1,
      "block_id": 2,
      "theme_id": 5
    }
  ]
}
```

**Properties**:
- **Immutable**: Once published, package content never changes
- **Versioned**: New version created on content change
- **Scoped**: Filtered by program/year/block/theme
- **Cacheable**: Safe for long-term client caching

### Offline Attempt

An **Offline Attempt** is a locally queued answer that will be synced when online.

**Structure**:
```json
{
  "client_attempt_id": "uuid",
  "idempotency_key": "uuid",
  "offline_session_id": "uuid",
  "question_id": "uuid",
  "selected_option_index": 2,
  "answered_at": "2026-01-28T10:00:00Z",
  "payload_hash": "sha256-hash"
}
```

**Properties**:
- **Client-Generated IDs**: `client_attempt_id` and `offline_session_id` are client-generated
- **Idempotency**: `idempotency_key` ensures safe retries
- **Payload Hash**: Verifies attempt integrity

---

## Test Package System

### Package Scopes

| Scope | Description | Scope Data |
|-------|-------------|------------|
| `PROGRAM` | All questions for entire program | `{}` |
| `YEAR` | All questions for a year | `{year_id: 1}` |
| `BLOCK` | All questions for a block | `{year_id: 1, block_id: 2}` |
| `THEME` | All questions for a theme | `{year_id: 1, block_id: 2, theme_id: 5}` |

### Package Lifecycle

1. **Creation**: Admin creates package with questions
2. **Publishing**: Package marked as `is_published=true`
3. **Versioning**: New version created on content change
4. **Download**: Mobile clients download via API
5. **Caching**: Clients cache using ETag

### Package Download Flow

```
1. Client requests package list
   GET /api/v1/tests/packages?scope=BLOCK&block_id=2

2. Client checks local cache
   - If package_id exists and version_hash matches → use cached
   - Otherwise → download

3. Client downloads package
   GET /api/v1/tests/packages/{package_id}
   If-None-Match: W/"version_hash"

4. Server responds
   - If ETag matches → 304 Not Modified
   - Otherwise → 200 OK with package content
```

---

## Sync Algorithm

### Step-by-Step Sync Process

#### 1. Client Prepares Batch

Client collects queued attempts and prepares batch:

```json
{
  "attempts": [
    {
      "client_attempt_id": "uuid-1",
      "idempotency_key": "uuid-1-key",
      "offline_session_id": "uuid-session-1",
      "question_id": "uuid-q1",
      "selected_option_index": 2,
      "answered_at": "2026-01-28T10:00:00Z",
      "payload_hash": "sha256-hash-1"
    },
    {
      "client_attempt_id": "uuid-2",
      "idempotency_key": "uuid-2-key",
      "offline_session_id": "uuid-session-1",
      "question_id": "uuid-q2",
      "selected_option_index": 0,
      "answered_at": "2026-01-28T10:05:00Z",
      "payload_hash": "sha256-hash-2"
    }
  ]
}
```

#### 2. Client Sends Batch

```http
POST /api/v1/sync/attempts:batch
Authorization: Bearer <token>
Content-Type: application/json

{
  "attempts": [...]
}
```

#### 3. Server Processes Each Attempt

For each attempt, server:

1. **Validates payload hash**
   - Computes hash from attempt data
   - Compares with client-provided hash
   - If mismatch → `rejected` with `PAYLOAD_HASH_MISMATCH`

2. **Checks idempotency (Redis)**
   - Looks up `idempotency:{idempotency_key}` in Redis
   - If found → `duplicate` (already processed)
   - If not found → continue

3. **Maps offline session**
   - If `session_id` provided → use existing session
   - If `offline_session_id` provided → get/create server session
   - Stores mapping in Redis: `offline_session:{offline_session_id}` → `session_id`

4. **Checks database idempotency**
   - Queries `SessionAnswer` for `(session_id, question_id)`
   - If exists → `duplicate` (idempotent)
   - If not exists → create new answer

5. **Creates answer**
   - Creates `SessionAnswer` record
   - Computes correctness from question `correct_index`
   - Commits transaction

6. **Stores idempotency record**
   - Stores in Redis: `idempotency:{idempotency_key}` → response data
   - 24-hour TTL

#### 4. Server Returns Results

```json
{
  "results": [
    {
      "client_attempt_id": "uuid-1",
      "status": "acked",
      "error_code": null,
      "server_attempt_id": "uuid-server-1",
      "server_session_id": "uuid-server-session-1"
    },
    {
      "client_attempt_id": "uuid-2",
      "status": "duplicate",
      "error_code": null,
      "server_attempt_id": "uuid-server-2",
      "server_session_id": "uuid-server-session-1"
    }
  ]
}
```

### Status Values

| Status | Description | Action |
|--------|-------------|--------|
| `acked` | Successfully processed | Remove from local queue |
| `duplicate` | Already processed (idempotent) | Remove from local queue |
| `rejected` | Processing failed | Keep in queue, retry later |

---

## Failure Scenarios & Recovery

### Scenario 1: Network Failure During Sync

**Problem**: Client sends batch, network fails before response.

**Recovery**:
1. Client retries with same `idempotency_key` values
2. Server detects duplicates via Redis/DB
3. Returns `duplicate` status for already-processed attempts
4. Client removes duplicates from queue

**Result**: No double-scoring, safe retry.

### Scenario 2: Partial Batch Success

**Problem**: Some attempts succeed, others fail.

**Recovery**:
1. Server processes each attempt independently
2. Returns status per attempt (`acked`, `duplicate`, `rejected`)
3. Client removes successful attempts from queue
4. Client retries failed attempts later

**Result**: Partial progress preserved, failed attempts retried.

### Scenario 3: Payload Hash Mismatch

**Problem**: Client hash doesn't match server-computed hash.

**Recovery**:
1. Server returns `rejected` with `PAYLOAD_HASH_MISMATCH`
2. Client logs error, keeps attempt in queue
3. Client may re-validate attempt data
4. Client retries with corrected hash

**Result**: Data integrity maintained, client can fix and retry.

### Scenario 4: Redis Unavailable

**Problem**: Redis down, idempotency checks fail.

**Recovery**:
1. Server falls back to database-only idempotency
2. Uses `(session_id, question_id)` unique constraint
3. Processes attempts normally
4. May allow some duplicate processing (acceptable risk)

**Result**: Degraded but functional, no data loss.

### Scenario 5: Offline Session Mapping Lost

**Problem**: Redis mapping expired, offline_session_id not found.

**Recovery**:
1. Server creates new session for offline_session_id
2. Stores new mapping in Redis
3. Processes attempts normally
4. Client may see new `server_session_id` (acceptable)

**Result**: New session created, attempts processed successfully.

---

## API Reference

### GET /api/v1/tests/packages

List available test packages.

**Query Parameters**:
- `scope` (optional): Filter by scope (PROGRAM, YEAR, BLOCK, THEME)
- `year_id` (optional): Filter by year_id
- `block_id` (optional): Filter by block_id
- `theme_id` (optional): Filter by theme_id

**Response**:
```json
{
  "items": [
    {
      "package_id": "uuid",
      "name": "Year 1 Block A",
      "scope": "BLOCK",
      "scope_data": {"year_id": 1, "block_id": 2},
      "version": 1,
      "version_hash": "abc123...",
      "updated_at": "2026-01-28T10:00:00Z"
    }
  ]
}
```

### GET /api/v1/tests/packages/{package_id}

Download full test package.

**Headers**:
- `If-None-Match` (optional): ETag from previous request

**Response**:
- `200 OK`: Package content with `ETag` header
- `304 Not Modified`: Package unchanged (ETag matches)

**Example**:
```http
GET /api/v1/tests/packages/550e8400-e29b-41d4-a716-446655440000
If-None-Match: W/"abc123def456"
```

### HEAD /api/v1/tests/packages/{package_id}

Check package ETag without downloading content.

**Response**:
- `200 OK`: Package exists, `ETag` header included
- `304 Not Modified`: Package unchanged
- `404 Not Found`: Package not found

### POST /api/v1/sync/attempts:batch

Batch sync offline attempts.

**Request**:
```json
{
  "attempts": [
    {
      "client_attempt_id": "uuid",
      "idempotency_key": "uuid",
      "offline_session_id": "uuid",
      "question_id": "uuid",
      "selected_option_index": 2,
      "answered_at": "2026-01-28T10:00:00Z",
      "payload_hash": "sha256-hash"
    }
  ]
}
```

**Response**:
```json
{
  "results": [
    {
      "client_attempt_id": "uuid",
      "status": "acked",
      "error_code": null,
      "server_attempt_id": "uuid",
      "server_session_id": "uuid"
    }
  ]
}
```

**Status Codes**:
- `200 OK`: Batch processed (check individual results)
- `400 Bad Request`: Invalid request (empty batch, too many attempts)

---

## Testing Examples

### Download Package

```bash
# List packages
curl -X GET "http://localhost:8000/api/v1/tests/packages?scope=BLOCK&block_id=2" \
  -H "Authorization: Bearer <token>"

# Download package (first time)
curl -X GET "http://localhost:8000/api/v1/tests/packages/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <token>"

# Download package (with ETag - should return 304)
curl -X GET "http://localhost:8000/api/v1/tests/packages/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <token>" \
  -H "If-None-Match: W/\"abc123def456\""
```

### Batch Sync

```bash
# Sync batch of attempts
curl -X POST "http://localhost:8000/api/v1/sync/attempts:batch" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "attempts": [
      {
        "client_attempt_id": "123e4567-e89b-12d3-a456-426614174000",
        "idempotency_key": "223e4567-e89b-12d3-a456-426614174000",
        "offline_session_id": "323e4567-e89b-12d3-a456-426614174000",
        "question_id": "550e8400-e29b-41d4-a716-446655440000",
        "selected_option_index": 2,
        "answered_at": "2026-01-28T10:00:00Z",
        "payload_hash": "abc123def456..."
      }
    ]
  }'

# Retry same batch (should return duplicates)
curl -X POST "http://localhost:8000/api/v1/sync/attempts:batch" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "attempts": [
      {
        "client_attempt_id": "123e4567-e89b-12d3-a456-426614174000",
        "idempotency_key": "223e4567-e89b-12d3-a456-426614174000",
        "offline_session_id": "323e4567-e89b-12d3-a456-426614174000",
        "question_id": "550e8400-e29b-41d4-a716-446655440000",
        "selected_option_index": 2,
        "answered_at": "2026-01-28T10:00:00Z",
        "payload_hash": "abc123def456..."
      }
    ]
  }'
```

---

## Implementation Notes

### Idempotency Strategy

- **Redis**: Primary idempotency check (fast, 24h TTL)
- **Database**: Secondary idempotency check (unique constraint on `(session_id, question_id)`)
- **Fail-Open**: If Redis unavailable, falls back to DB-only

### Offline Session Mapping

- **Redis Storage**: `offline_session:{offline_session_id}` → `session_id`
- **TTL**: 7 days (configurable)
- **Deterministic**: Same `offline_session_id` always maps to same server session

### Atomicity

- **Per-Attempt**: Each attempt processed independently
- **Not Per-Batch**: Batch failures don't rollback successful attempts
- **Commit Per-Item**: Each `acked` attempt committed immediately

### Safety Guarantees

- **No Double-Scoring**: Idempotency prevents duplicate scoring
- **Data Integrity**: Payload hash verification
- **Consistent Mapping**: Offline sessions map deterministically

---

## Next Steps (Task 174)

- [ ] Add package generation/admin endpoints
- [ ] Implement package versioning automation
- [ ] Add sync status tracking
- [ ] Implement sync retry backoff
- [ ] Add sync metrics/observability

---

**Last Updated**: 2026-01-28  
**Maintained By**: Backend Team
