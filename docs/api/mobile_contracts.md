# Mobile-Safe API Contracts

This document defines the API contract standards for mobile clients with flaky networks and offline sync requirements. All rules apply to ensure safe, reliable mobile client integration.

**Status**: Implemented (Task 172)  
**API Version**: `/api/v1/...` (path-based versioning)  
**Last Updated**: 2026-01-28

---

## Table of Contents

1. [API Versioning](#api-versioning)
2. [Error Envelope Standardization](#error-envelope-standardization)
3. [Idempotency Support](#idempotency-support)
4. [Pagination & List Responses](#pagination--list-responses)
5. [Time & Formatting Rules](#time--formatting-rules)
6. [ETag / Caching Readiness](#etag--caching-readiness)
7. [Mobile-Critical Endpoints](#mobile-critical-endpoints)
8. [Error Code Reference](#error-code-reference)

---

## API Versioning

### Strategy: Path-Based Versioning

**Format**: `/api/v1/...`

- All endpoints are prefixed with `/api/v1/`
- Default version is `v1` if not specified
- Future versions will use `/api/v2/`, `/api/v3/`, etc.

### Deprecation Policy

- **No breaking changes** within `v1`
- Breaking changes require a new version (e.g., `v2`)
- Deprecated endpoints will be announced with 6-month notice
- Deprecated endpoints will return `X-API-Deprecated: true` header

### Example

```http
GET /api/v1/sessions
Authorization: Bearer <token>
```

---

## Error Envelope Standardization

### Standard Error Format

All error responses follow this schema:

```json
{
  "error_code": "STRING_STABLE_CODE",
  "message": "Human readable message",
  "details": { ... } | null,
  "request_id": "uuid-string" | null
}
```

### Error Response Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error_code` | string | Yes | Stable error code (see [Error Code Reference](#error-code-reference)) |
| `message` | string | Yes | Human-readable error message |
| `details` | object\|array\|null | No | Additional error context |
| `request_id` | string\|null | No | Request ID for tracing (UUID format) |

### Example Error Response

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid request data",
  "details": [
    {
      "field": "session_id",
      "issue": "Invalid UUID format",
      "type": "value_error"
    }
  ],
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Exception Handling

The API uses global exception handlers for:

- **HTTPException**: Standard HTTP errors (400, 401, 403, 404, etc.)
- **RequestValidationError**: Pydantic validation errors (422)
- **AppError**: Application-specific errors with structured codes
- **General Exceptions**: Unhandled exceptions (500)

All are normalized to the standard error envelope format.

---

## Idempotency Support

### Overview

Idempotency ensures safe retries for mobile clients with flaky networks. Critical for POST/PUT/PATCH operations.

### Implementation

**Header**: `Idempotency-Key: <unique-key>`

- Client generates a unique key per request (e.g., UUID)
- Server stores response in Redis with 24-hour TTL
- Same key + same payload → returns cached response (200/201)
- Same key + different payload → returns 409 Conflict

### Supported Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sessions/{session_id}/submit` | POST | Submit test session |

### Behavior

1. **First Request** (new key):
   - Process request normally
   - Store response in Redis with key + payload hash
   - Return response

2. **Retry** (same key + same payload):
   - Return cached response (200/201)
   - No duplicate processing

3. **Conflict** (same key + different payload):
   - Return 409 with `error_code: "IDEMPOTENCY_KEY_CONFLICT"`
   - Request is rejected

### Example Request

```http
POST /api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/submit
Authorization: Bearer <token>
Idempotency-Key: 123e4567-e89b-12d3-a456-426614174000
Content-Type: application/json
```

### Example Conflict Response

```json
{
  "error_code": "IDEMPOTENCY_KEY_CONFLICT",
  "message": "Idempotency-Key was used with a different request payload",
  "details": {
    "idempotency_key": "123e4567..."
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Redis Storage

- **Key Format**: `idempotency:{idempotency_key}`
- **TTL**: 24 hours
- **Storage**: Response body, status code, headers, payload hash

---

## Pagination & List Responses

### Cursor-Based Pagination (Mobile-Safe)

**Preferred for mobile clients** - efficient and consistent.

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cursor` | string\|null | No | Cursor token from previous response |
| `limit` | integer | No | Items per page (default: 50, max: 100) |

### Response Format

```json
{
  "items": [...],
  "next_cursor": "string|null",
  "has_more": true|false
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `items` | array | List of items for current page |
| `next_cursor` | string\|null | Cursor for next page (null if no more) |
| `has_more` | boolean | True if more items available |

### Example Request

```http
GET /api/v1/sessions?cursor=eyJpZCI6IjU1MGU4NDAwIn0&limit=20
Authorization: Bearer <token>
```

### Example Response

```json
{
  "items": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "started_at": "2026-01-28T10:00:00Z"
    }
  ],
  "next_cursor": "eyJpZCI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCJ9",
  "has_more": true
}
```

### Page-Based Pagination (Legacy)

**Still supported for web/admin clients** but not recommended for mobile.

- Uses `page` and `page_size` parameters
- Returns `{items, page, page_size, total}` format
- Less efficient for large datasets

---

## Time & Formatting Rules

### Timestamps

- **Format**: ISO-8601 UTC (e.g., `2026-01-28T10:00:00Z`)
- **Timezone**: Always UTC (Z suffix)
- **Precision**: Milliseconds optional (e.g., `2026-01-28T10:00:00.123Z`)

### Numeric Fields

- **Never return**: `NaN`, `Infinity`, `-Infinity`
- **Null handling**: Use `null` for missing values
- **Decimal precision**: Use appropriate precision (e.g., `score_pct: 85.50`)

### Example

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "started_at": "2026-01-28T10:00:00Z",
  "submitted_at": "2026-01-28T11:30:00Z",
  "score_pct": 85.50
}
```

---

## ETag / Caching Readiness

### Overview

ETag support enables efficient caching for content/test download endpoints.

### Implementation

**Headers**:
- `ETag: W/"<hash>"` (weak ETag)
- `If-None-Match: W/"<hash>"` (client request)

### Behavior

1. **First Request**:
   - Server computes ETag from content
   - Returns 200 with `ETag` header

2. **Subsequent Request** (with `If-None-Match`):
   - If ETag matches → return 304 Not Modified
   - If ETag differs → return 200 with new content + ETag

### Supported Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/import/schemas/{schema_id}/template` | GET | Download CSV template |
| `/api/v1/admin/import/jobs/{job_id}/rejected.csv` | GET | Download rejected rows CSV |

### Example Request

```http
GET /api/v1/admin/import/schemas/550e8400-e29b-41d4-a716-446655440000/template
Authorization: Bearer <token>
If-None-Match: W/"abc123def456"
```

### Example Response (304 Not Modified)

```http
HTTP/1.1 304 Not Modified
ETag: W/"abc123def456"
```

### Example Response (200 OK)

```http
HTTP/1.1 200 OK
Content-Type: text/csv
Content-Disposition: attachment; filename="template.csv"
ETag: W/"abc123def456"
```

---

## Mobile-Critical Endpoints

### Session Management

| Endpoint | Method | Idempotency | Cursor Pagination | Description |
|----------|--------|-------------|-------------------|-------------|
| `/api/v1/sessions` | POST | No | N/A | Create test session |
| `/api/v1/sessions/{session_id}` | GET | N/A | N/A | Get session state |
| `/api/v1/sessions/{session_id}/submit` | POST | **Yes** | N/A | Submit session (critical) |
| `/api/v1/sessions` | GET | N/A | **Yes** | List sessions |

### Analytics

| Endpoint | Method | Idempotency | Cursor Pagination | Description |
|----------|--------|-------------|-------------------|-------------|
| `/api/v1/analytics/overview` | GET | N/A | N/A | Analytics overview |
| `/api/v1/analytics/recent-sessions` | GET | N/A | **Yes** | Recent sessions |

### Content Lists

| Endpoint | Method | Idempotency | Cursor Pagination | Description |
|----------|--------|-------------|-------------------|-------------|
| `/api/v1/mistakes/list` | GET | N/A | **Yes** (planned) | List mistakes |
| `/api/v1/bookmarks` | GET | N/A | **Yes** (planned) | List bookmarks |

---

## Error Code Reference

### Standard Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `VALIDATION_LIMIT_EXCEEDED` | 422 | Validation limit exceeded (length, range, etc.) |
| `HTTP_ERROR` | 400-499 | Generic HTTP error |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `IDEMPOTENCY_KEY_CONFLICT` | 409 | Idempotency key reused with different payload |

### Authentication & Authorization

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_REQUIRED` | 401 | Authentication required |
| `AUTHENTICATION_FAILED` | 401 | Invalid credentials |
| `TOKEN_EXPIRED` | 401 | Access token expired |
| `TOKEN_INVALID` | 401 | Invalid token format |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `ROLE_REQUIRED` | 403 | Specific role required |

### Resource Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `RESOURCE_NOT_FOUND` | 404 | Resource not found |
| `RESOURCE_CONFLICT` | 409 | Resource conflict |
| `RESOURCE_LOCKED` | 423 | Resource locked |

### Rate Limiting

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `RATE_LIMIT_IP_LOCKED` | 429 | IP address locked |
| `RATE_LIMIT_EMAIL_LOCKED` | 429 | Email address locked |

---

## Testing Idempotency

### Manual Testing with curl

#### 1. Submit Session (First Request)

```bash
curl -X POST "http://localhost:8000/api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/submit" \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: test-key-123" \
  -H "Content-Type: application/json"
```

**Expected**: 200 OK with session submission response

#### 2. Retry (Same Key + Same Payload)

```bash
curl -X POST "http://localhost:8000/api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/submit" \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: test-key-123" \
  -H "Content-Type: application/json"
```

**Expected**: 200 OK with **same** response (cached)

#### 3. Conflict (Same Key + Different Payload)

```bash
# Note: This would require a different endpoint or payload
# For demonstration, assume different session_id in body
curl -X POST "http://localhost:8000/api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/submit" \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{"different": "payload"}'
```

**Expected**: 409 Conflict with `IDEMPOTENCY_KEY_CONFLICT` error

---

## Implementation Checklist

### Completed (Task 172)

- [x] API versioning: `/api/v1/...` path-based
- [x] Error envelope: `{error_code, message, details}` format
- [x] Idempotency: Redis-based with `Idempotency-Key` header
- [x] Cursor pagination: `{items, next_cursor, has_more}` format
- [x] ETag support: Download endpoints with `If-None-Match` handling
- [x] Timestamp format: ISO-8601 UTC enforcement
- [x] Numeric validation: No NaN/Infinity in responses

### Future Tasks

- [ ] Task 173: Audit all mobile endpoints for cursor pagination
- [ ] Task 174: Add batch sync endpoint with idempotency
- [ ] Task 175: Implement offline sync queue for mobile clients

---

## Notes

- **Backward Compatibility**: All changes maintain backward compatibility with web clients
- **Redis Dependency**: Idempotency requires Redis (fails open if unavailable)
- **Performance**: ETag computation is lightweight (MD5 hash)
- **Security**: Idempotency keys are truncated in error messages

---

**Last Updated**: 2026-01-28  
**Maintained By**: Backend Team
