# Data Model Documentation

## Overview

This document describes the database schema, entity relationships, and data flow for the Medical Exam Platform.

## Database: PostgreSQL

### Entity Relationship Diagram

```
User (1) ──< (N) AttemptSession
                │
                └──< (N) AttemptAnswer ──> (1) Question

Block (1) ──< (N) Theme ──< (N) Question
```

## Core Entities

### User

**Table:** `users`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String (PK) | NOT NULL | Unique user identifier |
| role | String | NOT NULL | "student" or "admin" |
| created_at | DateTime | DEFAULT now() | Account creation timestamp |

**Relationships:**
- One-to-Many: `AttemptSession` (user can have multiple sessions)

**Indexes:**
- Primary Key: `id`
- Index: `role` (for role-based queries)

---

### Block

**Table:** `blocks`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String (PK) | NOT NULL | Block identifier (A-F) |
| name | String | NOT NULL | Block name (e.g., "Anatomy") |
| year | Integer | NOT NULL | Academic year (1 or 2) |
| description | Text | NULL | Block description |

**Relationships:**
- One-to-Many: `Theme` (block contains multiple themes)

**Indexes:**
- Primary Key: `id`
- Index: `year` (for year-based filtering)

**Example Data:**
- `id: "A"`, `name: "Anatomy"`, `year: 1`
- `id: "B"`, `name: "Biochemistry"`, `year: 1`

---

### Theme

**Table:** `themes`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer (PK) | AUTO_INCREMENT | Unique theme identifier |
| block_id | String (FK) | NOT NULL → blocks.id | Parent block |
| name | String | NOT NULL | Theme name |
| description | Text | NULL | Theme description |

**Relationships:**
- Many-to-One: `Block` (theme belongs to one block)
- One-to-Many: `Question` (theme contains multiple questions)

**Indexes:**
- Primary Key: `id`
- Foreign Key: `block_id`
- Index: `block_id` (for block-based queries)

---

### Question (Legacy)

**Table:** `questions_legacy` (renamed from `questions` in CMS migration)

Legacy question model with Integer ID. See CMS Question below for new structure.

### Question (CMS - Tasks 67-72)

**Table:** `questions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID (PK) | NOT NULL | Unique question identifier |
| stem | Text | NULL | Question stem (supports markdown/latex) |
| option_a | Text | NULL | Option A |
| option_b | Text | NULL | Option B |
| option_c | Text | NULL | Option C |
| option_d | Text | NULL | Option D |
| option_e | Text | NULL | Option E |
| correct_index | SmallInteger | NULL, 0-4 | Index of correct option |
| explanation_md | Text | NULL | Explanation in markdown |
| status | Enum | NOT NULL, DEFAULT DRAFT | Workflow status: DRAFT, IN_REVIEW, APPROVED, PUBLISHED |
| year_id | Integer (FK) | NULL → years.id | Year anchor |
| block_id | Integer (FK) | NULL → blocks.id | Block anchor |
| theme_id | Integer (FK) | NULL → themes.id | Theme anchor |
| topic_id | Integer | NULL | Topic anchor (no FK yet) |
| concept_id | Integer | NULL | Concept anchor (no FK yet) |
| cognitive_level | String(50) | NULL | Cognitive level |
| difficulty | String(50) | NULL | Difficulty level |
| source_book | String(200) | NULL | Source book |
| source_page | String(50) | NULL | Source page (e.g., "p. 12-13") |
| source_ref | String(100) | NULL | Source reference |
| created_by | UUID (FK) | NOT NULL → users.id | Creator |
| updated_by | UUID (FK) | NOT NULL → users.id | Last updater |
| approved_by | UUID (FK) | NULL → users.id | Approver |
| approved_at | DateTime | NULL | Approval timestamp |
| published_at | DateTime | NULL | Publication timestamp |
| created_at | DateTime | DEFAULT now() | Creation timestamp |
| updated_at | DateTime | NULL | Last update timestamp |

**Relationships:**
- Many-to-One: `Year`, `Block`, `Theme`
- One-to-Many: `QuestionVersion`, `QuestionMedia`

**Constraints:**
- `correct_index` must be 0-4 (check constraint)
- Status transitions enforced in application layer
- Required fields vary by status (enforced in workflow)

**Indexes:**
- Primary Key: `id`
- Index: `status`, `updated_at`, `theme_id`, `block_id`, `year_id`

**Workflow:**
- DRAFT → IN_REVIEW (submit): requires stem, 5 options, correct_index, year_id, block_id, theme_id, difficulty, cognitive_level
- IN_REVIEW → APPROVED (approve): all submit checks + explanation_md
- IN_REVIEW → DRAFT (reject): requires reason
- APPROVED → PUBLISHED (publish): all approve checks + source_book, source_page
- PUBLISHED → APPROVED (unpublish)

### QuestionVersion

**Table:** `question_versions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID (PK) | NOT NULL | Version identifier |
| question_id | UUID (FK) | NOT NULL → questions.id | Question reference |
| version_no | Integer | NOT NULL | Version number (starts at 1) |
| snapshot | JSONB | NOT NULL | Full snapshot of question fields |
| change_kind | Enum | NOT NULL | CREATE, EDIT, STATUS_CHANGE, PUBLISH, UNPUBLISH, IMPORT |
| change_reason | String(500) | NULL | Reason for change |
| changed_by | UUID (FK) | NOT NULL → users.id | User who made change |
| changed_at | DateTime | DEFAULT now() | Change timestamp |

**Indexes:**
- Primary Key: `id`
- Unique: `(question_id, version_no)`
- Index: `question_id`, `version_no`

### MediaAsset

**Table:** `media_assets`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID (PK) | NOT NULL | Media identifier |
| storage_provider | Enum | NOT NULL, DEFAULT LOCAL | LOCAL or S3 |
| path | String(500) | NOT NULL | Storage path |
| mime_type | String(100) | NOT NULL | MIME type |
| size_bytes | Integer | NOT NULL | File size |
| sha256 | String(64) | NULL | SHA256 hash (for deduplication) |
| created_by | UUID (FK) | NOT NULL → users.id | Creator |
| created_at | DateTime | DEFAULT now() | Creation timestamp |

**Indexes:**
- Primary Key: `id`
- Index: `sha256` (for deduplication)

### QuestionMedia

**Table:** `question_media`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID (PK) | NOT NULL | Attachment identifier |
| question_id | UUID (FK) | NOT NULL → questions.id | Question reference |
| media_id | UUID (FK) | NOT NULL → media_assets.id | Media reference |
| role | Enum | NOT NULL | STEM, EXPLANATION, OPTION_A-E |
| created_at | DateTime | DEFAULT now() | Creation timestamp |

**Indexes:**
- Primary Key: `id`
- Index: `question_id`, `media_id`

### AuditLog

**Table:** `audit_log`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID (PK) | NOT NULL | Audit entry identifier |
| actor_user_id | UUID (FK) | NOT NULL → users.id | User who performed action |
| action | String(100) | NOT NULL | Action name (e.g., "question.create") |
| entity_type | String(50) | NOT NULL | Entity type (QUESTION, MEDIA) |
| entity_id | UUID | NOT NULL | Entity identifier |
| before | JSONB | NULL | State before change |
| after | JSONB | NULL | State after change |
| meta | JSONB | NULL | Additional metadata (IP, user-agent, request-id) |
| created_at | DateTime | DEFAULT now() | Timestamp |

**Indexes:**
- Primary Key: `id`
- Index: `entity_type`, `entity_id`, `created_at`, `actor_user_id`

---

### AttemptSession

**Table:** `attempt_sessions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer (PK) | AUTO_INCREMENT | Unique session identifier |
| user_id | String (FK) | NOT NULL → users.id | Student user |
| question_count | Integer | NOT NULL | Number of questions |
| time_limit_minutes | Integer | NOT NULL | Time limit in minutes |
| question_ids | JSON | NOT NULL | Array of question IDs |
| is_submitted | Boolean | DEFAULT false | Submission status |
| started_at | DateTime | DEFAULT now() | Session start time |
| submitted_at | DateTime | NULL | Submission timestamp |

**Relationships:**
- Many-to-One: `User` (session belongs to one user)
- One-to-Many: `AttemptAnswer` (session contains multiple answers)

**Indexes:**
- Primary Key: `id`
- Foreign Key: `user_id`
- Index: `user_id` (for user session queries)
- Index: `is_submitted` (for submission status queries)
- Index: `started_at` (for chronological queries)

**Example JSON:**
```json
{
  "question_ids": [1, 2, 3, 4, 5]
}
```

---

### AttemptAnswer

**Table:** `attempt_answers`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer (PK) | AUTO_INCREMENT | Unique answer identifier |
| session_id | Integer (FK) | NOT NULL → attempt_sessions.id | Parent session |
| question_id | Integer (FK) | NOT NULL → questions.id | Question answered |
| selected_option_index | Integer | NOT NULL, 0-4 | Selected option |
| is_correct | Boolean | NOT NULL | Correctness flag |
| is_marked_for_review | Boolean | DEFAULT false | Review flag |
| answered_at | DateTime | DEFAULT now() | Answer timestamp |

**Relationships:**
- Many-to-One: `AttemptSession` (answer belongs to one session)
- Many-to-One: `Question` (answer references one question)

**Indexes:**
- Primary Key: `id`
- Foreign Key: `session_id`
- Foreign Key: `question_id`
- Unique: `(session_id, question_id)` (one answer per question per session)
- Index: `is_correct` (for correctness analysis)

---

## Data Flow

### Question Lifecycle

1. **Creation** (Admin)
   - Question created with `is_published = false`
   - Tags optional at creation

2. **Validation** (Admin)
   - Tags required before publishing
   - Options validated (exactly 5)
   - Correct index validated (0-4)

3. **Publishing** (Admin)
   - `is_published = true`
   - Question becomes available to students

4. **Student Access**
   - Only published questions visible via `GET /questions`
   - Questions filtered by `is_published = true`

### Session Lifecycle

1. **Creation**
   - Student selects block/theme
   - Backend selects published questions
   - Session created with `is_submitted = false`

2. **Answering**
   - Student submits answers via `POST /sessions/{id}/answer`
   - Answers stored with correctness computed
   - Can mark for review

3. **Submission**
   - `POST /sessions/{id}/submit`
   - `is_submitted = true`
   - `submitted_at` timestamp set
   - Score calculated

4. **Review**
   - `GET /sessions/{id}/review`
   - Returns all answers with explanations
   - Shows correct/incorrect status

---

## Data Integrity Rules

### Referential Integrity

- All foreign keys enforce referential integrity
- Cascade rules:
  - Deleting a user → cascade delete sessions → cascade delete answers
  - Deleting a block → prevent if themes exist (or cascade)
  - Deleting a theme → prevent if questions exist (or cascade)
  - Deleting a question → prevent if answers exist (or soft delete)

### Business Rules

1. **Question Publishing**
   - Tags required before `is_published = true`
   - Cannot unpublish if used in submitted sessions (consider soft delete)

2. **Session Submission**
   - Cannot submit if already submitted
   - Cannot answer after submission

3. **Answer Validation**
   - `selected_option_index` must be 0-4
   - One answer per question per session (enforced by unique constraint)

---

## Future Extensions

### Planned Entities (Not Implemented)

1. **UserProfile**
   - Extended user information
   - Preferences, settings

2. **Concept** (Neo4j)
   - Knowledge graph nodes
   - Relationships between concepts

3. **QuestionVersion**
   - Version history for questions
   - Audit trail

4. **MockExam**
   - Full-length exam configurations
   - Blueprint definitions

5. **AnalyticsEvent**
   - User interaction tracking
   - Performance metrics

---

## Data Seeding

See `backend/seed.py` for initial data:

- **Users**: `admin-1`, `student-1`
- **Blocks**: A-F for Year 1 and Year 2
- **Themes**: 5-10 themes per block
- **Questions**: ~30 published MCQs

Run seeding:
```bash
# Via API
POST http://localhost:8000/seed

# Or directly
cd backend
python -c "from seed import seed_database; seed_database()"
```

---

## Migration Strategy

### Current State
- SQLAlchemy models define schema
- Tables created via `Base.metadata.create_all()`

### Future State
- Use Alembic for migrations
- Version-controlled schema changes
- Rollback support

### Migration Commands (Future)
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Performance Considerations

### Indexing Strategy

**High-frequency queries:**
- `questions.is_published` (student question lists)
- `attempt_sessions.user_id` (user session history)
- `attempt_answers.session_id` (session review)

**Composite indexes (future):**
- `(theme_id, is_published)` for theme-based question queries
- `(user_id, is_submitted)` for user session queries

### Query Optimization

1. **Question Lists**
   - Use `is_published` index
   - Limit results (default: 50)
   - Consider pagination for large datasets

2. **Session Review**
   - Join `attempt_answers` with `questions` efficiently
   - Pre-fetch all questions for a session

3. **Analytics Queries** (Future)
   - Consider read replicas
   - Materialized views for common aggregations

---

## Data Retention

### Current Policy
- No automatic deletion
- All data retained indefinitely

### Future Policy (To Be Defined)
- Archive old sessions after X months
- Soft delete for questions (maintain history)
- Compliance with data protection regulations

---

## Backup Strategy

### Current State
- Docker volume persistence
- Manual backup via `pg_dump`

### Recommended (Production)
- Automated daily backups
- Point-in-time recovery
- Off-site backup storage
- Backup retention policy

