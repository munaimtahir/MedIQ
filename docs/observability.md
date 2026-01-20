# Observability & Telemetry

This document describes the telemetry and event logging system for the exam prep platform.

---

## Overview

The platform collects behavioral telemetry from test sessions to enable:
- Performance analytics
- User behavior insights
- Learning pattern analysis
- A/B testing support
- Data warehouse integration (Snowflake)

**IMPORTANT**: All telemetry is **best-effort**. Failures must NOT impact the user experience.

---

## Event Envelope (v1)

Every telemetry event follows a canonical envelope structure:

### Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique event ID |
| `event_version` | Integer | Yes | Schema version (default: 1) |
| `event_type` | String | Yes | Event type (see allowed types below) |
| `event_ts` | Timestamp | Yes | Server timestamp (UTC) |
| `client_ts` | Timestamp | No | Client-reported timestamp |
| `seq` | Integer | No | Client sequence number |
| `session_id` | UUID | Yes | Test session ID |
| `user_id` | UUID | Yes | User ID |
| `question_id` | UUID | No | Question ID (if applicable) |
| `source` | String | No | Event source: "web", "mobile", "api" |
| `payload_json` | JSONB | Yes | Event-specific data |

### Server vs Client Timestamps

- **`event_ts`**: Set by server when event is ingested (authoritative)
- **`client_ts`**: Optionally provided by client (for latency analysis)

Use `event_ts` for business logic and analytics. Use `client_ts` only for latency correction studies.

---

## Event Types

### Session Lifecycle

| Event Type | Payload | Description |
|------------|---------|-------------|
| `SESSION_CREATED` | `{mode, filters, count}` | Session created |
| `SESSION_SUBMITTED` | `{reason: "manual"\|"expired"}` | Session finalized |
| `SESSION_EXPIRED` | `{}` | Session auto-expired |
| `REVIEW_OPENED` | `{}` | Review page accessed |

### Navigation

| Event Type | Payload | Description |
|------------|---------|-------------|
| `QUESTION_VIEWED` | `{position}` | Question displayed |
| `NAVIGATE_NEXT` | `{from_position, to_position}` | Next button clicked |
| `NAVIGATE_PREV` | `{from_position, to_position}` | Previous button clicked |
| `NAVIGATE_JUMP` | `{from_position, to_position}` | Jumped to question via navigator |

### Answer Interactions

| Event Type | Payload | Description |
|------------|---------|-------------|
| `ANSWER_SELECTED` | `{position, selected_index}` | Answer chosen |
| `ANSWER_CHANGED` | `{position, from_index, to_index}` | Answer modified |
| `MARK_FOR_REVIEW_TOGGLED` | `{position, marked}` | Review flag toggled |

### Behavioral

| Event Type | Payload | Description |
|------------|---------|-------------|
| `PAUSE_BLUR` | `{state: "blur"\|"focus"}` | Window focus changed |

---

## Payload Guidelines

**Keep payloads small** (≤ 4KB per event):
- Use simple key-value pairs
- Avoid nested objects when possible
- Do NOT include full question text
- Do NOT include PII (Personally Identifiable Information)

**Examples:**

Good:
```json
{
  "position": 5,
  "selected_index": 2
}
```

Bad:
```json
{
  "question": {
    "stem": "Long question text...",
    "options": ["A", "B", "C", "D", "E"],
    "metadata": {...}
  }
}
```

---

## Data Storage

### Database: Append-Only Table

Table: `attempt_events`

**Append-Only Guarantees:**
- Events are NEVER updated or deleted
- Immutable for analytics integrity
- Enforced at application level (no update/delete endpoints)

**Indexes:**
- `(session_id, event_ts)` - Session timeline queries
- `(user_id, event_ts)` - User activity queries
- `(event_type, event_ts)` - Event type analysis
- `(session_id, seq)` - Client sequence verification

**Retention:**
- Events retained indefinitely in Postgres
- Archived to Snowflake for long-term analysis (tasks 138-141)

---

## Client-Side Telemetry

### Batching & Flush Triggers

The frontend telemetry client queues events and flushes them in batches to minimize network overhead.

**Flush Conditions:**
1. Queue size ≥ 10 events
2. Timer (every 12 seconds)
3. Submit button clicked (before redirect)
4. Page unload / visibility change (best-effort)

**Retry Logic:**
- Failed batches retry up to 2 times with exponential backoff
- After max retries, events are dropped (silent fail)

**Best-Effort Guarantee:**
- Telemetry failures NEVER block the UI
- Network errors logged to console only
- No user-facing error messages

### Usage Example

```typescript
import { useTelemetry } from "@/lib/hooks/useTelemetry";

function SessionPlayer() {
  const { track, flush } = useTelemetry(sessionId);

  useEffect(() => {
    track("QUESTION_VIEWED", { position: 5 });
  }, [currentPosition]);

  async function handleSubmit() {
    await flush(); // Ensure all events sent before redirect
    await submitSession();
  }
}
```

---

## Server-Side Emission

Authoritative events are logged automatically from session endpoints:

| Endpoint | Events Emitted |
|----------|----------------|
| `POST /v1/sessions` | `SESSION_CREATED` |
| `POST /v1/sessions/{id}/answer` | `ANSWER_SELECTED`, `ANSWER_CHANGED`, `MARK_FOR_REVIEW_TOGGLED` |
| `POST /v1/sessions/{id}/submit` | `SESSION_SUBMITTED` |
| `GET /v1/sessions/{id}/review` | `REVIEW_OPENED` |

**Best-Effort Logging:**
- Telemetry insert failures are caught and logged
- Primary request continues successfully
- Errors logged to server logs for monitoring

---

## API Endpoints

### POST /v1/telemetry/events

Ingest batch of telemetry events from client.

**Request:**
```json
{
  "source": "web",
  "events": [
    {
      "event_type": "QUESTION_VIEWED",
      "client_ts": "2026-01-20T12:34:56.000Z",
      "seq": 12,
      "session_id": "uuid",
      "question_id": "uuid-or-null",
      "payload": { "position": 3 }
    }
  ]
}
```

**Response:**
```json
{
  "accepted": 5,
  "rejected": 0,
  "rejected_reasons_sample": []
}
```

**Validation:**
- User must own all sessions referenced
- Questions must belong to sessions
- Event type must be in allowed list
- Payload size ≤ 4KB per event
- Batch size ≤ 50 events

**Rejection Handling:**
- Invalid events skipped without failing batch
- Returns count of accepted/rejected
- Sample rejection reasons (max 5)

---

## Data Export

### Snowflake Integration (Future)

**Status:** Stub implemented, full integration planned for tasks 138-141.

**Export Module:** `backend/app/services/telemetry_export.py`

**Planned Features:**
- Scheduled batch exports (e.g., hourly)
- Incremental export (only new events)
- Deduplication tracking
- Error handling and retry
- Export status monitoring

**Current State:**
```python
await export_attempt_events_to_warehouse(since_ts)
# Raises NotImplementedError - planned for tasks 138-141
```

---

## Privacy & Security

### Data Minimization

**Collected:**
- Session IDs, user IDs, question IDs
- Navigation patterns
- Answer selections (index only, not content)
- Timestamps and sequences

**NOT Collected:**
- Question text or option text
- User names or emails
- IP addresses or device fingerprints
- Exact keystrokes or mouse movements

### Access Control

- Students can only submit events for their own sessions
- Session ownership validated on ingestion
- Question membership validated
- Unauthorized access returns 403

### Data Retention

- Events retained indefinitely for analytics
- No automated deletion
- Manual purge only for GDPR/compliance requests

---

## Monitoring & Alerts

### Key Metrics

1. **Ingestion Rate**
   - Events per second
   - Batch size distribution
   - Rejection rate

2. **Client Behavior**
   - Flush frequency
   - Retry rate
   - Queue overflow rate

3. **Server Health**
   - Insert latency (p50, p95, p99)
   - Failed inserts
   - Database load

### Recommended Alerts

- Rejection rate > 5%
- Insert failure rate > 1%
- Batch size anomalies (too large/small)
- Export failures (when implemented)

---

## Troubleshooting

### Events Not Appearing

1. Check client console for errors
2. Verify session ownership (403 errors)
3. Check payload size (must be < 4KB)
4. Verify network connectivity
5. Check server logs for insert failures

### High Rejection Rate

Common causes:
- Session not owned by user
- Question not in session
- Invalid event type
- Payload too large
- Malformed JSON

### Performance Issues

If telemetry impacts performance:
1. Increase flush interval (frontend)
2. Reduce batch size
3. Add database indexes
4. Archive old events to Snowflake

---

## Best Practices

### DO

✅ Keep payloads minimal and focused  
✅ Use event_ts for business logic  
✅ Log errors but continue on failure  
✅ Validate ownership before ingestion  
✅ Monitor rejection rates  

### DON'T

❌ Include PII in payloads  
❌ Fail user requests on telemetry errors  
❌ Trust client_ts for business logic  
❌ Update or delete events  
❌ Block UI for telemetry  

---

## Future Enhancements

Planned for later tasks:
- Real-time dashboards (tasks 138-141)
- Snowflake data warehouse integration
- ML-based learning insights
- Predictive performance analytics
- A/B testing framework
- Anomaly detection

---

**Version:** 1.0  
**Last Updated:** 2026-01-20  
**Related Tasks:** 91-94 (implemented), 138-141 (planned)
