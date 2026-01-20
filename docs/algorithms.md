# Learning Intelligence Engine — Algorithms Documentation

**Last Updated:** January 21, 2026  
**Status:** Foundation complete (Tasks 101-102), algorithms pending (Tasks 103+)

---

## Overview

The Learning Intelligence Engine is a versioned, auditable system for computing personalized learning metrics and recommendations. All algorithms are:

- **Versioned:** Each algorithm has explicit version strings (v0, v1, etc.)
- **Parameterized:** Parameters are separate from code versions and can be tuned independently
- **Auditable:** Every run is logged with inputs, outputs, and execution metadata
- **Deterministic:** Same version + same params + same data = same results

---

## Algorithm Keys

The system includes five core algorithms:

| Algo Key | Purpose | Status |
|----------|---------|--------|
| `mastery` | Track student understanding levels per block/theme | v0 seeded (stub) |
| `revision` | Schedule questions for spaced repetition | v0 seeded (stub) |
| `difficulty` | Estimate question difficulty from performance data | v0 seeded (stub) |
| `adaptive` | Select optimal questions for learning | v0 seeded (stub) |
| `mistakes` | Identify common error patterns | v0 seeded (stub) |

**Note:** v0 implementations are stubs that raise `NotImplementedError`. Actual compute logic will be implemented in Tasks 103+ / 111+.

---

## Versioning Rules

### Algorithm Versions

- Each algorithm has multiple **versions** (e.g., v0, v1, v2)
- Only **one ACTIVE version** per algorithm at any time
- Other versions can be DEPRECATED or EXPERIMENTAL
- Switching the active version is a deliberate, audited action

**Database Table:** `algo_versions`

**Fields:**
- `id` (UUID): Unique version identifier
- `algo_key` (string): Algorithm name (mastery, revision, etc.)
- `version` (string): Version string (v0, v1, etc.)
- `status` (string): ACTIVE | DEPRECATED | EXPERIMENTAL
- `description` (text): Human-readable description
- `created_at`, `updated_at`: Timestamps

**Constraints:**
- Unique constraint on `(algo_key, version)`
- Index on `(algo_key, status)` for fast active lookups

---

## Parameter Sets

### Separation from Code Version

- **Parameters are independent of code version**
- You can tune params without changing the version string
- Each algorithm version can have **multiple parameter sets**
- Only **one is_active=true** per algo_version at any time

**Why separate?**
- Allows A/B testing of parameters
- Historical reproducibility (know which params were used)
- Rollback without code changes

**Database Table:** `algo_params`

**Fields:**
- `id` (UUID): Unique params identifier
- `algo_version_id` (UUID): Foreign key to algo_versions
- `params_json` (JSONB): Parameter dictionary
- `checksum` (string): SHA256 of normalized params (for deduplication)
- `is_active` (boolean): Whether this is the active param set
- `created_by_user_id` (UUID): Optional admin who created params
- `created_at`, `updated_at`: Timestamps

**Constraints:**
- Index on `(algo_version_id, is_active)`

**Example params_json:**

```json
{
  "threshold": 0.7,
  "decay_factor": 0.95,
  "min_attempts": 5
}
```

---

## Active Version + Params Resolution

The Learning Engine exposes helper functions to resolve the active state:

```python
from app.learning_engine import resolve_active

# Returns (AlgoVersion, AlgoParams) or (None, None)
version, params = await resolve_active(db, "mastery")

if version and params:
    # Run algorithm with these settings
    result = await compute_mastery_v0(db, input_data, params.params_json)
```

**Resolution Steps:**
1. Find ACTIVE algo_version for given algo_key
2. Find is_active=true params for that version
3. Return both or None if missing

---

## Run Logging

### Why Log Runs?

Every algorithm execution is logged to provide:
- **Audit trail:** Who ran what, when, and why
- **Debugging:** Inputs/outputs for failed runs
- **Performance tracking:** Execution time, success rate
- **Compliance:** Reproducibility for regulatory requirements

**Database Table:** `algo_runs`

**Fields:**
- `id` (UUID): Unique run identifier
- `algo_version_id` (UUID): Which version was used
- `params_id` (UUID): Which parameter set was used
- `user_id` (UUID): Optional user (if user-specific run)
- `session_id` (UUID): Optional session (if session-triggered)
- `trigger` (string): manual | submit | nightly | cron | api
- `status` (string): RUNNING | SUCCESS | FAILED
- `started_at`, `completed_at`: Timestamps
- `input_summary_json` (JSONB): Input metadata
- `output_summary_json` (JSONB): Output metadata
- `error_message` (text): Error details if FAILED

**Indexes:**
- `(user_id, started_at)`: Fast user-specific lookups
- `(algo_version_id, started_at)`: Version performance analysis
- `(session_id)`: Session-triggered run lookups

### Logging Workflow

```python
from app.learning_engine import log_run_start, log_run_success, log_run_failure

# 1. Start run
run = await log_run_start(
    db,
    algo_version_id=version.id,
    params_id=params.id,
    user_id=current_user.id,
    trigger="submit",
    input_summary={"block_id": 1, "theme_id": 5}
)

try:
    # 2. Execute algorithm
    result = await compute_mastery_v0(db, input_data, params.params_json)
    
    # 3. Log success
    await log_run_success(
        db,
        run_id=run.id,
        output_summary={"mastery_scores": result.mastery_scores}
    )
except Exception as e:
    # 3. Log failure
    await log_run_failure(
        db,
        run_id=run.id,
        error_message=str(e)
    )
```

---

## Default Parameters (v0)

Default parameter sets are seeded automatically for all v0 algorithms:

### Mastery v0
```json
{
  "lookback_days": 90,
  "min_attempts": 5,
  "recency_buckets": [
    {"days": 7, "weight": 0.50},
    {"days": 30, "weight": 0.30},
    {"days": 90, "weight": 0.20}
  ],
  "difficulty_weights": {
    "easy": 0.90,
    "medium": 1.00,
    "hard": 1.10
  },
  "use_difficulty": false
}
```

### Revision v0
```json
{
  "horizon_days": 7,
  "min_attempts": 5,
  "mastery_bands": [
    {"name": "weak", "max": 0.39},
    {"name": "medium", "max": 0.69},
    {"name": "strong", "max": 0.84},
    {"name": "mastered", "max": 1.00}
  ],
  "spacing_days": {
    "weak": 1,
    "medium": 2,
    "strong": 5,
    "mastered": 12
  },
  "question_counts": {
    "weak": [15, 20],
    "medium": [10, 15],
    "strong": [5, 10],
    "mastered": [5, 5]
  },
  "priority_weights": {
    "mastery_inverse": 70,
    "recency": 2,
    "low_data_bonus": 10
  }
}
```

### Difficulty v0
```json
{
  "window_size": 100,
  "min_attempts": 10
}
```

### Adaptive v0
```json
{
  "exploration_rate": 0.2,
  "target_accuracy": 0.75
}
```

### Mistakes v0
```json
{
  "min_frequency": 3,
  "lookback_days": 90
}
```

---

## API Endpoints

### GET /v1/learning/info

Returns the current state of all learning algorithms.

**Authentication:** Required (any authenticated user)

**Response:**

```json
{
  "algorithms": [
    {
      "algo_key": "mastery",
      "active_version": "v0",
      "status": "ACTIVE",
      "active_params": {
        "threshold": 0.7,
        "decay_factor": 0.95,
        "min_attempts": 5
      },
      "updated_at": "2026-01-21T12:00:00Z"
    },
    {
      "algo_key": "revision",
      "active_version": "v0",
      "status": "ACTIVE",
      "active_params": {
        "intervals": [1, 3, 7, 14, 30],
        "ease_factor": 2.5
      },
      "updated_at": "2026-01-21T12:00:00Z"
    }
    // ... other algorithms
  ]
}
```

**Use Cases:**
- Display algorithm configuration to admins
- Verify active versions in production
- Debugging (check if expected version is active)

---

## Mastery v0 — Implemented ✅

**Status:** Fully implemented (Tasks 103-104)  
**Database Table:** `user_theme_mastery`  
**Granularity:** Theme-level (not concept-level)

### Purpose

Track student understanding levels per theme using recency-weighted accuracy from completed practice sessions.

### Formula

```
mastery_score = Σ (bucket_accuracy × bucket_weight)
```

Where:
- **bucket_accuracy** = correct / total within time bucket
- **bucket_weight** = configured weight (defaults: 7d=0.5, 30d=0.3, 90d=0.2)
- Recent attempts weighted more heavily

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lookback_days` | int | 90 | How far back to consider attempts |
| `min_attempts` | int | 5 | Minimum attempts for confident score |
| `recency_buckets` | array | See below | Time buckets with weights |
| `difficulty_weights` | object | `{easy: 0.9, medium: 1.0, hard: 1.1}` | Difficulty adjustment multipliers |
| `use_difficulty` | boolean | false | Whether to apply difficulty weighting |

**Default Recency Buckets:**
```json
[
  {"days": 7, "weight": 0.50},   // Last week: 50% weight
  {"days": 30, "weight": 0.30},  // Last month: 30% weight
  {"days": 90, "weight": 0.20}   // Last 90 days: 20% weight
]
```

### Behavior

1. **Data Sources:**
   - Only `SUBMITTED` or `EXPIRED` sessions
   - Uses frozen question tags (block/theme/year from `session_questions.snapshot_json` or `question_version`)
   - Never uses live question tags (they may change later)

2. **Minimum Attempts:**
   - If `attempts_total < min_attempts`: `mastery_score = 0.0`
   - Breakdown includes `"reason": "insufficient_attempts"`

3. **Recency Weighting:**
   - More recent attempts count more
   - Attempts outside `lookback_days` ignored entirely
   - Each bucket contributes: `bucket_accuracy × bucket_weight`

4. **Difficulty Adjustment (Optional):**
   - If `use_difficulty = true` and difficulty available in frozen data
   - Easy questions weighted 0.9× (less credit for correctness)
   - Medium questions weighted 1.0× (normal)
   - Hard questions weighted 1.1× (more credit for correctness)

5. **Upsert Behavior:**
   - Recomputing updates existing rows
   - Unique constraint on `(user_id, theme_id)`
   - Provenance tracked: `algo_version_id`, `params_id`, `run_id`

### Database Schema

**Table:** `user_theme_mastery`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK to users |
| `year` | int | Academic year |
| `block_id` | int | FK to blocks |
| `theme_id` | int | FK to themes |
| `attempts_total` | int | Total attempts in lookback |
| `correct_total` | int | Total correct in lookback |
| `accuracy_pct` | numeric(5,2) | Simple accuracy percentage |
| `mastery_score` | numeric(6,4) | Recency-weighted score (0..1) |
| `last_attempt_at` | timestamptz | Most recent attempt timestamp |
| `computed_at` | timestamptz | When mastery was computed |
| `algo_version_id` | UUID | FK to algo_versions |
| `params_id` | UUID | FK to algo_params |
| `run_id` | UUID | FK to algo_runs |
| `breakdown_json` | JSONB | Explainability data |

**Indexes:**
- `(user_id, theme_id)` UNIQUE
- `(user_id, mastery_score)` - Find weakest/strongest themes
- `(user_id, computed_at)` - Freshness queries
- `(theme_id, mastery_score)` - Theme-level analytics

### Breakdown JSON Structure

**Sufficient Attempts:**
```json
{
  "total_attempts": 12,
  "buckets": {
    "7d": {
      "attempts": 3,
      "correct": 2,
      "accuracy": 0.6667,
      "weight": 0.50,
      "contribution": 0.3333
    },
    "30d": {
      "attempts": 5,
      "correct": 4,
      "accuracy": 0.8000,
      "weight": 0.30,
      "contribution": 0.2400
    },
    "90d": {
      "attempts": 12,
      "correct": 9,
      "accuracy": 0.7500,
      "weight": 0.20,
      "contribution": 0.1500
    }
  },
  "mastery_score": 0.7233,
  "use_difficulty": false
}
```

**Insufficient Attempts:**
```json
{
  "reason": "insufficient_attempts",
  "required": 5,
  "actual": 2
}
```

### Example Usage

```python
from app.learning_engine.mastery.service import recompute_mastery_v0_for_user

# Recompute for a user
result = await recompute_mastery_v0_for_user(db, user_id=user.id)

# Returns:
{
  "themes_computed": 8,
  "records_upserted": 8,
  "run_id": "uuid"
}
```

### Querying Mastery

```python
from app.models.learning_mastery import UserThemeMastery

# Get user's weakest themes
stmt = select(UserThemeMastery).where(
    UserThemeMastery.user_id == user.id,
    UserThemeMastery.mastery_score < 0.7,
).order_by(UserThemeMastery.mastery_score.asc())

weak_themes = await db.execute(stmt)
```

### Future Enhancements (Out of Scope for v0)

- **Concept-level mastery** (when concept graph is active)
- **BKT (Bayesian Knowledge Tracing)** for v1
- **Forgetting curves** (time-decay model)
- **Skill transfer** (related themes influence)
- **Confidence intervals** (not just point estimates)

---

## Revision v0 — Implemented ✅

**Status:** Fully implemented (Tasks 105-106)  
**Database Table:** `revision_queue`  
**Granularity:** Theme-level  
**Endpoint:** `POST /v1/learning/revision/plan`

### Purpose

Generate personalized revision schedules using spaced repetition based on mastery levels. Determines when themes are due for review and how many questions to practice.

### Algorithm Flow

```
1. Load user_theme_mastery records
2. For each theme:
   a. Determine mastery band (weak/medium/strong/mastered)
   b. Compute spacing based on band
   c. Check if due within horizon
   d. Calculate priority score
   e. Assign recommended question count
3. Upsert to revision_queue
```

### Mastery Bands

| Band | Mastery Range | Spacing | Questions (low/high attempts) |
|------|---------------|---------|-------------------------------|
| **Weak** | 0.00 – 0.39 | 1 day | 15 / 20 |
| **Medium** | 0.40 – 0.69 | 2 days | 10 / 15 |
| **Strong** | 0.70 – 0.84 | 5 days | 5 / 10 |
| **Mastered** | 0.85 – 1.00 | 12 days | 5 / 5 |

**Spacing Rule:**
```
next_due = last_attempt_date + spacing_days[band]
```

### Priority Score Formula

```
priority = mastery_inverse + recency + low_data_bonus

Where:
- mastery_inverse = (1 - mastery_score) × 70
- recency = min(days_since_last, 90) × 2
- low_data_bonus = 10 if attempts < min_attempts else 0
```

**Higher score = higher priority**

**Examples:**
- Weak theme (0.3), 30 days ago, 10 attempts:
  - mastery_inverse = 0.7 × 70 = 49.0
  - recency = 30 × 2 = 60.0
  - low_data_bonus = 0
  - **Total priority = 109.0**

- Strong theme (0.8), 2 days ago, 3 attempts:
  - mastery_inverse = 0.2 × 70 = 14.0
  - recency = 2 × 2 = 4.0
  - low_data_bonus = 10
  - **Total priority = 28.0**

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `horizon_days` | int | 7 | How far ahead to schedule |
| `min_attempts` | int | 5 | Threshold for low-data bonus |
| `mastery_bands` | array | See table | Band definitions with max thresholds |
| `spacing_days` | object | See table | Days between revisions per band |
| `question_counts` | object | See table | Recommended counts per band |
| `priority_weights` | object | See formula | Weight components |

### Database Schema

**Table:** `revision_queue`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK to users |
| `year` | int | Academic year |
| `block_id` | int | FK to blocks |
| `theme_id` | int | FK to themes |
| `due_date` | date | When revision is due |
| `priority_score` | numeric(5,2) | Ordering priority |
| `recommended_count` | int | Suggested question count |
| `status` | text | DUE / DONE / SNOOZED / SKIPPED |
| `reason_json` | JSONB | Explainability data |
| `generated_at` | timestamptz | When created |
| `last_seen_at` | timestamptz | Last UI access |
| `algo_version_id` | UUID | FK to algo_versions |
| `params_id` | UUID | FK to algo_params |
| `run_id` | UUID | FK to algo_runs |

**Constraints:**
- UNIQUE on `(user_id, theme_id, due_date)`

**Indexes:**
- `(user_id, due_date, status)` - Fast "due today" queries
- `(user_id, priority_score DESC)` - Priority ordering

### Reason JSON Structure

```json
{
  "band": "weak",
  "mastery_score": 0.35,
  "attempts_total": 8,
  "spacing_days": 1,
  "last_attempt_days_ago": 2,
  "is_due_now": true,
  "priority_breakdown": {
    "mastery_inverse": 45.50,
    "recency": 4.00,
    "low_data_bonus": 0
  }
}
```

### Upsert Behavior

**On Conflict** (same user, theme, due_date):
- **If status = DUE:** Update priority, count, reason
- **If status = DONE/SKIPPED/SNOOZED:** Do NOT update (user action preserved)

**Benefits:**
- Idempotent scheduler runs
- Respects user actions
- Prevents duplicate rows

### API Endpoint

**POST /v1/learning/revision/plan**

**Request:**
```json
{
  "scope": "today",
  "year": 1,
  "block_id": 3
}
```

**Response:**
```json
{
  "generated": 12,
  "due_today": 7,
  "run_id": "uuid"
}
```

**Use Cases:**
- Student: "Show me today's revision topics"
- Student: "What should I practice this week?"
- Nightly job: Regenerate queues for all users

### Example Usage

```python
from app.learning_engine.revision.service import generate_revision_queue_v0

# Generate for a user
result = await generate_revision_queue_v0(
    db,
    user_id=user.id,
    year=1,
    block_id=3,
    trigger="nightly"
)

# Returns:
{
  "generated": 12,
  "due_today": 7,
  "run_id": "uuid"
}
```

### Querying Revision Queue

```python
from app.models.learning_revision import RevisionQueue

# Get today's due items, ordered by priority
today = date.today()
stmt = select(RevisionQueue).where(
    RevisionQueue.user_id == user.id,
    RevisionQueue.due_date == today,
    RevisionQueue.status == "DUE"
).order_by(RevisionQueue.priority_score.desc())

due_items = await db.execute(stmt)

for item in due_items.scalars():
    print(f"Theme {item.theme_id}: {item.recommended_count} questions")
    print(f"  Priority: {item.priority_score}")
    print(f"  Reason: {item.reason_json}")
```

### Behavior Rules

1. **Never Attempted:**
   - `due_date = current_date` (due immediately)
   - `priority_score` includes low_data_bonus

2. **Recently Attempted:**
   - If within spacing window → not due yet
   - Scheduled for future date

3. **Weak Themes Prioritized:**
   - Lower mastery = higher priority
   - Ensures struggling areas get attention

4. **Horizon Limit:**
   - Only schedules within `horizon_days` (default: 7)
   - Prevents infinite future scheduling

5. **Status Protection:**
   - User marks DONE → stays DONE
   - Scheduler doesn't reset to DUE

### Future Enhancements (Out of Scope for v0)

- **FSRS (Free Spaced Repetition Scheduler)** - ML-based spacing
- **User preferences** - Adjust spacing multipliers
- **Difficulty-aware scheduling** - Harder questions = longer spacing
- **Concept-level revision** - When concept graph ready
- **Adaptive horizons** - Extend for long-term planning

---

## Difficulty Calibration v0 — Implemented ✅

**Status:** Fully implemented (Task 107)  
**Database Table:** `question_difficulty`  
**Algorithm:** ELO-lite rating system

### Purpose

Maintain live difficulty ratings for all questions based on student performance. Uses an ELO-inspired algorithm to dynamically adjust question difficulty as more students attempt them.

### ELO-lite Formula

```
expected = 1 / (1 + 10 ^ ((question_rating - student_rating) / rating_scale))
delta = k_factor × (actual - expected)
new_rating = question_rating + delta
```

**Where:**
- `actual` = 1 if correct, 0 if incorrect
- `expected` = predicted probability of correctness
- `k_factor` = adjustment magnitude (default: 16)
- `rating_scale` = logistic scaling constant (default: 400)

### Student Rating Strategies

**1. Fixed Strategy**
- All students assigned `baseline_rating` (default: 1000)
- Simple, consistent, no personalization

**2. Mastery-Mapped Strategy** (default)
- Map student's `mastery_score` (0..1) to rating range
- Default range: 800 (weak) to 1200 (strong)
- Uses `user_theme_mastery` for the question's theme
- Falls back to baseline if mastery unavailable

```python
student_rating = min_rating + (mastery_score × (max_rating - min_rating))
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `baseline_rating` | int | 1000 | Starting rating for new questions |
| `k_factor` | int | 16 | ELO adjustment sensitivity |
| `rating_scale` | int | 400 | Logistic curve scaling |
| `student_rating_strategy` | string | "mastery_mapped" | How to compute student rating |
| `mastery_rating_map` | object | `{min: 800, max: 1200}` | Range for mastery mapping |

### Behavior

**When Updates Occur:**
- Triggered on **session submission** only
- All answered questions in session updated in bulk
- Best-effort: failures do NOT block session submission

**Rating Dynamics:**
- Correct answer by weak student → difficulty increases (question is harder than expected)
- Wrong answer by strong student → difficulty decreases (question is easier than expected)
- Balanced performance → minimal change

**Initial State:**
- New questions start at `baseline_rating` (1000)
- Ratings stabilize after ~20-30 attempts
- Early attempts have larger influence (higher k_factor)

### Database Schema

**Table:** `question_difficulty`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `question_id` | UUID | FK to questions (UNIQUE) |
| `rating` | numeric(8,2) | Current difficulty rating |
| `attempts` | int | Total attempts across all users |
| `correct` | int | Total correct across all users |
| `p_correct` | numeric(5,4) | Cached accuracy (correct/attempts) |
| `last_updated_at` | timestamptz | Most recent update |
| `algo_version_id` | UUID | FK to algo_versions |
| `params_id` | UUID | FK to algo_params |
| `run_id` | UUID | FK to algo_runs |
| `breakdown_json` | JSONB | Explainability data |

**Indexes:**
- `(question_id)` UNIQUE - Fast lookup
- `(rating)` - Range queries
- `(attempts)` - Data quality filtering

### Breakdown JSON Structure

```json
{
  "actual": 1,
  "expected": 0.6347,
  "delta": 5.92,
  "student_rating": 1080.0,
  "theme_id": 15,
  "mastery_score": 0.7500
}
```

**Fields:**
- `actual`: 1 if correct, 0 if incorrect
- `expected`: Predicted probability (0..1)
- `delta`: Rating change applied
- `student_rating`: Student's computed rating
- `theme_id`: Question's theme (if available)
- `mastery_score`: Student's mastery for that theme (if available)

### Example Usage

```python
from app.learning_engine.difficulty.service import update_question_difficulty_v0_for_session

# Called after session submission
result = await update_question_difficulty_v0_for_session(
    db,
    session_id=session.id,
    trigger="submit"
)

# Returns:
{
  "questions_updated": 15,
  "avg_delta": 3.47,
  "run_id": "uuid"
}
```

### Querying Difficulty

```python
from app.models.learning_difficulty import QuestionDifficulty

# Get easiest questions
stmt = select(QuestionDifficulty).where(
    QuestionDifficulty.rating < 950,
    QuestionDifficulty.attempts >= 10,
).order_by(QuestionDifficulty.rating.asc())

easy_questions = await db.execute(stmt)

# Get hardest questions
stmt = select(QuestionDifficulty).where(
    QuestionDifficulty.rating > 1150,
    QuestionDifficulty.attempts >= 10,
).order_by(QuestionDifficulty.rating.desc())

hard_questions = await db.execute(stmt)
```

### Rating Interpretation

| Rating Range | Difficulty | Expected Accuracy (avg student) |
|--------------|------------|--------------------------------|
| < 900 | Very Easy | > 85% |
| 900 – 950 | Easy | 75% – 85% |
| 950 – 1050 | Medium | 55% – 75% |
| 1050 – 1100 | Hard | 40% – 55% |
| > 1100 | Very Hard | < 40% |

### Future Enhancements (Out of Scope for v0)

- **IRT (Item Response Theory)** - Multi-parameter models
- **Time-decay** - Reduce weight of old attempts
- **Adaptive k_factor** - Larger for questions with fewer attempts
- **Question-specific curves** - Custom scaling per question type
- **Confidence intervals** - Rating ± uncertainty

---

## Adaptive Selection v0 — Implemented ✅

**Status:** Fully implemented (Task 108)  
**Algorithm:** Rule-based deterministic selection

### Purpose

Select optimal questions for each student using multi-factor scoring. Balances:
- **Weak theme prioritization** - Focus on struggling areas
- **Difficulty matching** - Questions matched to current mastery level
- **Anti-repeat** - Avoid recently seen questions
- **Diversity** - Mix across themes and difficulty levels

### Selection Algorithm

```
Step 1: Determine target themes
  - Priority 1: Themes due in revision_queue
  - Priority 2: Weakest themes by mastery_score
  - Ensure ≥2 themes for diversity

Step 2: Build candidate pool
  - Status = PUBLISHED
  - Matches year/blocks/themes
  - Exclude questions seen in last N days

Step 3: Compute fit scores
  - mastery_inverse: Prefer weak themes
  - difficulty_distance: Match question rating to target
  - freshness: Prefer not-recently-seen (all equal after filter)

Step 4: Sort by fit score (deterministic tie-breaking)

Step 5: Apply coverage constraints
  - Theme mix (e.g., 50% weak, 30% medium, 20% mixed)
  - Difficulty mix (e.g., 20% easy, 60% medium, 20% hard)
  - Max per theme (even distribution)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `anti_repeat_days` | int | 14 | Exclude questions seen in last N days |
| `theme_mix` | object | See below | Target proportion per mastery band |
| `difficulty_targets` | object | See below | Rating ranges per mastery band |
| `difficulty_bucket_limits` | object | See below | Rating thresholds for easy/medium/hard |
| `difficulty_mix` | object | See below | Target proportion per difficulty bucket |
| `fit_weights` | object | See below | Component weights for fit score |

**Default Theme Mix:**
```json
{
  "weak": 0.5,    // 50% from weak themes
  "medium": 0.3,  // 30% from medium themes
  "mixed": 0.2    // 20% from all themes
}
```

**Default Difficulty Targets (by Mastery Band):**
```json
{
  "weak": [900, 1050],    // Easier questions for weak themes
  "medium": [1000, 1150], // Moderate questions
  "strong": [1050, 1250]  // Harder questions for strong themes
}
```

**Default Difficulty Bucket Limits:**
```json
{
  "easy": [0, 950],
  "medium": [950, 1100],
  "hard": [1100, 9999]
}
```

**Default Difficulty Mix:**
```json
{
  "easy": 0.2,    // 20% easy questions
  "medium": 0.6,  // 60% medium questions
  "hard": 0.2     // 20% hard questions
}
```

**Default Fit Weights:**
```json
{
  "mastery_inverse": 0.6,    // 60% weight to weak themes
  "difficulty_distance": 0.3, // 30% weight to difficulty match
  "freshness": 0.1           // 10% weight to freshness
}
```

### Fit Score Formula

```
fit_score = 
    mastery_inverse_weight × (1 - mastery_score) +
    difficulty_distance_weight × (1 - normalized_distance) +
    freshness_weight × freshness_bonus
```

**Components:**
- **mastery_inverse**: Prioritizes questions from weak themes (lower mastery = higher score)
- **difficulty_distance**: Prioritizes questions near target difficulty for student's level
- **freshness**: Bonus for questions not seen recently (all candidates equal after anti-repeat filter)

**Deterministic Tie-Breaking:**
- Sort by: `(-fit_score, hash(user_id + question_id + today))`
- Same input always produces same output
- No randomness

### Behavior

**Anti-Repeat Logic:**
1. Exclude questions attempted in last `anti_repeat_days`
2. If candidate pool too small → relax filter
3. Prevents staleness while ensuring sufficient pool

**Theme Prioritization:**
1. Revision queue themes (due today/overdue) - highest priority
2. Weakest themes by mastery score
3. Minimum 2 themes for diversity (if available)

**Coverage Constraints:**
- **Soft constraints** - can exceed targets by small margin if needed
- **Theme distribution** - Max per theme = `count / num_themes + 1`
- **Difficulty distribution** - Enforces difficulty_mix proportions (±2 tolerance)

**Fallback Behavior:**
- If constraints conflict → prioritize theme coverage over difficulty
- If still insufficient → relax all constraints
- Ensures at least some questions returned (if any exist)

### Example Usage

```python
from app.learning_engine.adaptive.service import adaptive_select_v0

# Select 20 questions for a user
result = await adaptive_select_v0(
    db,
    user_id=user.id,
    year=1,
    block_ids=[block1_id, block2_id],
    theme_ids=None,  # All themes in blocks
    count=20,
    mode="tutor",
    trigger="practice_builder"
)

# Returns:
{
  "question_ids": [uuid1, uuid2, ...],
  "count": 20,
  "run_id": "uuid"
}
```

### Integration Points

**Practice Builder:**
- Student selects blocks/themes/count
- Backend calls `adaptive_select_v0`
- Returns optimized question list
- Creates session with selected questions

**Revision Mode:**
- Student clicks "Start Revision"
- Backend queries `revision_queue` for due themes
- Calls `adaptive_select_v0` with due themes
- Prioritizes weak areas

**Exam Mode:**
- Traditional random selection (not adaptive)
- Or: use adaptive with balanced difficulty_mix

### Future Enhancements (Out of Scope for v0)

- **Bandit algorithms** - Explore/exploit tradeoff
- **Collaborative filtering** - "Students like you struggled with..."
- **Concept dependencies** - Enforce prerequisite mastery
- **Learning velocity** - Adjust difficulty based on improvement rate
- **User preferences** - Allow students to tune aggressiveness

---

## Mistake Engine v0 — Implemented ✅

**Status:** Fully implemented (Tasks 109-110)  
**Database Table:** `mistake_log`  
**Algorithm:** Rule-based classification with precedence

### Purpose

Classify wrong answers into mistake types to help students understand why they got questions incorrect. Uses telemetry data (time spent, answer changes, blur events) and rule-based logic to categorize mistakes.

### Mistake Types (v0)

Only **wrong answers** are classified. Correct answers are ignored.

| Type | Description | Typical Cause |
|------|-------------|---------------|
| `CHANGED_ANSWER_WRONG` | Changed answer, still got it wrong | Overthinking, second-guessing |
| `TIME_PRESSURE_WRONG` | Answered under time pressure | Rushing, poor time management |
| `FAST_WRONG` | Answered too quickly | Careless reading, impulsive |
| `DISTRACTED_WRONG` | Tab-away/blur during question | Loss of focus, interruption |
| `SLOW_WRONG` | Spent long time, still wrong | Struggling, uncertain |
| `KNOWLEDGE_GAP` | Fallback for other wrong answers | Lack of understanding |

### Classification Rules (Precedence Order)

Rules are applied in strict order. First match wins.

```
1. CHANGED_ANSWER_WRONG
   IF change_count >= 1

2. TIME_PRESSURE_WRONG
   IF remaining_sec_at_answer <= time_pressure_remaining_sec (default: 60s)

3. FAST_WRONG
   IF time_spent_sec <= fast_wrong_sec (default: 20s)

4. DISTRACTED_WRONG
   IF blur_count >= blur_threshold (default: 1)

5. SLOW_WRONG
   IF time_spent_sec >= slow_wrong_sec (default: 90s)

6. KNOWLEDGE_GAP
   Fallback for all other wrong answers
```

**Why precedence matters:**
- A question with `change_count=2` and `time_spent_sec=15` is classified as `CHANGED_ANSWER_WRONG`, not `FAST_WRONG`
- Order reflects the most specific/actionable diagnosis first

### Feature Extraction

Features are extracted from:
- **session_answers:** `is_correct`, `answered_at`
- **session_questions:** `position`, frozen tags (year/block/theme)
- **attempt_events (telemetry):** Time tracking, changes, blur events

**Telemetry Features:**

| Feature | Source Events | Calculation |
|---------|---------------|-------------|
| `time_spent_sec` | `QUESTION_VIEWED` | Time between consecutive views, capped at 600s |
| `change_count` | `ANSWER_CHANGED` | Count of answer change events |
| `blur_count` | `PAUSE_BLUR` (state="blur") | Count of tab-away/window blur events |
| `mark_for_review_used` | `MARK_FOR_REVIEW_TOGGLED` (marked=true) | Whether question was flagged |
| `remaining_sec_at_answer` | Session timing | Time left when answer submitted |

**Telemetry Missing?**
- If telemetry is unavailable or incomplete:
  - `time_spent_sec = null`
  - `change_count = 0`
  - `blur_count = 0`
  - `mark_for_review_used = false`
- Classifier still works, defaulting to `KNOWLEDGE_GAP` for wrong answers

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fast_wrong_sec` | int | 20 | Threshold for fast wrong (seconds) |
| `slow_wrong_sec` | int | 90 | Threshold for slow wrong (seconds) |
| `time_pressure_remaining_sec` | int | 60 | Threshold for time pressure (seconds left) |
| `blur_threshold` | int | 1 | Minimum blur count for distracted |
| `severity_rules` | object | See below | Severity (1-3) per mistake type |

**Default Severity Rules:**
```json
{
  "FAST_WRONG": 1,
  "DISTRACTED_WRONG": 1,
  "CHANGED_ANSWER_WRONG": 2,
  "TIME_PRESSURE_WRONG": 2,
  "SLOW_WRONG": 2,
  "KNOWLEDGE_GAP": 2
}
```

**Severity Scale:**
- **1:** Minor/behavioral - easily correctable
- **2:** Moderate - requires attention
- **3:** Severe - fundamental issue (not used in v0)

### Database Schema

**Table:** `mistake_log`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK to users |
| `session_id` | UUID | FK to test_sessions |
| `question_id` | UUID | FK to questions |
| `position` | int | Order in session |
| `year` | int | Frozen academic year |
| `block_id` | UUID | Frozen block FK |
| `theme_id` | UUID | Frozen theme FK |
| `is_correct` | bool | Always false in v0 |
| `mistake_type` | string | Classification result |
| `severity` | smallint | 1-3 |
| `evidence_json` | JSONB | Explainability data |
| `created_at` | timestamptz | When classified |
| `algo_version_id` | UUID | FK to algo_versions |
| `params_id` | UUID | FK to algo_params |
| `run_id` | UUID | FK to algo_runs |

**Constraints:**
- UNIQUE on `(session_id, question_id)` - one classification per attempt

**Indexes:**
- `(user_id, created_at)` - User's mistake history
- `(session_id)` - Session-level queries
- `(mistake_type)` - Aggregate by type
- `(year)`, `(block_id)`, `(theme_id)` - Analytics filtering

### Evidence JSON Structure

```json
{
  "time_spent_sec": 18.5,
  "change_count": 2,
  "blur_count": 0,
  "remaining_sec_at_answer": 45.2,
  "mark_for_review_used": true,
  "rule_fired": "CHANGED_ANSWER_WRONG",
  "thresholds": {
    "fast_wrong_sec": 20,
    "slow_wrong_sec": 90,
    "time_pressure_remaining_sec": 60,
    "blur_threshold": 1
  }
}
```

**Purpose:**
- **Explainability:** Why this classification was chosen
- **Debugging:** Verify feature extraction and rule logic
- **Auditing:** Reproduce classification with same inputs
- **UI:** Show students specific metrics for their mistakes

### Behavior

**Trigger:**
- Runs automatically on **session submission**
- Best-effort: failures do NOT block submission
- Idempotent: rerunning updates existing records

**Upsert Logic:**
- If `(session_id, question_id)` already exists → UPDATE
- Prevents duplicates on re-runs
- Updates `mistake_type`, `severity`, `evidence_json`, provenance fields

**Performance:**
- Bulk upsert (single query for all mistakes)
- Telemetry extraction parallelizable (future optimization)
- Typical session (50 questions, 15 wrong): ~200ms

### Example Usage

```python
from app.learning_engine.mistakes.service import classify_mistakes_v0_for_session

# Called automatically on session submit, or manually
result = await classify_mistakes_v0_for_session(
    db,
    session_id=session.id,
    trigger="submit"
)

# Returns:
{
    "total_wrong": 15,
    "classified": 15,
    "counts_by_type": {
        "KNOWLEDGE_GAP": 7,
        "FAST_WRONG": 3,
        "CHANGED_ANSWER_WRONG": 2,
        "TIME_PRESSURE_WRONG": 2,
        "SLOW_WRONG": 1
    },
    "run_id": "uuid"
}
```

### Querying Mistakes

```python
from app.models.mistakes import MistakeLog

# Get user's most common mistakes
stmt = select(
    MistakeLog.mistake_type,
    func.count().label('count')
).where(
    MistakeLog.user_id == user.id
).group_by(
    MistakeLog.mistake_type
).order_by(
    func.count().desc()
)

common_mistakes = await db.execute(stmt)

# Get mistakes for a theme
stmt = select(MistakeLog).where(
    MistakeLog.user_id == user.id,
    MistakeLog.theme_id == theme_id,
    MistakeLog.mistake_type != "KNOWLEDGE_GAP"  # Exclude general gaps
).order_by(MistakeLog.created_at.desc())

theme_mistakes = await db.execute(stmt)
```

### Integration Points

**Session Submission:**
- After session marked SUBMITTED
- After difficulty update (Task 107)
- Runs best-effort in try-except block
- Logged but doesn't fail submission

**Future UI (Tasks 111+):**
- Student dashboard: "Your common mistakes"
- Review page: Show mistake type per question
- Analytics: Trend of mistake types over time
- Recommendations: "You often change answers—trust your first instinct"

### Future Enhancements (Out of Scope for v0)

- **Classify correct answers** - "Lucky guess", "Confident correct", "Slow but correct"
- **Composite types** - "Fast AND distracted wrong"
- **ML-based classification** - Supervised learning on labeled data
- **Temporal patterns** - "Mistakes late in exam", "Mistakes after break"
- **Concept-level** - "Knowledge gap in specific concept"
- **Remediation suggestions** - Auto-link to learning resources

---

## Learning Engine API Surface (v0) — Implemented ✅

**Status:** Fully implemented (Tasks 111-115)  
**Base Path:** `/v1/learning`  
**Authentication:** Required (Student/Admin/Reviewer)

### Purpose

Expose all Learning Engine algorithms via stable, secure REST API endpoints. All endpoints follow a standardized response envelope and enforce role-based access control.

### Standard Response Envelope

All Learning Engine endpoints return:

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

**Fields:**
- `ok`: Always true for successful responses (errors use FastAPI standard)
- `run_id`: UUID of the algo_run record (for audit trail)
- `algo`: Algorithm identification (key + version)
- `params_id`: UUID of the active params used
- `summary`: Algorithm-specific output summary

### Authorization Rules

**Students:**
- Can only operate on their own data
- Cannot specify `user_id` for another user
- Can only access their own sessions

**Admins/Reviewers:**
- Can specify any `user_id`
- Can access any session
- Full access to all endpoints

**Session-scoped endpoints:**
- Verify session ownership before execution
- Return 403 if unauthorized

### Idempotency Guarantee

All endpoints are idempotent:
- Calling twice with same inputs produces same result
- No duplicate database records created
- Safe for retries and background jobs

---

### Endpoint 1: POST /v1/learning/mastery/recompute

**Purpose:** Recompute Mastery v0 scores for a user.

**Request:**
```json
{
  "user_id": "uuid | null",
  "year": 1,
  "block_id": "uuid | null",
  "theme_id": "uuid | null",
  "dry_run": false
}
```

**Response Summary:**
```json
{
  "themes_processed": 12,
  "records_upserted": 12,
  "dry_run": false
}
```

**Use Cases:**
- Student recomputes after completing sessions
- Admin triggers recompute for specific user
- Dry-run to preview impact

**Service Called:** `recompute_mastery_v0_for_user()`

---

### Endpoint 2: POST /v1/learning/revision/plan

**Purpose:** Generate revision_queue entries for a user.

**Request:**
```json
{
  "user_id": "uuid | null",
  "year": 1,
  "block_id": "uuid | null"
}
```

**Response Summary:**
```json
{
  "generated": 14,
  "due_today": 6
}
```

**Use Cases:**
- Student generates revision schedule
- Nightly job regenerates for all users
- Admin triggers for specific user

**Service Called:** `generate_revision_queue_v0()`

---

### Endpoint 3: POST /v1/learning/adaptive/next

**Purpose:** Select next best questions using Adaptive v0.

**Request:**
```json
{
  "user_id": "uuid | null",
  "year": 1,
  "block_ids": ["uuid"],
  "theme_ids": ["uuid"] | null,
  "count": 20,
  "mode": "tutor",
  "source": "weakness"
}
```

**Response Summary:**
```json
{
  "count": 20,
  "themes_used": ["uuid1", "uuid2"],
  "difficulty_distribution": {
    "easy": 4,
    "medium": 12,
    "hard": 4
  },
  "question_ids": ["uuid1", "uuid2", "..."]
}
```

**Important:**
- Does NOT create a session (returns question_ids only)
- Deterministic output for same inputs
- Prioritizes weak themes and revision-due themes

**Use Cases:**
- Practice Builder: Get optimal questions
- Revision Mode: Get questions for due themes
- Adaptive Test: Get difficulty-matched questions

**Service Called:** `adaptive_select_v0()`

---

### Endpoint 4: POST /v1/learning/difficulty/update

**Purpose:** Update question difficulty ratings for a session.

**Request:**
```json
{
  "session_id": "uuid"
}
```

**Response Summary:**
```json
{
  "questions_updated": 18,
  "avg_delta": -2.14
}
```

**Important:**
- Idempotent (safe to call multiple times)
- Automatically called on session submission
- Manual call useful for re-rating

**Use Cases:**
- Automatic: Called on every session submission
- Manual: Admin triggers re-rating
- Batch: Re-rate after param tuning

**Service Called:** `update_question_difficulty_v0_for_session()`

---

### Endpoint 5: POST /v1/learning/mistakes/classify

**Purpose:** Classify mistakes for a submitted session.

**Request:**
```json
{
  "session_id": "uuid"
}
```

**Response Summary:**
```json
{
  "total_wrong": 9,
  "classified": 9,
  "counts_by_type": {
    "FAST_WRONG": 3,
    "CHANGED_ANSWER_WRONG": 2,
    "KNOWLEDGE_GAP": 4
  }
}
```

**Important:**
- Idempotent (safe to call multiple times)
- Automatically called on session submission
- Only classifies wrong answers

**Use Cases:**
- Automatic: Called on every session submission
- Manual: Admin triggers re-classification
- Analytics: Query mistake patterns

**Service Called:** `classify_mistakes_v0_for_session()`

---

### Error Handling

**Standard FastAPI Error Format:**
```json
{
  "detail": "Error message"
}
```

**Common Error Codes:**
- `403 Forbidden` - Insufficient permissions or unauthorized access
- `404 Not Found` - Session/resource not found
- `422 Unprocessable Entity` - Invalid request parameters
- `500 Internal Server Error` - Algorithm execution failed

**Best Practices:**
- All algorithm failures are caught and returned as errors
- No internal stack traces exposed to clients
- Detailed error messages for debugging

---

### Integration Examples

**Practice Builder Flow:**
```python
# 1. Get optimal questions
response = POST /v1/learning/adaptive/next
{
  "year": 1,
  "block_ids": [block_id],
  "count": 20,
  "mode": "tutor",
  "source": "weakness"
}

# 2. Create session with returned question_ids
session = POST /v1/sessions
{
  "mode": "TUTOR",
  "count": 20,
  "question_ids": response.summary.question_ids
}
```

**Post-Session Flow (Automatic):**
```python
# On session submission:
# 1. Submit session
POST /v1/sessions/{id}/submit

# 2. Automatically triggered (best-effort):
#    - Difficulty update
#    - Mistake classification

# 3. User can manually trigger:
POST /v1/learning/mastery/recompute
POST /v1/learning/revision/plan
```

**Admin Dashboard Flow:**
```python
# Recompute for specific user
POST /v1/learning/mastery/recompute
{
  "user_id": "target_user_id",
  "year": 1
}

# Generate revision plan
POST /v1/learning/revision/plan
{
  "user_id": "target_user_id",
  "year": 1
}
```

---

### Testing

All endpoints have comprehensive pytest coverage:
- RBAC enforcement (students vs admins)
- Session ownership verification
- Idempotency (no duplicate records)
- run_id always returned
- Dry-run functionality
- Deterministic output

See `backend/tests/test_learning_api.py` for full test suite.

---

### Future Enhancements (Out of Scope for v0)

**v1 API Features:**
- Batch operations (recompute for multiple users)
- Async job queue (long-running computations)
- Webhooks (notify on completion)
- Pagination (large result sets)
- Filtering/sorting (advanced queries)

**v2 Algorithm Features:**
- ML-based algorithms (BKT, collaborative filtering)
- Real-time updates (streaming)
- A/B testing framework
- Custom parameter overrides per request

---

## Compute Endpoints (Legacy - Use v1/learning instead)

Future tasks will add compute endpoints for each algorithm:

- `POST /v1/learning/mastery` - Compute mastery scores
- `POST /v1/learning/revision` - Get revision schedule
- `POST /v1/learning/difficulty/{question_id}` - Assess difficulty
- `POST /v1/learning/adaptive/select` - Select adaptive questions
- `POST /v1/learning/mistakes/{theme_id}` - Identify common mistakes

These are **NOT implemented yet** and will raise `NotImplementedError` if called directly from code.

---

## Module Structure

```
backend/app/learning_engine/
├── __init__.py              # Public API exports
├── constants.py             # Enums (AlgoKey, AlgoStatus, RunStatus, etc.)
├── contracts.py             # Input/Output Pydantic models
├── registry.py              # Version/params resolution helpers
├── runs.py                  # Run logging helpers
├── params.py                # Parameter validation/defaults
├── info.py                  # Assemble info responses
├── mastery/
│   ├── __init__.py
│   └── v0.py                # Stub (raises NotImplementedError)
├── revision/
│   ├── __init__.py
│   └── v0.py                # Stub
├── difficulty/
│   ├── __init__.py
│   └── v0.py                # Stub
├── adaptive/
│   ├── __init__.py
│   └── v0.py                # Stub
└── mistakes/
    ├── __init__.py
    └── v0.py                # Stub
```

**Module Boundary:** All learning algorithm logic MUST live within `learning_engine/`. Other services should not implement algorithm logic directly.

---

## Design Principles

1. **Version Everything**
   - Algorithm code versions
   - Parameter sets
   - Input/output schemas

2. **One Active at a Time**
   - Only one ACTIVE algo_version per algo_key
   - Only one is_active=true params per algo_version
   - Enforced transactionally in code

3. **Audit Everything**
   - Every run is logged
   - Inputs/outputs captured
   - Errors preserved

4. **No Mutations**
   - Never edit an existing algo_version or params row
   - Create new rows, update active flags
   - Historical data preserved

5. **Deterministic**
   - Same version + same params + same data = same result
   - No randomness unless explicitly seeded
   - No side effects in pure compute functions

6. **Explainable**
   - All algorithms must document their logic
   - Parameters have semantic meaning
   - Outputs include reasoning/metadata

---

## Future Work

### Tasks 103-110 (Algorithm Implementations)
- Implement actual compute logic for v0 algorithms
- Add unit tests per algorithm
- Validate parameter constraints
- Document algorithm formulas

### Tasks 111-115 (Compute Endpoints)
- Add POST endpoints for each algorithm
- Integrate with session submission workflow
- Add cron jobs for nightly batch processing
- Performance optimization

### Tasks 116+ (Advanced Features)
- A/B testing framework for parameter tuning
- ML-based algorithms (v1, v2)
- Real-time streaming updates
- Personalized recommendations dashboard

---

## Testing

See `backend/tests/test_learning_engine.py` for comprehensive tests covering:

- Seeded algo_versions exist
- Active version/params resolution
- Run logging (start/success/failure)
- Activating new versions/params deactivates old ones
- Parameter validation

---

## FAQs

**Q: Can I have multiple active versions of the same algorithm?**  
A: No. Only one ACTIVE version per algo_key. This ensures deterministic behavior.

**Q: Can I change parameters without changing the version?**  
A: Yes. Create a new params row, activate it, and the old one is automatically deactivated.

**Q: How do I roll back to a previous version?**  
A: Use the `activate_algo_version()` helper to set a different version as ACTIVE.

**Q: What if I want to test a new algorithm in production?**  
A: Mark it as EXPERIMENTAL. You can manually trigger runs with it, but it won't be used by default.

**Q: How do I know which version was used for a specific session?**  
A: Query `algo_runs` table by `session_id`. The `algo_version_id` and `params_id` are logged.

---

## References

- Database models: `backend/app/models/learning.py`
- Registry helpers: `backend/app/learning_engine/registry.py`
- Run logging: `backend/app/learning_engine/runs.py`
- API endpoint: `backend/app/api/v1/endpoints/learning.py`

---

**END OF ALGORITHMS DOCUMENTATION**
