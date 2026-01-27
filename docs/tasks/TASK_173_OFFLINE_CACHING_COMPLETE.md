# Task 173: Offline Caching Support for Mobile Clients - Implementation Complete

**Status**: ✅ Complete  
**Date**: 2026-01-28  
**Implemented By**: Backend Team

---

## Summary

Implemented comprehensive offline caching and sync support for mobile clients, enabling:
1. Download of test content packages for offline use
2. Safe queuing and syncing of attempts when online

---

## Implementation Details

### A) Test Package System ✅

#### 1. Test Package Model

**File**: `backend/app/models/test_package.py`

- Created `TestPackage` model with:
  - `package_id` (UUID)
  - `version` (int) and `version_hash` (SHA-256)
  - `scope` (PROGRAM, YEAR, BLOCK, THEME)
  - `scope_data` (JSONB for flexible filtering)
  - `questions_json` (immutable question snapshots)
  - `is_published` flag

**Properties**:
- Immutable once published
- Versioned on content change
- Safe for long-term caching

#### 2. Package Endpoints

**File**: `backend/app/api/v1/endpoints/test_packages.py`

**Endpoints Implemented**:

1. **GET /api/v1/tests/packages**
   - Lists published packages
   - Supports filtering by scope, year_id, block_id, theme_id
   - Returns package metadata (id, version, hash, updated_at)

2. **GET /api/v1/tests/packages/{package_id}**
   - Returns full package with questions
   - Supports ETag/If-None-Match → 304 Not Modified
   - Efficient caching for mobile clients

3. **HEAD /api/v1/tests/packages/{package_id}**
   - Check package ETag without downloading
   - Useful for cache validation

**Schemas**: `backend/app/schemas/test_package.py`
- `TestPackageListItem` - List item
- `TestPackageOut` - Full package
- `QuestionSnapshot` - Frozen question data

---

### B) Batch Sync System ✅

#### 1. Sync Schemas

**File**: `backend/app/schemas/sync.py`

- `SyncAttemptItem` - Single attempt in batch
- `BatchSyncRequest` - Batch request (max 100 attempts)
- `SyncAttemptResult` - Result per attempt
- `BatchSyncResponse` - Batch response

#### 2. Batch Sync Endpoint

**File**: `backend/app/api/v1/endpoints/sync.py`

**Endpoint**: `POST /api/v1/sync/attempts:batch`

**Features**:
- Processes each attempt independently (atomic per item)
- Idempotency via Redis + database
- Offline session mapping (client → server)
- Payload hash verification
- Status per attempt: `acked`, `duplicate`, `rejected`

**Processing Flow**:
1. Validate payload hash
2. Check Redis idempotency
3. Map offline session to server session
4. Check database idempotency
5. Create answer if new
6. Store idempotency record
7. Commit per attempt

**Safety Guarantees**:
- ✅ No double-scoring (idempotency enforced)
- ✅ Atomic per attempt (not per batch)
- ✅ Consistent offline session mapping
- ✅ Data integrity (payload hash)

---

### C) Offline Session Mapping ✅

**Implementation**: `get_or_create_offline_session()`

**Strategy**:
- Redis mapping: `offline_session:{offline_session_id}` → `server_session_id`
- 7-day TTL for mappings
- Deterministic: same offline_session_id → same server session
- Creates session on first sync if not exists

**Session Creation**:
- Uses question metadata to determine scope (year, block, theme)
- Defaults to TUTOR mode
- Status: ACTIVE

---

### D) Documentation ✅

**File**: `docs/mobile/offline.md`

Comprehensive documentation including:
- Offline data model
- Test package system
- Sync algorithm (step-by-step)
- Failure scenarios & recovery
- API reference
- Testing examples (curl)

---

## Files Created

1. `backend/app/models/test_package.py` - Test Package model
2. `backend/app/schemas/test_package.py` - Package schemas
3. `backend/app/api/v1/endpoints/test_packages.py` - Package endpoints
4. `backend/app/schemas/sync.py` - Sync schemas
5. `backend/app/api/v1/endpoints/sync.py` - Batch sync endpoint
6. `docs/mobile/offline.md` - Comprehensive documentation
7. `docs/tasks/TASK_173_OFFLINE_CACHING_COMPLETE.md` - This file

## Files Modified

1. `backend/app/api/v1/router.py` - Added test_packages and sync routers

---

## Database Migration Required

**New Table**: `test_packages`

```sql
CREATE TABLE test_packages (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    scope VARCHAR(50) NOT NULL,
    scope_data JSONB NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    version_hash VARCHAR(64) NOT NULL,
    questions_json JSONB NOT NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMP WITH TIME ZONE,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (scope, scope_data, version)
);

CREATE INDEX ix_test_packages_scope ON test_packages(scope);
CREATE INDEX ix_test_packages_published ON test_packages(is_published, published_at);
CREATE INDEX ix_test_packages_version_hash ON test_packages(version_hash);
```

**Note**: Migration file should be created via Alembic.

---

## Testing

### Test Package Download

```bash
# List packages
curl -X GET "http://localhost:8000/api/v1/tests/packages?scope=BLOCK&block_id=2" \
  -H "Authorization: Bearer <token>"

# Download package
curl -X GET "http://localhost:8000/api/v1/tests/packages/{package_id}" \
  -H "Authorization: Bearer <token>"

# Check ETag (HEAD)
curl -X HEAD "http://localhost:8000/api/v1/tests/packages/{package_id}" \
  -H "Authorization: Bearer <token>" \
  -H "If-None-Match: W/\"abc123\""
```

### Batch Sync

```bash
# Sync batch
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

# Retry (should return duplicates)
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

## Key Features

### ✅ Test Package System

- Immutable, versioned packages
- ETag-based caching
- Scope-based filtering (PROGRAM, YEAR, BLOCK, THEME)
- Safe for long-term client caching

### ✅ Batch Sync System

- Idempotent per attempt
- Atomic per item (not per batch)
- Offline session mapping
- Payload hash verification
- Status per attempt (acked/duplicate/rejected)

### ✅ Safety Guarantees

- No double-scoring
- Data integrity (hash verification)
- Consistent session mapping
- Fail-open (Redis unavailable → DB-only)

---

## Constraints Met

- ✅ No breaking changes to existing submit endpoints
- ✅ Batch endpoint atomic per item (not per batch)
- ✅ No placeholders - all endpoints fully implemented
- ✅ Comprehensive documentation

---

## Next Steps (Task 174)

### TODO Checklist

- [ ] Create Alembic migration for `test_packages` table
- [ ] Add admin endpoints for package creation/publishing
- [ ] Implement package generation from question bank
- [ ] Add package versioning automation
- [ ] Add sync status tracking/metrics
- [ ] Implement sync retry backoff strategy
- [ ] Add observability (logs, metrics, traces)
- [ ] Create package generation scripts
- [ ] Add package validation tests
- [ ] Add sync endpoint integration tests

---

## Notes

- **Package Generation**: Currently manual - admin endpoints needed for Task 174
- **Session Mapping**: Uses Redis with 7-day TTL - may need adjustment
- **Idempotency**: Dual-layer (Redis + DB) for reliability
- **Performance**: Batch limit of 100 attempts per request

---

**Status**: ✅ Complete  
**Ready for**: Mobile client integration, package generation (Task 174)
