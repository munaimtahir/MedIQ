# API Contracts

## Base URL

- Development: `http://localhost:8000`
- Production: TBD

## Authentication

**Temporary**: Use `X-User-Id` header
- Student: `X-User-Id: student-1`
- Admin: `X-User-Id: admin-1`

## Endpoints

### Syllabus

#### GET /blocks

Get all blocks, optionally filtered by year.

**Query Parameters:**
- `year` (optional): Filter by year (1 or 2)

**Response:**
```json
[
  {
    "id": "A",
    "name": "Anatomy",
    "year": 1,
    "description": "Human anatomy and structure"
  }
]
```

#### GET /themes

Get all themes, optionally filtered by block.

**Query Parameters:**
- `block_id` (optional): Filter by block ID

**Response:**
```json
[
  {
    "id": 1,
    "block_id": "A",
    "name": "Cardiovascular System",
    "description": "Theme: Cardiovascular System"
  }
]
```

### Admin - Questions

#### GET /admin/questions

List all questions (admin only).

**Query Parameters:**
- `skip` (default: 0): Pagination offset
- `limit` (default: 100): Page size
- `published` (optional): Filter by published status (true/false)

**Headers:**
- `X-User-Id`: Must be admin user

**Response:**
```json
[
  {
    "id": 1,
    "theme_id": 1,
    "question_text": "Which of the following...",
    "options": ["Option A", "Option B", "Option C", "Option D", "Option E"],
    "correct_option_index": 0,
    "explanation": "Explanation text",
    "tags": ["tag1", "tag2"],
    "difficulty": "medium",
    "is_published": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": null
  }
]
```

#### POST /admin/questions

Create a new question (admin only).

**Headers:**
- `X-User-Id`: Must be admin user

**Request Body:**
```json
{
  "theme_id": 1,
  "question_text": "Question text here",
  "options": ["A", "B", "C", "D", "E"],
  "correct_option_index": 0,
  "explanation": "Optional explanation",
  "tags": ["tag1", "tag2"],
  "difficulty": "medium"
}
```

**Validation:**
- `options` must have exactly 5 items
- `correct_option_index` must be 0-4
- `tags` required before publishing

**Response:** Question object

#### GET /admin/questions/{id}

Get a question by ID (admin only).

**Response:** Question object

#### PUT /admin/questions/{id}

Update a question (admin only).

**Request Body:** Partial question object (all fields optional)

**Response:** Updated question object

#### POST /admin/questions/{id}/publish

Publish a question (admin only).

**Validation:**
- Question must have tags

**Response:**
```json
{
  "message": "Question published",
  "question_id": 1
}
```

#### POST /admin/questions/{id}/unpublish

Unpublish a question (admin only).

**Response:**
```json
{
  "message": "Question unpublished",
  "question_id": 1
}
```

### Admin - Questions CMS (Tasks 67-72)

The CMS Question Bank provides a full workflow system with versioning, audit logging, and media support.

#### GET /v1/admin/questions

List questions with filtering, pagination, and search.

**Query Parameters:**
- `status` (optional): Filter by status (DRAFT, IN_REVIEW, APPROVED, PUBLISHED)
- `year_id` (optional): Filter by year ID
- `block_id` (optional): Filter by block ID
- `theme_id` (optional): Filter by theme ID
- `difficulty` (optional): Filter by difficulty
- `cognitive_level` (optional): Filter by cognitive level
- `source_book` (optional): Filter by source book
- `q` (optional): Text search on stem
- `page` (default: 1): Page number
- `page_size` (default: 20): Page size (max 100)
- `sort` (default: updated_at): Sort field
- `order` (default: desc): Sort order (asc/desc)

**Authentication:** Bearer token (ADMIN or REVIEWER role required)

**Response:** Array of QuestionListOut objects

#### POST /v1/admin/questions

Create a new question (starts as DRAFT).

**Request Body:**
```json
{
  "stem": "What is 2+2?",
  "option_a": "3",
  "option_b": "4",
  "option_c": "5",
  "option_d": "6",
  "option_e": "7",
  "correct_index": 1,
  "explanation_md": "2+2 equals 4",
  "year_id": 1,
  "block_id": 1,
  "theme_id": 1,
  "difficulty": "easy",
  "cognitive_level": "recall"
}
```

**Response:** QuestionOut object (201 Created)

#### GET /v1/admin/questions/{question_id}

Get a question by ID.

**Response:** QuestionOut object

#### PUT /v1/admin/questions/{question_id}

Update a question. All fields optional.

**Response:** QuestionOut object

#### DELETE /v1/admin/questions/{question_id}

Delete a question (hard delete, ADMIN only).

**Response:** 204 No Content

#### POST /v1/admin/questions/{question_id}/submit

Submit question for review (DRAFT → IN_REVIEW).

**Validation:**
- stem, all 5 options, correct_index required
- year_id, block_id, theme_id required
- difficulty, cognitive_level required

**Response:**
```json
{
  "message": "Question submitted for review",
  "question_id": "uuid",
  "previous_status": "DRAFT",
  "new_status": "IN_REVIEW"
}
```

#### POST /v1/admin/questions/{question_id}/approve

Approve question (IN_REVIEW → APPROVED). Requires ADMIN or REVIEWER.

**Validation:**
- All submit checks plus explanation_md required

**Response:**
```json
{
  "message": "Question approved",
  "question_id": "uuid",
  "previous_status": "IN_REVIEW",
  "new_status": "APPROVED"
}
```

#### POST /v1/admin/questions/{question_id}/reject

Reject question (IN_REVIEW → DRAFT). Requires reason.

**Request Body:**
```json
{
  "reason": "Needs more explanation"
}
```

**Response:**
```json
{
  "message": "Question rejected",
  "question_id": "uuid",
  "previous_status": "IN_REVIEW",
  "new_status": "DRAFT"
}
```

#### POST /v1/admin/questions/{question_id}/publish

Publish question (APPROVED → PUBLISHED). ADMIN only.

**Validation:**
- All approve checks plus source_book and source_page required

**Response:**
```json
{
  "message": "Question published",
  "question_id": "uuid",
  "previous_status": "APPROVED",
  "new_status": "PUBLISHED"
}
```

#### POST /v1/admin/questions/{question_id}/unpublish

Unpublish question (PUBLISHED → APPROVED). ADMIN only.

**Response:**
```json
{
  "message": "Question unpublished",
  "question_id": "uuid",
  "previous_status": "PUBLISHED",
  "new_status": "APPROVED"
}
```

#### GET /v1/admin/questions/{question_id}/versions

Get version history for a question.

**Response:** Array of VersionOut objects

#### GET /v1/admin/questions/{question_id}/versions/{version_id}

Get a specific version of a question.

**Response:** VersionOut object

### Admin - Media

#### POST /v1/admin/media

Upload a media file (image, etc.).

**Request:** multipart/form-data with `file` field

**Allowed MIME types:** image/jpeg, image/png, image/gif, image/webp

**Response:** MediaOut object (201 Created)

#### GET /v1/admin/media/{media_id}

Get media asset information.

**Response:** MediaOut object

#### POST /v1/admin/media/questions/{question_id}/attach

Attach media to a question.

**Request Body:**
```json
{
  "media_id": "uuid",
  "role": "STEM"
}
```

**Roles:** STEM, EXPLANATION, OPTION_A, OPTION_B, OPTION_C, OPTION_D, OPTION_E

**Response:**
```json
{
  "message": "Media attached successfully",
  "question_id": "uuid",
  "media_id": "uuid"
}
```

#### DELETE /v1/admin/media/questions/{question_id}/detach/{media_id}

Detach media from a question.

**Response:** 204 No Content

### Student - Practice & Test Sessions

#### GET /questions

Get published questions (student access).

**Query Parameters:**
- `theme_id` (optional): Filter by theme
- `block_id` (optional): Filter by block
- `limit` (default: 50): Maximum results

**Response:** Array of Question objects (published only)

---

## Test Sessions v1

All session endpoints require authentication. Sessions are owned by the user and enforce access control.

### POST /v1/sessions

Create a new test session with deterministic question selection.

**Request Body:**
```json
{
  "mode": "TUTOR",
  "year": 1,
  "blocks": ["A", "B"],
  "themes": [1, 2, 3],
  "count": 20,
  "duration_seconds": 3600,
  "difficulty": ["EASY", "MEDIUM"],
  "cognitive": ["RECALL", "UNDERSTAND"]
}
```

**Fields:**
- `mode` (required): "TUTOR" or "EXAM"
- `year` (required): 1 or 2
- `blocks` (required): Array of block codes
- `themes` (optional): Array of theme IDs (null = all themes in blocks)
- `count` (required): Number of questions (1-200)
- `duration_seconds` (optional): Test duration in seconds
- `difficulty` (optional): Filter by difficulty levels
- `cognitive` (optional): Filter by cognitive levels

**Response (201):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",
  "mode": "TUTOR",
  "total_questions": 20,
  "started_at": "2026-01-20T14:30:00Z",
  "expires_at": "2026-01-20T15:30:00Z",
  "progress": {
    "answered_count": 0,
    "marked_for_review_count": 0,
    "current_position": 1
  }
}
```

### GET /v1/sessions/{session_id}

Get session state with current question content.

**Response (200):**
```json
{
  "session": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "mode": "TUTOR",
    "status": "ACTIVE",
    "total_questions": 20,
    "started_at": "2026-01-20T14:30:00Z",
    "expires_at": "2026-01-20T15:30:00Z",
    "score_correct": null,
    "score_total": null,
    "score_pct": null
  },
  "progress": {
    "answered_count": 5,
    "marked_for_review_count": 2,
    "current_position": 6
  },
  "questions": [
    {
      "position": 1,
      "question_id": "q-uuid-1",
      "has_answer": true,
      "marked_for_review": false
    }
  ],
  "current_question": {
    "question_id": "q-uuid-6",
    "position": 6,
    "stem": "What is the function of the mitochondria?",
    "option_a": "Protein synthesis",
    "option_b": "Energy production",
    "option_c": "DNA replication",
    "option_d": "Lipid storage",
    "option_e": "Waste removal"
  }
}
```

**Notes:**
- Applies lazy expiry: if `expires_at` has passed, session auto-submits
- Current question does NOT include correct answer or explanation

### POST /v1/sessions/{session_id}/answer

Submit or update an answer.

**Request Body:**
```json
{
  "question_id": "q-uuid-1",
  "selected_index": 2,
  "marked_for_review": false
}
```

**Response (200):**
```json
{
  "answer": {
    "id": "answer-uuid",
    "session_id": "session-uuid",
    "question_id": "q-uuid-1",
    "selected_index": 2,
    "is_correct": true,
    "answered_at": "2026-01-20T14:35:00Z",
    "changed_count": 1,
    "marked_for_review": false
  },
  "progress": {
    "answered_count": 6,
    "marked_for_review_count": 2,
    "current_position": 7
  }
}
```

### POST /v1/sessions/{session_id}/submit

Submit session and compute final score.

**Response (200):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SUBMITTED",
  "score_correct": 17,
  "score_total": 20,
  "score_pct": 85.00,
  "submitted_at": "2026-01-20T15:15:00Z"
}
```

**Notes:**
- Unanswered questions treated as incorrect
- No negative marking
- Session locked after submission

### GET /v1/sessions/{session_id}/review

Get complete review with frozen question content.

**Response (200):**
```json
{
  "session": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "SUBMITTED",
    "score_correct": 17,
    "score_total": 20,
    "score_pct": 85.00
  },
  "items": [
    {
      "question": {
        "question_id": "q-uuid-1",
        "position": 1,
        "stem": "What is the function of the mitochondria?",
        "option_a": "Protein synthesis",
        "option_b": "Energy production",
        "option_c": "DNA replication",
        "option_d": "Lipid storage",
        "option_e": "Waste removal",
        "correct_index": 1,
        "explanation_md": "Mitochondria are the powerhouse..."
      },
      "answer": {
        "question_id": "q-uuid-1",
        "selected_index": 1,
        "is_correct": true,
        "marked_for_review": false,
        "answered_at": "2026-01-20T14:35:00Z",
        "changed_count": 0
      }
    }
  ]
}
```

**Notes:**
- Only available for SUBMITTED or EXPIRED sessions
- Returns frozen content (immune to question edits after session creation)

### Utility

#### POST /seed

Seed the database with demo data (development only).

**Response:**
```json
{
  "message": "Database seeded successfully"
}
```

---

## Telemetry Events

### POST /v1/telemetry/events

Ingest a batch of behavioral telemetry events from the client.

**NOTE:** This is best-effort. Invalid events are skipped without failing the batch.

**Request Body:**
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
    },
    {
      "event_type": "NAVIGATE_NEXT",
      "client_ts": "2026-01-20T12:35:10.000Z",
      "seq": 13,
      "session_id": "uuid",
      "payload": { "from_position": 3, "to_position": 4 }
    }
  ]
}
```

**Fields:**
- `source` (required): Event source ("web", "mobile", "api")
- `events` (required): Array of events (max 50)
  - `event_type` (required): Event type (see allowed types in observability.md)
  - `client_ts` (optional): Client-side timestamp
  - `seq` (optional): Client sequence number
  - `session_id` (required): Session UUID
  - `question_id` (optional): Question UUID
  - `payload` (required): Event-specific data (max 4KB)

**Response (200):**
```json
{
  "accepted": 2,
  "rejected": 0,
  "rejected_reasons_sample": []
}
```

**Validation:**
- User must own the session
- Question (if provided) must belong to session
- Event type must be in allowed list
- Payload size ≤ 4KB per event
- Batch size ≤ 50 events

**Allowed Event Types:**
- `SESSION_CREATED`, `SESSION_SUBMITTED`, `SESSION_EXPIRED`, `REVIEW_OPENED`
- `QUESTION_VIEWED`, `NAVIGATE_NEXT`, `NAVIGATE_PREV`, `NAVIGATE_JUMP`
- `ANSWER_SELECTED`, `ANSWER_CHANGED`, `MARK_FOR_REVIEW_TOGGLED`
- `PAUSE_BLUR`

**Notes:**
- Events are stored append-only (never updated/deleted)
- Server sets `event_ts` (do not trust client timestamp for business logic)
- Telemetry failures must not impact user experience
- See `docs/observability.md` for full details

**Errors:**
- `400`: Validation error (invalid event type, payload too large, batch too large)
- `403`: Unauthorized (session not owned by user, question not in session)

---

## Learning Engine API v0

All Learning Engine endpoints follow a standardized response envelope and enforce role-based access control.

### Standard Response Envelope

```json
{
  "ok": true,
  "run_id": "uuid",
  "algo": {
    "key": "mastery",
    "version": "v0"
  },
  "params_id": "uuid",
  "summary": { ... }
}
```

### Authentication & Authorization

- **Students**: Can only operate on their own data
- **Admins/Reviewers**: Can specify any `user_id`
- **Session-scoped endpoints**: Enforce session ownership

---

### POST /v1/learning/mastery/recompute

Recompute Mastery v0 scores for a user.

**Authentication:** Required (Student/Admin/Reviewer)

**Request Body:**
```json
{
  "user_id": "uuid | null",
  "year": 1,
  "block_id": "uuid | null",
  "theme_id": "uuid | null",
  "dry_run": false
}
```

**Request Fields:**
- `user_id` (optional): Target user (defaults to current user; students cannot specify another user)
- `year` (required): Academic year (1-6)
- `block_id` (optional): Filter to specific block
- `theme_id` (optional): Filter to specific theme
- `dry_run` (optional): If true, compute counts only without DB writes

**Response:**
```json
{
  "ok": true,
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "algo": {
    "key": "mastery",
    "version": "v0"
  },
  "params_id": "660e8400-e29b-41d4-a716-446655440000",
  "summary": {
    "themes_processed": 12,
    "records_upserted": 12,
    "dry_run": false
  }
}
```

**Use Cases:**
- Student recomputes their own mastery after completing sessions
- Admin triggers mastery recompute for specific user
- Dry-run to preview impact before actual computation

---

### POST /v1/learning/revision/plan

Generate revision queue entries for a user.

**Authentication:** Required (Student/Admin/Reviewer)

**Request Body:**
```json
{
  "user_id": "uuid | null",
  "year": 1,
  "block_id": "uuid | null"
}
```

**Request Fields:**
- `user_id` (optional): Target user (defaults to current user)
- `year` (required): Academic year (1-6)
- `block_id` (optional): Filter to specific block

**Response:**
```json
{
  "ok": true,
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "algo": {
    "key": "revision",
    "version": "v0"
  },
  "params_id": "660e8400-e29b-41d4-a716-446655440000",
  "summary": {
    "generated": 14,
    "due_today": 6
  }
}
```

**Use Cases:**
- Student generates their revision schedule
- Admin triggers revision planning for specific user
- Nightly job regenerates queues for all users

---

### POST /v1/learning/adaptive/next

Select next best questions using Adaptive Selection.

**Versions:**
- **v1 (default)**: Constrained Thompson Sampling over themes with BKT/FSRS/Elo integration
- **v0 (fallback)**: Rule-based selection if v1 not configured

**Authentication:** Required (Student/Admin/Reviewer)

**Request Body:**
```json
{
  "user_id": "uuid | null",
  "year": 1,
  "block_ids": [1, 2],
  "theme_ids": [10, 20] | null,
  "count": 20,
  "mode": "tutor",
  "source": "mixed"
}
```

**Request Fields:**
- `user_id` (optional): Target user (defaults to current user)
- `year` (required): Academic year (1-6)
- `block_ids` (required): List of block IDs (integers, min 1)
- `theme_ids` (optional): Filter to specific themes
- `count` (required): Number of questions to select (1-100)
- `mode` (required): "tutor", "exam", or "revision"
- `source` (optional): "mixed", "revision", or "weakness" (default: "mixed")

**Response (v1):**
```json
{
  "ok": true,
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "algo": {
    "key": "adaptive_selection",
    "version": "v1"
  },
  "params_id": "660e8400-e29b-41d4-a716-446655440000",
  "summary": {
    "count": 20,
    "question_ids": ["uuid1", "uuid2", "..."],
    "plan": {
      "themes": [
        {
          "theme_id": 123,
          "quota": 10,
          "base_priority": 0.73,
          "sampled_y": 0.41,
          "final_score": 0.34
        }
      ],
      "due_ratio": 0.65,
      "p_band": {"low": 0.55, "high": 0.80},
      "stats": {
        "excluded_recent": 12,
        "explore_used": 2,
        "avg_p_correct": 0.68
      }
    }
  }
}
```

**Response (v0 fallback):**
```json
{
  "ok": true,
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "algo": {
    "key": "adaptive",
    "version": "v0"
  },
  "params_id": "660e8400-e29b-41d4-a716-446655440000",
  "summary": {
    "count": 20,
    "themes_used": [],
    "difficulty_distribution": {
      "easy": 4,
      "medium": 12,
      "hard": 4
    },
    "question_ids": ["uuid1", "uuid2", "..."]
  }
}
```

**v1 Features:**
- **Thompson Sampling**: Per-user per-theme Beta posteriors for explore/exploit balance
- **BKT Integration**: Prioritizes themes with low mastery (weakness)
- **FSRS Integration**: Prioritizes due concepts in revision mode
- **Elo Challenge Band**: Selects questions with optimal difficulty (p(correct) ∈ [0.55, 0.80])
- **Deterministic**: Same inputs on same day produce same output (seeded RNG)
- **Explainable**: Plan shows themes, scores, and selection reasoning

**v1 Plan Fields:**
- `themes`: Selected themes with quota allocation and Thompson scores
- `due_ratio`: Fraction of questions from FSRS due concepts
- `p_band`: Elo difficulty target range
- `stats.excluded_recent`: Questions excluded due to anti-repeat filter
- `stats.explore_used`: Questions selected for exploration
- `stats.avg_p_correct`: Average predicted probability of correctness

**Important Notes:**
- Does NOT create a session (returns question_ids only)
- Deterministic output for same inputs (seeded by user_id + date + params)
- Prioritizes weak themes, due concepts, and optimal difficulty
- Interleaves questions across themes (except in exam mode)

**Use Cases:**
- Practice Builder: Get optimal questions for user learning
- Revision Mode: Get questions for FSRS due concepts
- Adaptive Test: Get difficulty-matched questions
- Weakness Mode: Focus on lowest mastery themes

---

### POST /v1/learning/difficulty/update

Update question difficulty ratings for a submitted session.

**Authentication:** Required (Student/Admin/Reviewer)

**Request Body:**
```json
{
  "session_id": "uuid"
}
```

**Request Fields:**
- `session_id` (required): Session ID (must be owned by user or user must be admin)

**Response:**
```json
{
  "ok": true,
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "algo": {
    "key": "difficulty",
    "version": "v0"
  },
  "params_id": "660e8400-e29b-41d4-a716-446655440000",
  "summary": {
    "questions_updated": 18,
    "avg_delta": -2.14
  }
}
```

**Important Notes:**
- Idempotent (safe to call multiple times)
- Automatically called on session submission
- Manual call useful for re-rating after param changes

**Use Cases:**
- Automatic: Called on every session submission
- Manual: Admin triggers re-rating for specific session
- Batch: Re-rate all sessions after param tuning

---

### POST /v1/learning/mistakes/classify

Classify mistakes for a submitted session.

**Authentication:** Required (Student/Admin/Reviewer)

**Request Body:**
```json
{
  "session_id": "uuid"
}
```

**Request Fields:**
- `session_id` (required): Session ID (must be owned by user or user must be admin)

**Response:**
```json
{
  "ok": true,
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "algo": {
    "key": "mistakes",
    "version": "v0"
  },
  "params_id": "660e8400-e29b-41d4-a716-446655440000",
  "summary": {
    "total_wrong": 9,
    "classified": 9,
    "counts_by_type": {
      "FAST_WRONG": 3,
      "CHANGED_ANSWER_WRONG": 2,
      "KNOWLEDGE_GAP": 4
    }
  }
}
```

**Mistake Types:**
- `CHANGED_ANSWER_WRONG` - Changed answer, still wrong
- `TIME_PRESSURE_WRONG` - Answered under time pressure
- `FAST_WRONG` - Answered too quickly
- `DISTRACTED_WRONG` - Tab-away/blur during question
- `SLOW_WRONG` - Spent long time, still wrong
- `KNOWLEDGE_GAP` - Fallback for other wrong answers

**Important Notes:**
- Idempotent (safe to call multiple times)
- Automatically called on session submission
- Only classifies wrong answers (correct answers ignored)

**Use Cases:**
- Automatic: Called on every session submission
- Manual: Admin triggers re-classification for specific session
- Analytics: Query mistake patterns for user/theme

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

**Status Codes:**
- `200`: Success
- `201`: Created
- `204`: No Content
- `400`: Bad Request (validation error)
- `401`: Unauthorized (missing/invalid X-User-Id)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Internal Server Error

## Rate Limiting

Not implemented yet. Planned for production.

## Versioning

Current version: `v1.0.0`

API versioning strategy: TBD (headers or URL path)

