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
- **Reversible:** Runtime kill switch allows instant fallback v1 ⇄ v0 without student disruption

---

## Algorithm Keys

The system includes six core algorithms:

| Algo Key | Purpose | Status |
|----------|---------|--------|
| `mastery` | Track student understanding levels per block/theme | v0 implemented |
| `revision` | Schedule questions for spaced repetition | v0 implemented |
| `difficulty` | Estimate question difficulty from performance data | v0 implemented |
| `adaptive` | Select optimal questions for learning | v0 implemented |
| `mistakes` | Identify common error patterns | v0 implemented |
| `bkt` | Bayesian Knowledge Tracing for concept-level mastery | v1 implemented |

**Note:** v0 implementations use simple rule-based approaches. BKT v1 uses a production-grade 4-parameter Bayesian model.

---

## Constants and Configuration

### Philosophy

All algorithmic constants in this system follow strict provenance rules:

1. **No Magic Numbers:** Every constant is centralized in `backend/app/learning_engine/config.py`
2. **Source Attribution:** Every constant includes documentation of its origin (research paper, library default, or heuristic reasoning)
3. **Calibration Tracking:** Constants marked as heuristic have explicit calibration plans
4. **Import-time Validation:** Invalid constants fail fast at startup, not during production

### Constants Registry

All constants are defined as `SourcedValue` objects in `config.py`:

```python
from app.learning_engine.config import FSRS_DEFAULT_WEIGHTS, BKT_L0_MIN

# Access value
weights = FSRS_DEFAULT_WEIGHTS.value

# Check provenance
print(FSRS_DEFAULT_WEIGHTS.sources)
# ["FSRS-6 default parameters from py-fsrs library", ...]
```

### Constant Categories

**1. FSRS (Spaced Repetition System)**
- `FSRS_DEFAULT_WEIGHTS`: 19 parameters for FSRS-6 scheduler
- `FSRS_DESIRED_RETENTION`: Target retention rate (0.90)
- `FSRS_RETENTION_MIN/MAX`: Bounds for retention optimization
- `FSRS_TRAINING_MIN_LOGS`: Minimum review logs required for per-user tuning

**Source:** py-fsrs library defaults, FSRS-6 paper (2024)

**2. BKT (Bayesian Knowledge Tracing)**
- `BKT_L0_MIN/MAX`: Prior knowledge bounds
- `BKT_T_MIN/MAX`: Learning rate bounds
- `BKT_S_MIN/MAX`: Slip probability bounds
- `BKT_G_MIN/MAX`: Guess probability bounds
- `BKT_STABILITY_EPSILON`: Numerical stability threshold

**Source:** Baker et al. (2008), pyBKT defaults, empirical literature

**3. Rating Mapper (MCQ → FSRS Rating)**
- `RATING_FAST_ANSWER_MS`: Threshold for "fast" answer (15 seconds)
- `RATING_SLOW_ANSWER_MS`: Threshold for "slow" answer (90 seconds)
- `RATING_MAX_CHANGES_FOR_CONFIDENT`: Max answer changes for "easy" rating

**Source:** Heuristic - marked for calibration (see `docs/calibration-plan.md`)

**4. Telemetry Validation**
- `TELEMETRY_MIN_TIME_MS/MAX_TIME_MS`: Bounds for valid attempt durations
- `TELEMETRY_MAX_CHANGES`: Cap for answer change count

**Source:** Heuristic sanity bounds

**5. Mastery Computation**
- `MASTERY_LOOKBACK_DAYS`: Recency window for mastery calculation
- `MASTERY_MIN_ATTEMPTS`: Minimum attempts before reporting mastery
- `MASTERY_DIFFICULTY_WEIGHTS`: Weights for difficulty buckets

**Source:** Heuristic - marked for calibration

**6. Training Pipelines**
- `TRAINING_BKT_MIN_ATTEMPTS`: Minimum attempts for BKT EM fitting
- `TRAINING_DIFFICULTY_MIN_ATTEMPTS`: Minimum attempts for difficulty calibration

**Source:** pyBKT documentation, heuristic minimum for statistical significance

### Calibration Status

**Authoritative (16/23 constants):**
- FSRS defaults
- BKT constraints (from literature)
- Numerical stability thresholds

**Heuristic - Needs Calibration (7/23 constants):**
- Rating thresholds (FAST_ANSWER_MS, SLOW_ANSWER_MS, MAX_CHANGES_FOR_CONFIDENT)
- Difficulty weights (MASTERY_DIFFICULTY_WEIGHTS)
- Training thresholds (some)

See `docs/calibration-plan.md` for prioritization and timeline.

### Validation

Constants are validated at import time via `_validate_all_constants()`:
- FSRS weights: Must have exactly 19 parameters
- Retention bounds: Must be in (0, 1) and properly ordered
- BKT constraints: S + G < 1 (non-degeneracy), learned > unlearned
- Timing thresholds: FAST < SLOW, all positive

**Tests:** `backend/tests/test_constants_provenance.py` enforces:
- All constants have non-empty source attribution
- Sources explain reasoning (not just "set to X")
- Heuristic constants mention calibration plans

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

---

## Mistake Engine v1 — Implemented ✅

**Status:** Fully implemented (Task 123)  
**Database Tables:** `mistake_model_version`, `mistake_training_run`, `mistake_inference_log`  
**Algorithm:** Supervised classifier (Logistic Regression + LightGBM) with v0 fallback

### Purpose

Upgrade Mistake Engine from rule-based v0 to a supervised classifier that learns from historical mistake patterns. Maintains cold-start safety with v0 fallback and provides defensible, versioned outputs.

### Architecture

**Key Components:**
1. **Feature Extraction** (`features.py`) - Extended features from attempt + telemetry
2. **Weak Labeling** (`weak_labels.py`) - v0 rules → weak labels with confidence
3. **Training Pipeline** (`train.py`) - Offline batch training (logreg + LightGBM + calibration)
4. **Model Registry** (`registry.py`) - Artifact storage and versioning
5. **Inference** (`infer.py`) - Runtime classification with fallback
6. **API** (`api.py`) - FastAPI endpoints

### Cold-Start Safety

**Always keep v0 as fallback:**
- If no ACTIVE model exists → use v0 rule engine
- If model confidence < threshold → fallback to v0
- Per-user personalization only via calibration (no per-user models)

**Global model first:**
- Single global model trained on all users
- Per-user calibration only after user has >= K attempts (K configurable)
- User-specific stats features have safe defaults when history is small

### Feature Set (v1)

**Attempt-level:**
- `response_time_seconds` - Time spent on question
- `response_time_zscore_user` - Z-score vs user median (percentile-based)
- `response_time_zscore_cohort` - Z-score vs cohort median
- `changed_answer_count` - Number of answer changes
- `first_answer_correct` - Whether first answer was correct
- `final_answer_correct` - Final correctness
- `mark_for_review_used` - Whether marked for review
- `pause_blur_count` - Tab-away/blur events
- `time_remaining_at_answer` - Time remaining (if exam mode)

**Question/context:**
- `question_difficulty` - Elo rating or initial difficulty bucket
- `cognitive_level` - Cognitive level tag (if available)
- `block_id`, `theme_id`, `year` - Academic structure

**User context (cold-start safe):**
- `user_rolling_accuracy_last_n` - Rolling accuracy from last N attempts
- `user_rolling_median_time_last_n` - Rolling median time
- `session_pacing_indicator` - User vs cohort pacing

**Important:** All "fast/slow" thresholds are defined via percentiles relative to user + cohort distributions, not fixed seconds.

### Weak Labeling Strategy

**Use v0 rules to assign:**
- `weak_label` (mistake_type)
- `label_confidence` in [0, 1]

**Confidence rules:**
- Deterministic patterns (e.g., "changed answer from correct->wrong") → high confidence (0.9-1.0)
- Ambiguous patterns → lower confidence (0.6-0.8)
- Fallback (KNOWLEDGE_GAP) → medium confidence (0.7)

### Training Pipeline

**CLI Command:**
```bash
python -m app.learning_engine.mistakes_v1.cli train \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --model lgbm \
    --calibration isotonic
```

**Steps:**
1. Build dataset from Postgres (join attempts + telemetry + question metadata)
2. Generate weak labels + confidence weights
3. Train logistic regression baseline + LightGBM primary
4. Calibrate probabilities (sigmoid or isotonic)
5. Compute metrics (macro F1, weighted F1, calibration ECE)
6. Persist artifacts + metadata

### Inference (Runtime)

**Logic:**
1. If no ACTIVE model → use v0 rule engine (RULE_V0)
2. Else compute features and predict
3. If max_prob < CONF_THRESHOLD (default: 0.5) → fallback to v0
4. Save result to `mistake_log` with `source=MODEL_V1` or `RULE_V0`

**Output:**
- `mistake_type` - Predicted type
- `confidence` - Prediction confidence [0, 1]
- `top_features` - Top contributing features (explainability)
- `model_version_id` - Model version used

### Database Schema

**New Tables:**
- `mistake_model_version` - Model artifacts and metadata
- `mistake_training_run` - Training job logs
- `mistake_inference_log` - Runtime inference logs (sampled)

**Updated `mistake_log`:**
- `source` - RULE_V0 or MODEL_V1
- `model_version_id` - FK to mistake_model_version (nullable)
- `confidence` - Prediction confidence (nullable)

### API Endpoints

- **POST `/v1/learning/mistakes/classify`** - Classify an attempt
- **GET `/v1/learning/mistakes/model`** - Get active model metadata
- **POST `/v1/learning/mistakes/model/train`** (Admin) - Trigger training
- **POST `/v1/learning/mistakes/model/activate`** (Admin) - Activate model version
- **GET `/v1/learning/mistakes/debug/{session_id}/{question_id}`** (Admin) - Debug info

### Versioning & Auditing

- Model version stored in `mistake_model_version`
- Training run metadata in `mistake_training_run`
- Feature/label schema versions tracked
- Git commit hash stored
- All classifications logged with `source` and `model_version_id`

### Future Enhancements (Out of Scope for v1)

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

## BKT (Bayesian Knowledge Tracing) v1

### Purpose

BKT v1 provides **concept-level mastery tracking** using a standard 4-parameter Bayesian model. Unlike the theme-level Mastery v0, BKT tracks mastery at the **concept** (skill) level, which is more granular and allows for fine-grained knowledge state estimation.

### Model

BKT uses four parameters per concept:

- **L0** (p_L0): Prior probability that the student has already mastered the concept before any observations
- **T** (p_T): Probability of learning (transition from unmastered to mastered after an opportunity)
- **S** (p_S): Probability of slip (student knows the concept but answers incorrectly)
- **G** (p_G): Probability of guess (student doesn't know the concept but answers correctly)

### Online Update Formula

Given an observation (correct or incorrect answer), BKT updates the mastery probability:

1. **Predict correctness:**
   ```
   P(Correct) = P(L) × (1 - S) + (1 - P(L)) × G
   ```

2. **Compute posterior given observation:**
   ```
   If correct:
     P(L|Correct) = [P(L) × (1 - S)] / P(Correct)
   
   If incorrect:
     P(L|Wrong) = [P(L) × S] / (1 - P(Correct))
   ```

3. **Apply learning transition:**
   ```
   P(L_next) = P(L|obs) + (1 - P(L|obs)) × T
   ```

### Database Schema

#### `bkt_skill_params`

Stores fitted BKT parameters per concept.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `concept_id` | UUID | Concept (skill) identifier |
| `algo_version_id` | UUID | FK to `algo_versions` |
| `p_L0` | float | Prior mastery probability |
| `p_T` | float | Learning rate |
| `p_S` | float | Slip probability |
| `p_G` | float | Guess probability |
| `constraints_applied` | jsonb | Constraints used during fitting |
| `fitted_at` | timestamp | When parameters were fitted |
| `fitted_on_data_from` | timestamp | Training data start date |
| `fitted_on_data_to` | timestamp | Training data end date |
| `metrics` | jsonb | AUC, RMSE, logloss, CV metrics |
| `is_active` | boolean | Whether these params are active for this concept |

**Constraints:**
- Only one active parameter set per concept at a time
- Parameters must satisfy: `0 < L0, T, S, G < 1`, `S + G < 1`, `(1 - S) > G`

#### `bkt_user_skill_state`

Tracks current mastery state per user-concept pair.

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | UUID | Primary key (composite) |
| `concept_id` | UUID | Primary key (composite) |
| `p_mastery` | float | Current mastery probability [0, 1] |
| `n_attempts` | int | Total attempts on this concept |
| `last_attempt_at` | timestamp | Last attempt timestamp |
| `last_seen_question_id` | UUID | Last question ID (for anti-repeat) |
| `algo_version_id` | UUID | Version used for last update |
| `updated_at` | timestamp | Last update timestamp |

#### `mastery_snapshot`

Optional historical snapshots for analytics.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | User identifier |
| `concept_id` | UUID | Concept identifier |
| `p_mastery` | float | Mastery probability at snapshot time |
| `n_attempts` | int | Attempts at snapshot time |
| `algo_version_id` | UUID | Algorithm version |
| `created_at` | timestamp | Snapshot timestamp |

### Training Pipeline

BKT parameters are fitted using **Expectation-Maximization (EM)** via the `pyBKT` library.

#### Training Dataset

- **Source:** `session_answers` from SUBMITTED/EXPIRED sessions
- **Format:** Sequences of correctness (0/1) per user per concept
- **Minimum requirements:**
  - At least 10 total attempts per concept
  - At least 3 unique users per concept

#### Fitting Process

1. Build training dataset from historical attempts
2. Fit parameters using EM algorithm (pyBKT)
3. Apply parameter constraints:
   - L0: [0.001, 0.5]
   - T: [0.001, 0.5]
   - S: [0.001, 0.4]
   - G: [0.001, 0.4]
4. Validate parameters (degeneracy checks)
5. Compute metrics (AUC, RMSE, logloss)
6. Persist to `bkt_skill_params`

#### CLI Usage

```bash
# Fit parameters for a single concept
python -m scripts.fit_bkt --concept-id <uuid>

# Fit with custom date range and activate
python -m scripts.fit_bkt --concept-id <uuid> \
  --from-date 2025-01-01 \
  --to-date 2026-01-01 \
  --activate

# Fit with custom constraints
python -m scripts.fit_bkt --concept-id <uuid> \
  --L0-min 0.01 --L0-max 0.3 \
  --T-min 0.05 --T-max 0.4 \
  --activate
```

### API Endpoints

All endpoints are under `/v1/learning/bkt`.

#### `POST /v1/learning/bkt/recompute`

Recompute BKT parameters from historical data (Admin only).

**Request:**
```json
{
  "from_date": "2025-01-01T00:00:00Z",
  "to_date": "2026-01-01T00:00:00Z",
  "min_attempts": 10,
  "concept_ids": ["<uuid1>", "<uuid2>"],
  "activate_new_params": false
}
```

**Response:**
```json
{
  "ok": true,
  "run_id": "<uuid>",
  "algo": {
    "key": "bkt",
    "version": "v1"
  },
  "params_id": "<uuid>",
  "summary": {
    "concepts_processed": 2,
    "params_fitted": 2,
    "new_algo_version_id": "<uuid>",
    "run_metrics": {},
    "errors": {}
  }
}
```

#### `POST /v1/learning/bkt/update`

Update BKT mastery for a single attempt.

**Request:**
```json
{
  "user_id": "<uuid>",  // Optional, defaults to current user
  "question_id": "<uuid>",
  "concept_id": "<uuid>",
  "correct": true,
  "current_time": "2026-01-21T12:00:00Z",  // Optional
  "snapshot_mastery": false
}
```

**Response:**
```json
{
  "user_id": "<uuid>",
  "concept_id": "<uuid>",
  "p_mastery": 0.75,
  "n_attempts": 5,
  "algo_version_id": "<uuid>",
  "params_id": "<uuid>"
}
```

**RBAC:**
- Students can only update their own mastery
- Admins can update any user's mastery

#### `GET /v1/learning/bkt/mastery`

Get BKT mastery state for a user.

**Query Params:**
- `user_id` (optional): User ID (defaults to current user)
- `concept_id` (optional): Filter by concept

**Response:**
```json
[
  {
    "user_id": "<uuid>",
    "concept_id": "<uuid>",
    "p_mastery": 0.75,
    "n_attempts": 5,
    "last_attempt_at": "2026-01-21T12:00:00Z",
    "last_seen_question_id": "<uuid>",
    "updated_at": "2026-01-21T12:00:00Z"
  }
]
```

**RBAC:**
- Students can only query their own mastery
- Admins can query any user's mastery

### Integration Points

#### Session Submission

BKT mastery is updated automatically when a session is submitted:

1. Session is submitted and scored
2. For each answered question:
   - Extract `concept_id` from `session_questions.snapshot_json`
   - Call `update_bkt_from_attempt()` with correctness
3. Updates are best-effort (do not block submission)

**Note:** Requires `concept_id` to be present in `snapshot_json` for each question.

### Numerical Stability

BKT core math includes guards for numerical stability:

- **Probability clamping:** All probabilities are clamped to [MIN_PROB, MAX_PROB] where MIN_PROB=1e-6, MAX_PROB=1-1e-6
- **Denominator guards:** Denominators in Bayes' rule are clamped to avoid division by zero
- **Output clamping:** Final mastery probabilities are clamped to [0, 1]

### Degeneracy Prevention

BKT parameters are validated to prevent degeneracy:

1. **Parameter range:** All params must be in (0, 1)
2. **Sum constraint:** S + G < 1
3. **Distinguishability:** (1 - S) > G (ensures P(Correct|Learned) > P(Correct|Unlearned))
4. **Learning constraint:** T > ε (ensures learning actually occurs)

### Default Parameters

If no fitted parameters exist for a concept, the system uses defaults:

```python
DEFAULT_BKT_PARAMS = {
    "p_L0": 0.1,  # 10% prior mastery
    "p_T": 0.2,   # 20% learning rate
    "p_S": 0.1,   # 10% slip rate
    "p_G": 0.2    # 20% guess rate
}
```

### Invariants

1. **Mastery in range:** `0 ≤ p_mastery ≤ 1` always
2. **Correct increases mastery:** `update(p_L, correct=True) ≥ update(p_L, correct=False)`
3. **Convergence:** Consistent correct answers → high mastery; consistent wrong answers → low mastery
4. **Reproducibility:** Same params + same sequence → same final mastery

### Testing

Tests cover:

- Core math functions (predict, posterior, transition, update)
- Parameter validation and constraint application
- Training dataset builder
- Property-based invariants (mastery always in [0,1], correct > wrong, convergence)
- API endpoints with RBAC

**Test file:** `backend/tests/test_bkt.py`

### References

- **Models:** `backend/app/models/bkt.py`
- **Core math:** `backend/app/learning_engine/bkt/core.py`
- **Service layer:** `backend/app/learning_engine/bkt/service.py`
- **Training:** `backend/app/learning_engine/bkt/training.py`
- **API:** `backend/app/api/v1/endpoints/bkt.py`
- **CLI:** `backend/scripts/fit_bkt.py`
- **Tests:** `backend/tests/test_bkt.py`

---

## SRS (Spaced Repetition System) v1 — FSRS-based Forgetting Model

### Purpose

SRS v1 provides **production-grade spaced repetition** using the Free Spaced Repetition Scheduler (FSRS) algorithm with per-user tuning. Unlike simple interval-based schedulers, FSRS models the forgetting curve using a 19-parameter model optimized for each user's learning patterns.

### Algorithm: FSRS-6

FSRS (Free Spaced Repetition Scheduler) is a memory model that predicts when you will forget information and schedules reviews accordingly.

**Key Concepts:**
- **Stability (S)**: How long (in days) it takes for retrievability to decay to a target level
- **Difficulty (D)**: Intrinsic difficulty of the concept [0, 10]
- **Retrievability (R)**: Probability of successful recall at any given time [0, 1]
- **Desired Retention**: Target retrievability (default 0.90 = 90%)

**FSRS-6 Parameters:**
- 19 global weights (learned from population data)
- Per-user weights (learned from individual review history)
- Desired retention (configurable per user)

### Cold Start Strategy

**New users:**
- Use global FSRS-6 default weights
- No blocking if personalized weights unavailable
- System tracks review logs in background

**Tuning Threshold:**
- Minimum 300 review logs required for training
- Training uses EM (Expectation-Maximization) via py-fsrs
- Shrinkage toward global weights (prevents overfitting)

**Transition:**
- Seamless switch from global to personalized weights
- No disruption to existing schedules
- All state updates remain consistent

### Rating Mapping from MCQ Attempts

Each MCQ attempt is converted to an FSRS rating (1-4) based on correctness and telemetry:

**Rating Scale:**
1. **Again (1)**: Failed to recall
2. **Hard (2)**: Recalled with difficulty
3. **Good (3)**: Recalled correctly
4. **Easy (4)**: Recalled easily and quickly

**Mapping Rules:**

| Condition | Rating | Explanation |
|-----------|--------|-------------|
| Incorrect | 1 (Again) | Always, regardless of time or changes |
| Correct + marked for review | 2 (Hard) | Student flagged uncertainty |
| Correct + many answer changes (>0) | 2 (Hard) | Multiple changes indicate uncertainty |
| Correct + very slow (>90s) | 2 (Hard) | Taking too long indicates struggle |
| Correct + fast (<15s) + no changes | 4 (Easy) | Quick answer indicates mastery |
| Correct (default) | 3 (Good) | Standard correct answer |

**Telemetry Used:**
- `time_spent_ms`: Time spent on question (milliseconds)
- `change_count`: Number of answer changes
- `marked_for_review`: Whether student flagged for review

**Determinism:**
- Mapping is deterministic (no randomness)
- Same inputs always produce same rating
- Thresholds are configurable

### Database Schema

#### `srs_user_params`

Stores per-user FSRS parameters and training metadata.

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | UUID | Primary key, FK to users |
| `fsrs_version` | string | FSRS version (default "fsrs-6") |
| `weights_json` | jsonb | Personalized 19-parameter weights (nullable) |
| `desired_retention` | float | Target retention probability (default 0.90) |
| `n_review_logs` | int | Total review logs for this user |
| `last_trained_at` | timestamp | Last training timestamp |
| `metrics_json` | jsonb | Training metrics (logloss, brier, ece, etc.) |

#### `srs_concept_state`

Tracks per-user per-concept memory state using FSRS.

| Field | Type | Description |
|-------|------|-------------|
| `user_id`, `concept_id` | UUID | Composite primary key |
| `stability` | float | Memory stability (days) |
| `difficulty` | float | Item difficulty [0, 10] |
| `last_reviewed_at` | timestamp | Last review timestamp |
| `due_at` | timestamp | Next review due date |
| `last_retrievability` | float | Retrievability at last review [0, 1] |

**Indexes:**
- `(user_id, due_at)` for queue queries
- `due_at` for global due queries
- `(user_id, concept_id)` for lookups

#### `srs_review_log`

Append-only log of all review attempts (for training).

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_id`, `concept_id` | UUID | User and concept identifiers |
| `reviewed_at` | timestamp | Review timestamp |
| `rating` | int | FSRS rating 1-4 |
| `correct` | bool | Whether answer was correct |
| `delta_days` | float | Days since last review |
| `time_spent_ms` | int | Time spent (ms, optional) |
| `change_count` | int | Answer changes (optional) |
| `predicted_retrievability` | float | R at review time (optional) |
| `raw_attempt_id`, `session_id` | UUID | Traceability to source data |

**Indexes:**
- `(user_id, reviewed_at)` for training queries
- `(user_id, concept_id, reviewed_at)` for concept history
- `session_id` for session linkage

### State Update Flow

When a student answers an MCQ:

1. **Extract concept IDs** from question (single or multiple)
2. **Load current state** (or create new with cold start)
3. **Compute delta_days** since last review
4. **Extract telemetry** (time_spent, changes, marked_for_review)
5. **Map to FSRS rating** (1-4) using deterministic rules
6. **Compute new state** using FSRS algorithm:
   - Predict retrievability at review time
   - Update stability and difficulty
   - Compute next due_at
7. **Upsert concept_state** (PostgreSQL upsert)
8. **Append review_log** (append-only, for training)
9. **Increment user's n_review_logs** counter

**Integration:**
- Runs after session submission (best-effort)
- Non-blocking (doesn't fail submission)
- Handles missing concept_id gracefully
- Logs warnings, not errors

### API Endpoints

All endpoints are under `/v1/learning/srs`.

#### `GET /v1/learning/srs/queue`

Get concepts due for review.

**Query Params:**
- `scope`: "today" (due now) or "week" (due in next 7 days)
- `limit`: Max concepts (1-500, default 100)

**Response:**
```json
{
  "scope": "today",
  "total_due": 15,
  "items": [
    {
      "concept_id": "<uuid>",
      "due_at": "2026-01-21T10:00:00Z",
      "stability": 3.5,
      "difficulty": 6.2,
      "retrievability": 0.65,
      "priority_score": 0.35,
      "is_overdue": true,
      "days_overdue": 1.5,
      "bucket": "overdue"
    }
  ]
}
```

**Features:**
- Ordered by due_at (overdue first)
- Priority from retrievability (lower R = higher priority)
- Time buckets: overdue, today, tomorrow, day_N, later
- Student scope (own concepts only)

#### `GET /v1/learning/srs/stats`

Get user's SRS statistics.

**Response:**
```json
{
  "total_concepts": 150,
  "due_today": 15,
  "due_this_week": 42,
  "total_reviews": 450,
  "has_personalized_weights": true,
  "last_trained_at": "2026-01-20T12:00:00Z"
}
```

#### `GET /v1/learning/srs/concepts/{concept_id}`

Get SRS state for a specific concept.

**Response:**
```json
{
  "user_id": "<uuid>",
  "concept_id": "<uuid>",
  "stability": 3.5,
  "difficulty": 6.2,
  "last_reviewed_at": "2026-01-20T10:00:00Z",
  "due_at": "2026-01-24T10:00:00Z",
  "last_retrievability": 0.75,
  "updated_at": "2026-01-20T10:00:05Z"
}
```

### Per-User Training Pipeline

**Status:** Planned for Phase 2C (not yet implemented)

**Planned Features:**
- Build training dataset from `srs_review_log`
- Minimum 300 logs threshold
- Train/val split (last 20% for validation)
- Run FSRS Optimizer EM algorithm (py-fsrs)
- Apply shrinkage toward global weights:
  - `alpha = min(0.8, log(n_logs)/log(5000))`
  - `final_weights = alpha * user_weights + (1-alpha) * global_weights`
- Evaluate metrics (logloss, Brier score)
- Reject if worse than baseline
- Persist weights + metrics to `srs_user_params`
- Log training run in `algo_runs`

**Admin Endpoints (Planned):**
- `POST /v1/admin/learning/srs/train-user/{user_id}`
- `POST /v1/admin/learning/srs/train-batch`

### Numerical Stability

All FSRS computations include guards:

1. **Finite checks**: All outputs validated with `isfinite()`
2. **Bounds validation**: Stability > 0, Difficulty ∈ [0,10], R ∈ [0,1]
3. **Fallbacks**: Invalid outputs replaced with safe defaults
4. **Due date enforcement**: Always in future
5. **Telemetry sanitization**: Validate time/changes, cap extremes

### Invariants

1. **Stability positive:** S > 0 always
2. **Difficulty in range:** 0 ≤ D ≤ 10 always
3. **Retrievability in range:** 0 ≤ R ≤ 1 always
4. **Due date in future:** due_at > reviewed_at always
5. **Rating affects stability:** Higher rating → longer stability
6. **Deterministic mapping:** Same inputs → same rating

### Auditability

- Every state change logged in `srs_review_log` (append-only)
- Training runs logged in `algo_runs` (when implemented)
- Reproducible computations (deterministic)
- Full traceability to source sessions

### Integration Points

**Session Submission:**
- Hook in `POST /v1/sessions/{id}/submit`
- Runs after session scored and committed
- Best-effort (non-blocking)
- Extracts concept_id from `snapshot_json`
- Handles multiple concepts per question
- Logs warnings on failure

**Revision Queue Sync:**
- Updates `revision_queue` table (materialized view)
- Maintains compatibility with existing UI
- Placeholder for concept→theme mapping

### Testing

Tests cover:

- **Rating mapper**: Deterministic mapping, all rules, telemetry validation
- **FSRS adapter**: State validity, finite outputs, rating effects, invariants
- **Integration**: Multiple concepts, telemetry features, property tests
- **Invariants**: Stability > 0, D ∈ [0,10], R ∈ [0,1], due_at in future

**Test file:** `backend/tests/test_srs.py`

### References

- **Models:** `backend/app/models/srs.py`
- **Rating mapper:** `backend/app/learning_engine/srs/rating_mapper.py`
- **FSRS adapter:** `backend/app/learning_engine/srs/fsrs_adapter.py`
- **Service layer:** `backend/app/learning_engine/srs/service.py`
- **API:** `backend/app/api/v1/endpoints/srs.py`
- **Schemas:** `backend/app/schemas/srs.py`
- **Tests:** `backend/tests/test_srs.py`
- **Training (planned):** `backend/app/learning_engine/srs/training.py`

### Implementation Status

**✅ Completed (Phase 1 + 2A + 2B):**
- Database schema (3 tables)
- FSRS adapter (state computation, scheduling)
- Rating mapper (MCQ → FSRS rating)
- Service layer (update_from_attempt)
- Queue API (3 endpoints)
- Session integration
- Comprehensive tests

**🚧 Planned (Phase 2C):**
- Per-user training pipeline (EM optimizer)
- Admin training endpoints
- Shrinkage toward global weights
- Training metrics and validation

---

## Adaptive Selection v1 — Constrained Thompson Sampling (Task 122)

### Purpose

Adaptive Selection v1 upgrades the rule-based v0 selector to a **production-grade multi-armed bandit** that:
- Uses **Thompson Sampling** over themes (arms) for explore/exploit balance
- Integrates **BKT mastery** (weakness), **FSRS due concepts** (forgetting prevention), and **Elo difficulty** (desirable difficulty)
- Learns **per-user theme preferences** via Beta posteriors updated from session outcomes
- Enforces **constraints** for curriculum coverage and safety

### Model: Two-Stage Theme-Level Thompson Sampling

**Stage A: Theme Selection (Bandit)**

Arms = themes in user's selected blocks. For each theme, compute:

1. **Base Priority** (deterministic, explainable):
   ```
   base_priority = w_weakness × (1 - mastery)
                 + w_due × due_ratio
                 + w_uncertainty × uncertainty_normalized
                 - w_recency × recency_penalty
   ```

2. **Thompson Sample**:
   - Maintain per-(user, theme) Beta posterior: Beta(a, b)
   - Sample y ~ Beta(a, b) each request
   - Final score: `base_priority × (ε_floor + y)`

3. **Select** top-k themes respecting constraints.

**Stage B: Question Selection (Within Theme)**

For each selected theme, pick questions using:
1. FSRS due concepts first (revision priority)
2. BKT weak concepts next (weakness priority)
3. Elo "challenge band" (prefer p(correct) ∈ [p_low, p_high])
4. Exploration slots for new/uncertain questions

### Database Schema

#### `bandit_user_theme_state`

Tracks per-user per-theme Beta posterior for Thompson Sampling.

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | UUID | Composite PK |
| `theme_id` | int | Composite PK |
| `a` | float | Beta alpha (success count + prior) |
| `b` | float | Beta beta (failure count + prior) |
| `n_sessions` | int | Sessions this theme was selected |
| `last_selected_at` | timestamp | When last selected |
| `last_reward` | float | Reward from most recent session [0,1] |
| `updated_at` | timestamp | Last update time |

**Initialization:** Beta(1, 1) = Uniform prior (no preference).

#### `adaptive_selection_log`

Append-only log of selection requests for audit and debugging.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | User identifier |
| `requested_at` | timestamp | Request time |
| `mode` | string | tutor, exam, revision |
| `source` | string | mixed, revision, weakness |
| `year`, `block_ids`, `theme_ids_filter` | - | Request parameters |
| `count` | int | Requested question count |
| `seed` | string | Deterministic seed for reproducibility |
| `algo_version_id`, `params_id`, `run_id` | UUID | Algo provenance |
| `candidates_json` | jsonb | All candidate themes with computed features |
| `selected_json` | jsonb | Selected themes with quotas |
| `question_ids_json` | jsonb | Final ordered question IDs |
| `stats_json` | jsonb | Stats: due_ratio, avg_p, exclusions |

### Parameters (Constants Registry)

All parameters are sourced from `backend/app/learning_engine/config.py`:

**Theme Selection:**
- `beta_prior_a`, `beta_prior_b`: Initial Beta parameters (default 1.0, 1.0)
- `epsilon_floor`: Minimum exploration factor (default 0.10)
- `min_theme_count`, `max_theme_count`: Theme bounds (default 2, 5)
- `min_per_theme`, `max_per_theme`: Per-theme question bounds (default 3, 20)

**Repeat Exclusion:**
- `exclude_seen_within_days`: Time-based exclusion (default 14 days)
- `exclude_seen_within_sessions`: Session-based exclusion (default 3 sessions)

**Revision Mode:**
- `revision_due_ratio_min`: Minimum fraction from due concepts (default 0.60)

**Elo Challenge Band:**
- `p_low`, `p_high`: Target p(correct) range (default 0.55, 0.80)
- `explore_new_question_rate`: Exploration for unrated questions (default 0.10)

**Feature Weights:**
- `w_weakness`: Weight on (1 - mastery) (default 0.45)
- `w_due`: Weight on due concepts (default 0.35)
- `w_uncertainty`: Weight on Elo uncertainty (default 0.10)
- `w_recency_penalty`: Penalty for recent practice (default 0.10)

### Reward Computation

After session completion, update Beta posteriors:

1. **Compute reward** from BKT mastery delta:
   ```
   reward = clamp((post_mastery - pre_mastery) / (1 - pre_mastery), 0, 1)
   ```

2. **Update posterior**:
   ```
   a_new = a + reward
   b_new = b + (1 - reward)
   ```

3. Only update for themes with >= `reward_min_attempts_per_theme` questions in session.

**Why BKT delta?** Rewards actual learning (mastery improvement), not just correctness. This makes the bandit optimize for learning yield, not "easy wins."

### Determinism

Selection is **deterministic** for identical inputs:
- Seed = hash(user_id, mode, count, block_ids, theme_ids, date_bucket)
- Same seed produces same RNG sequence
- Same RNG produces same Thompson samples
- Same samples produce same theme selection and question ordering

### Constraints (Safety)

Hard constraints (always enforced):
1. No duplicate questions in session
2. Questions must be PUBLISHED
3. Respect block/theme filters
4. Respect min/max theme count and per-theme quotas

Soft constraints (enforced with fallback):
1. Exclude recent questions (relax if supply low)
2. Revision due ratio (relax if not enough due concepts)
3. Challenge band (widen if insufficient candidates)

### API Response (v1)

```json
{
  "ok": true,
  "run_id": "uuid",
  "algo": {
    "key": "adaptive_selection",
    "version": "v1"
  },
  "params_id": "uuid",
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
```

### Integration Points

**Practice Builder:**
1. Student selects blocks/themes/count/mode
2. Backend calls `select_questions_v1()`
3. Returns ordered question_ids + plan
4. Create session with these questions

**Session Submit (Reward Update):**
1. Session submitted and scored
2. Compute BKT mastery delta per theme
3. Call `update_bandit_rewards_on_session_submit()`
4. Beta posteriors updated for future selections

### Testing

Tests in `backend/tests/test_adaptive_v1.py`:
- **Determinism**: Same inputs → same outputs
- **Constraints**: min/max themes, quotas, supply
- **Thompson Sampling**: Beta bounds, mean convergence
- **Reward**: BKT delta normalization, posterior updates
- **Question Picker**: Challenge band, interleaving

### Module Structure

```
backend/app/learning_engine/adaptive_v1/
├── __init__.py          # Public API
├── core.py              # Thompson Sampling, priority computation
├── repo.py              # Database queries
├── question_picker.py   # Within-theme question selection
├── reward.py            # Bandit reward computation
└── service.py           # Main orchestration
```

### Migration from v0

- v0 remains available as fallback if v1 not configured
- API endpoint supports both (auto-detects based on algo_version)
- No breaking changes to request format
- Response format extended with `plan` object

### Future Enhancements

- **Contextual bandit**: Include user features in arm selection
- **Concept-level arms**: When concept graph is mature
- **Online parameter tuning**: Bayesian optimization of weights
- **Multi-objective optimization**: Balance learning, engagement, coverage

---

## IRT (Item Response Theory) — Shadow/Offline (Task 125)

### Purpose

IRT calibration provides 2PL and 3PL item and ability estimates for offline analysis, admin visibility, and evaluation harness integration. **IRT is completely shadow/offline by default** and **never used for student-facing decisions** unless `FEATURE_IRT_ACTIVE` is enabled. BKT, FSRS, ELO, and Adaptive remain the source of truth for selection and scoring.

### Feature Flags

- **`FEATURE_IRT_SHADOW`** (default `true`): Allows offline calibration and admin visibility (runs, metrics, flagged items).
- **`FEATURE_IRT_ACTIVE`** (default `false`): When `false`, no student endpoints use IRT; no selection or scoring uses IRT.
- **`FEATURE_IRT_MODEL`** (default `"IRT_2PL"`): Model type to use when active. Must be `"IRT_2PL"` or `"IRT_3PL"`.
- **`FEATURE_IRT_SCOPE`** (default `"none"`): Activation scope. Ignored unless `FEATURE_IRT_ACTIVE=true`. Allowed values:
  - `"none"` (default): IRT not used
  - `"shadow_only"`: Equivalent to `FEATURE_IRT_ACTIVE=false`
  - `"selection_only"`: IRT used for question selection only
  - `"scoring_only"`: IRT used for scoring only
  - `"selection_and_scoring"`: IRT used for both selection and scoring

### Models

- **2PL**: \( P(\text{correct}) = \sigma(a(\theta - b)) \). Discrimination \(a > 0\) (softplus); difficulty \(b\); ability \(\theta\).
- **3PL**: \( P = c + (1 - c)\,\sigma(a(\theta - b)) \). Guessing \(c \in [0, 1/K]\) where \(K\) = option count (MCQ guessing floor).

**Constraints**: \(a > 0\); \(c \in [0, 1/K]\); \(\theta\) standardized post-fit (e.g. \(\theta \sim N(0,1)\)).

### What Is Stored

- **`irt_calibration_run`**: Run metadata, `dataset_spec`, status, seed, metrics (logloss, Brier, ECE, stability, info curve), `artifact_paths`, link to `eval_run_id`.
- **`irt_item_params`**: Per run/question: \(a\), \(b\), \(c\) (nullable for 2PL), SEs, `flags` (e.g. `low_discrimination`, `unstable`, `poor_fit`).
- **`irt_user_ability`**: Per run/user: \(\theta\), \(\theta_\text{se}\).
- **`irt_item_fit`** (optional): Per run/question: loglik, infit/outfit, `info_curve_summary`.

### Estimation

- **Staged**: (1) Joint MAP over \(\theta\) and item params with priors; (2) optional MML/EM scaffold (toggleable).
- **Priors**: \(\theta \sim N(0,1)\); \(a\) centered near 1 (e.g. log-normal); \(b \sim N(0,1)\); \(c\) implied by \(1/K\).
- **Cold start**: \(b\) from ELO difficulty when available; else from empirical p-value (logit); \(a\) from config prior; \(c\) near \(1/K\) for 3PL.
- **Determinism**: Fixed seed per run; `dataset_spec` stored; same seed + same spec → same metrics/params within tolerance.

### Evaluation Harness Integration

- Each calibration run produces an **eval run** (suite `irt_2pl` or `irt_3pl`) with **logloss**, **Brier**, **ECE** (and optional IRT-specific metrics). Artifacts (e.g. calibration curve, summary JSON) stored under `backend/artifacts/irt/<run_id>/`.

### Admin API

- **POST** `/v1/admin/irt/runs`: Create and run calibration (admin only).
- **GET** `/v1/admin/irt/runs`: List runs (filters: `model_type`, `status`).
- **GET** `/v1/admin/irt/runs/{id}`: Run details + metrics.
- **GET** `/v1/admin/irt/runs/{id}/items?flag=low_discrimination`: Item params, optionally filtered by flag.
- **GET** `/v1/admin/irt/runs/{id}/items/{question_id}`: Single item params.
- **GET** `/v1/admin/irt/runs/{id}/users/{user_id}`: User \(\theta\) and SE.

All IRT admin routes require **ADMIN** role and **`FEATURE_IRT_SHADOW`** enabled.

### IRT Activation Policy

IRT activation is controlled by a **strict "No-Vibes" activation policy** that requires objective, measurable criteria before IRT can be used for student-facing decisions.

#### Activation Gates (Policy v1)

All gates must pass for activation eligibility:

1. **Gate A: Minimum Data Sufficiency**
   - Requires: n_users_train >= 500, n_items_train >= 1000, n_attempts_train >= 100,000
   - Requires: median_attempts_per_item >= 50, median_attempts_per_user >= 100
   - Cold-start blocker to ensure sufficient data for reliable calibration

2. **Gate B: Holdout Predictive Superiority vs Baseline**
   - IRT must improve vs baseline (ELO+BKT+FSRS) on same holdout split:
     - logloss_irt <= logloss_baseline - 0.005
     - brier_irt <= brier_baseline - 0.003
     - ece_irt <= ece_baseline - 0.005
   - Improvement must hold in >= 3 evaluation replays/folds

3. **Gate C: Calibration Sanity**
   - No extreme parameter pathologies:
     - <= 15% items with low discrimination (a < 0.25)
     - <= 5% items with difficulty out of range (|b| > 4.0)
     - For 3PL: <= 10% items with c near cap (> 0.95*(1/K))

4. **Gate D: Parameter Stability Over Time**
   - Compare current run to previous eligible run:
     - Spearman corr(b) >= 0.90
     - Spearman corr(a) >= 0.80
     - For 3PL: Spearman corr(c) >= 0.70
     - median |delta_b| <= 0.15

5. **Gate E: Measurement Precision**
   - Ability SE distribution:
     - median(theta_se) <= 0.35
     - >= 60% users with theta_se <= 0.30

6. **Gate F: Coverage + Fairness Sanity**
   - No subgroup (year/block) has catastrophic degradation:
     - logloss_subgroup <= logloss_overall + 0.02

#### Activation Process

1. **Evaluate**: Admin runs evaluation on a SUCCEEDED calibration run
   - `POST /v1/admin/irt/activation/evaluate` with `run_id` and `policy_version`
   - Returns gate results and eligibility status
   - Decision stored in `irt_activation_decision` table

2. **Activate** (if eligible):
   - `POST /v1/admin/irt/activation/activate` with `run_id`, `scope`, `model_type`, `reason`
   - Requires latest decision `eligible=true`
   - Updates `platform_settings` with IRT flags
   - Creates audit event in `irt_activation_event`

3. **Deactivate** (kill-switch):
   - `POST /v1/admin/irt/activation/deactivate` with `reason`
   - Always allowed for ADMIN
   - Instantly sets `FEATURE_IRT_ACTIVE=false` and `FEATURE_IRT_SCOPE="none"`
   - Creates audit event

#### Progressive Rollout

- Initial activation recommended as `"selection_only"` for 2 weeks
- `"selection_and_scoring"` only allowed if:
  - Gate B improvements hold for 2 consecutive weekly runs
  - Gate D stability holds in both runs

#### Runtime Helpers

- `is_irt_active(db)`: Check if IRT is active (reads from platform_settings, fallback to config)
- `get_irt_scope(db)`: Get activation scope
- `get_irt_model(db)`: Get IRT model type
- `is_irt_shadow_enabled(db)`: Check if shadow mode enabled

### IRT Runtime Integration

IRT is integrated with the algorithm runtime framework as module `"irt"`:

**Runtime Helpers** (in `app.learning_engine.runtime`):
- `is_irt_shadow_enabled(db)`: Check if shadow mode is enabled (allows calibration runs)
- `is_irt_active_allowed(db, runtime_cfg)`: Check if IRT can be used for student decisions
  - Requires: Module override not "v0", `FEATURE_IRT_ACTIVE=true`, and not frozen
- `get_effective_irt_state(db)`: Get complete IRT state (shadow, active, frozen, override)

**Module Override Values:**
- `"v0"`: Never use IRT (even if active flag is on)
- `"v1"`: Eligible to be used (only if `FEATURE_IRT_ACTIVE=true`)
- `"shadow"`: Runs allowed (if not frozen), but NO usage in decisions

**Freeze Mode:**
- When `freeze_updates=true`, IRT calibration runs are blocked
- Runs set to FAILED status with error message
- No state mutations when frozen

**Session Snapshot:**
- Future IRT usage must respect session snapshot (`algo_profile_at_start`, `algo_overrides_at_start`)
- `maybe_get_irt_estimates_for_session()` function enforces this contract
- Returns `None` unless IRT is active-allowed

All helpers read from `platform_settings` first (for runtime changes), then fallback to `config.py`.

#### Audit Trail

All activation events are logged immutably in `irt_activation_event`:
- `EVALUATED`: Gate evaluation performed
- `ACTIVATED`: IRT activated for student-facing decisions
- `DEACTIVATED`: IRT deactivated (kill-switch)
- `ROLLED_BACK`: Previous activation rolled back

Each event includes:
- Previous and new state (flags and scope)
- Run ID (if applicable)
- Policy version
- Reason
- Created by user ID
- Timestamp

### Why Shadow?

- IRT is used only for **offline calibration**, **admin dashboards**, and **evaluation**. Student-facing selection, scoring, and difficulty updates use **BKT/FSRS/ELO/Adaptive** exclusively unless `FEATURE_IRT_ACTIVE` is explicitly enabled and all activation gates pass.

---

## Rank Prediction v1 — Shadow/Offline (Task 126)

### Purpose

Rank prediction provides **quantile-based percentile estimates** for students within their cohort (e.g., year). This enables analytics dashboards showing "You are in the top X% of your cohort" without affecting learning decisions. **Rank is completely shadow/offline by default** and **never used for student-facing decisions** unless explicitly activated via runtime override and feature flags.

### Feature Flags

- **`FEATURE_RANK_SHADOW`** (default `true`): Allows offline computation and admin visibility (snapshots, runs, metrics).
- **`FEATURE_RANK_ACTIVE`** (default `false`): When `false`, no student endpoints use rank; no selection or scoring uses rank.
- **Student-facing flag** (default `false`): Even if `FEATURE_RANK_ACTIVE=true`, student endpoints require an additional `rank.student_enabled` flag in `platform_settings`.

### Model: Empirical CDF over theta_proxy

Rank v1 uses a **quantile-based approach**:

1. **Compute theta_proxy** (ability proxy) for each user:
   - Priority 1: Elo user rating (if available)
   - Priority 2: Mastery-weighted score (weighted average of `mastery_score` across themes, weights = `attempts_total`)
   - Priority 3: Zero (with `insufficient_data` status)

2. **Build cohort CDF**:
   - Gather all users in cohort (e.g., "year:1")
   - Compute theta_proxy for each user
   - Sort thetas and build empirical CDF: `percentile = fraction of cohort thetas <= user theta`

3. **Uncertainty bands**:
   - Analytic approximation: `band_half_width = sqrt(p*(1-p)/N) * Z`
   - Where `Z` from config (default 1.28 for ~80% confidence)
   - `band_low = clip(percentile - half_width, 0, 1)`
   - `band_high = clip(percentile + half_width, 0, 1)`

### What Is Stored

- **`rank_prediction_snapshot`**: Daily snapshots per user/cohort:
  - `theta_proxy`: Ability proxy used
  - `predicted_percentile`: Percentile (0..1)
  - `band_low`, `band_high`: Uncertainty band
  - `status`: `ok`, `insufficient_data`, `unstable`, `blocked_frozen`, `disabled`
  - `model_version`: `"rank_v1_empirical_cdf"`
  - `features_hash`: Hash of features for reproducibility
  - Unique constraint: `(user_id, cohort_key, model_version, DATE(computed_at))`

- **`rank_model_run`**: Shadow evaluation run registry:
  - `cohort_key`: Cohort identifier (e.g., "year:1")
  - `dataset_spec`: Time window, filters
  - `metrics`: Coverage, stability, rank correlation
  - `status`: `QUEUED`, `RUNNING`, `DONE`, `FAILED`, `BLOCKED_FROZEN`, `DISABLED`

- **`rank_activation_event`**: Immutable audit log of activation events

- **`rank_config`**: Policy settings (MIN_COHORT_N, THETA_PROXY_PRIORITY, WINDOW_DAYS, etc.)

### Cohort Key Generation

- **Default**: `"year:{year_id}"` from user's academic profile
- **Optional**: `"year:{year_id}:block:{block_code}"` for block-specific cohorts
- **Fallback**: `"year:0"` if user has no academic profile

### Execution Modes

1. **Daily snapshots** (nightly job or on-demand):
   - For each active user, compute snapshot for their cohort
   - Must respect `freeze_updates`: if frozen, write status `"blocked_frozen"` and skip computation

2. **Offline evaluation** (admin-triggered):
   - Backtest using time-sliced cohorts
   - Metrics: coverage, stability (median abs percentile change week-to-week), rank correlation
   - Stored in `rank_model_run.metrics`

### Admin API

- **GET** `/v1/admin/rank/status?cohort_key=...`: Latest run summary + coverage + stability
- **POST** `/v1/admin/rank/runs`: Create and execute rank model run (admin only, shadow mode)
- **GET** `/v1/admin/rank/runs`: List runs (filters: `cohort_key`, `status`)
- **GET** `/v1/admin/rank/runs/{id}`: Run details + metrics
- **GET** `/v1/admin/rank/snapshots?user_id=...&cohort_key=...&days=30`: List snapshots
- **POST** `/v1/admin/rank/activate`: Activate rank for student-facing operations (requires eligibility gates)
- **POST** `/v1/admin/rank/deactivate`: Deactivate rank (kill-switch)

All rank admin routes require **ADMIN** role and rank mode not `"v0"`.

### Rank Activation Policy

Rank activation is controlled by **objective eligibility gates**:

#### Activation Gates

All gates must pass for activation eligibility:

1. **Gate A: Minimum Cohort Size**
   - Requires: `MIN_COHORT_N` users with `ok` status (default: 50)
   - Activation threshold: `ACTIVATION_MIN_COHORT_N` (default: 100)

2. **Gate B: Coverage**
   - Requires: `coverage >= COVERAGE_THRESHOLD` (default: 0.80)
   - Coverage = fraction of users with `ok` status

3. **Gate C: Stability**
   - Requires: `median_abs_percentile_change <= STABILITY_THRESHOLD_ABS_CHANGE` (default: 0.05)
   - Computed from week-to-week percentile changes

#### Activation Process

1. **Evaluate**: Admin checks eligibility for a cohort
   - `is_rank_eligible_for_activation(db, cohort_key)` returns `(eligible, reasons)`

2. **Activate** (if eligible):
   - `POST /v1/admin/rank/activate` with `cohort_key`, `reason`, `confirmation_phrase="ACTIVATE RANK"`
   - Requires eligibility gates passed (unless `force=true`)
   - Updates runtime config override `"rank": "v1"`
   - Creates audit event in `rank_activation_event`

3. **Deactivate** (kill-switch):
   - `POST /v1/admin/rank/deactivate` with `reason`, `confirmation_phrase="DEACTIVATE RANK"`
   - Always allowed for ADMIN
   - Instantly sets runtime override `"rank": "v0"`
   - Creates audit event

### Rank Runtime Integration

Rank is integrated with the algorithm runtime framework as module `"rank"`:

**Runtime Helpers** (in `app.learning_engine.runtime`):
- `get_rank_mode(db, runtime_cfg, snapshot_cfg)`: Get rank mode (`"v0"`, `"shadow"`, `"v1"`)
  - Respects session snapshot if provided
- `is_rank_enabled_for_admin(db, runtime_cfg)`: Check if rank enabled for admin operations
  - Returns `True` if mode is `"shadow"` or `"v1"`
- `is_rank_enabled_for_student(db, runtime_cfg, snapshot_cfg)`: Check if rank enabled for student operations
  - Returns `True` only if mode is `"v1"` AND `rank.student_enabled` flag is `true`

**Module Override Values:**
- `"v0"`: Disabled (no runs, no reads)
- `"shadow"`: Can compute/store snapshots + evaluation, but not used in any student-facing logic
- `"v1"`: Allowed to be used in analytics surfaces (still must not affect learning decisions unless separately approved)

**Freeze Mode:**
- When `freeze_updates=true`, rank snapshot computation is blocked
- Snapshots set to `"blocked_frozen"` status
- No state mutations when frozen

**Session Snapshot:**
- Future rank usage must respect session snapshot (`algo_profile_at_start`, `algo_overrides_at_start`)
- All rank reads use snapshot config

### Why Shadow?

- Rank is used only for **offline analytics**, **admin dashboards**, and **evaluation**. Student-facing selection, scoring, and difficulty updates **never use rank** unless explicitly activated and all gates pass.
- Even when activated, rank is intended for **analytics surfaces only**, not learning decisions.

---

## Graph-Aware Revision Planning v1 — Shadow/Offline (Task 127)

### Purpose

Graph-aware revision planning re-ranks and augments FSRS revision plans using prerequisite graph knowledge. It injects prerequisite themes that students should review before tackling due themes, improving learning efficiency. **Graph revision is completely shadow/offline by default** and **never affects student queues** unless explicitly activated via runtime override and feature flags.

### Feature Flags

- **`FEATURE_GRAPH_REVISION_SHADOW`** (default `true`): Allows offline computation and admin visibility (shadow plans, metrics).
- **`FEATURE_GRAPH_REVISION_ACTIVE`** (default `false`): When `false`, no student endpoints use graph revision; revision queues remain baseline FSRS only.
- **Student-facing flag** (default `false`): Even if `FEATURE_GRAPH_REVISION_ACTIVE=true`, student endpoints require an additional `graph_revision.active` flag in `platform_settings`.

### Model: Prerequisite-Aware Re-ranking

Graph revision v1 uses a **prerequisite injection approach**:

1. **Start with baseline**: Take FSRS due themes (canonical `due_at` from `user_revision_state`).

2. **Fetch prerequisites**: For each due theme, query Neo4j graph for prerequisite themes up to depth D (default 2).

3. **Score prerequisites**: For each prerequisite candidate:
   - `score = w1*(1 - mastery(p)) + w2*(is_overdue(p)) + w3*(recency_need(p))`
   - Where weights are configurable (default: mastery_inverse=0.5, is_overdue=0.3, recency_need=0.2)

4. **Select top prerequisites**: 
   - Respect injection cap (default: ≤25% of baseline count)
   - Max prereqs per theme (default: 2)
   - Avoid duplicates

5. **Produce ordered plan**:
   - Keep baseline due themes order stable
   - Insert prerequisites as "assist items" with explainability labels

**Explainability**: Each injected prerequisite stores reason codes and contributing signals (mastery score, overdue status, source themes).

### What Is Stored

- **`shadow_revision_plan`**: Daily shadow plans per user:
  - `baseline_count`: Number of baseline due themes
  - `injected_count`: Number of prerequisite themes injected
  - `plan_json`: Ordered list of plan items with `{theme_id, kind: "due"|"prereq", reason_codes, score, ...}`
  - `mode`: `"baseline"` (Neo4j unavailable) or `"shadow"` (graph-augmented)
  - Unique constraint: `(user_id, run_date)`

- **`prereq_edges`**: Authoritative prerequisite edges in Postgres (synced to Neo4j):
  - `from_theme_id`: Prerequisite theme
  - `to_theme_id`: Theme that requires the prerequisite
  - `weight`: Edge weight (default 1.0)
  - `source`: `"manual"`, `"imported"`, or `"inferred"`
  - `is_active`: Soft delete flag

- **`prereq_sync_run`**: Neo4j sync job tracking (node/edge counts, errors)

- **`graph_revision_run`**: Shadow evaluation run registry:
  - `metrics`: Coverage, injection rate, Neo4j availability, cycle count
  - `status`: `QUEUED`, `RUNNING`, `DONE`, `FAILED`, `BLOCKED_FROZEN`, `DISABLED`

- **`graph_revision_activation_event`**: Immutable audit log of activation events

- **`graph_revision_config`**: Policy settings (prereq_depth, injection_cap_ratio, scoring_weights, coverage_threshold, etc.)

### Neo4j Integration

- **Authoritative source**: Postgres `prereq_edges` table (single source of truth)
- **Neo4j projection**: Synced via idempotent sync job (upserts nodes/edges, removes inactive)
- **Schema**: 
  - Nodes: `(:Theme {theme_id: string})`
  - Edges: `(:Theme)-[:PREREQ_OF {weight: float}]->(:Theme)`
- **Health checks**: Ping Neo4j, node/edge counts, cycle detection
- **Graceful degradation**: If Neo4j unavailable, planner returns baseline-only plan (mode="baseline")

### Execution Modes

1. **Shadow computation** (nightly job or on-demand):
   - When `graph_revision` mode is `"shadow"`:
     - Compute `shadow_revision_plan` for active users
     - Store metrics in `graph_revision_run`
   - Must respect `freeze_updates`: if frozen, do not write plans; mark run `BLOCKED_FROZEN`

2. **When activated** (`graph_revision=v1` + feature flag `true`):
   - Revision queue builder may call planner to augment ordering
   - **MUST obey session snapshot** for any plan used in a session
   - **IMPORTANT**: Even when active, does not mutate FSRS state; only re-orders/selects items for today's plan

### Admin API

- **POST** `/v1/admin/graph-revision/sync`: Trigger Neo4j sync from Postgres
- **GET** `/v1/admin/graph-revision/sync/runs`: List sync runs
- **GET** `/v1/admin/graph-revision/sync/runs/{id}`: Get sync run details
- **GET** `/v1/admin/graph-revision/health`: Neo4j health + graph stats + cycle check
- **GET** `/v1/admin/graph-revision/edges`: List prerequisite edges
- **POST** `/v1/admin/graph-revision/edges`: Create edge
- **PUT** `/v1/admin/graph-revision/edges/{id}`: Update edge
- **DELETE** `/v1/admin/graph-revision/edges/{id}`: Soft delete edge (is_active=false)
- **GET** `/v1/admin/graph-revision/shadow-plans?user_id=...&days=7`: List shadow plans
- **POST** `/v1/admin/graph-revision/activate`: Activate graph revision (requires eligibility gates)
- **POST** `/v1/admin/graph-revision/deactivate`: Deactivate graph revision (kill-switch)

All graph revision admin routes require **ADMIN** role and graph_revision mode not `"v0"`.

### Graph Revision Activation Policy

Graph revision activation is controlled by **objective eligibility gates**:

#### Activation Gates

All gates must pass for activation eligibility:

1. **Gate A: Cycle Check**
   - Requires: No cycles detected in prerequisite graph (or cycles handled with explicit policy)
   - Default: `cycle_check_enabled=true` (prefer fail if cycles)

2. **Gate B: Coverage**
   - Requires: `coverage >= COVERAGE_THRESHOLD` (default: 0.50)
   - Coverage = fraction of active themes with at least one prerequisite edge

3. **Gate C: Neo4j Availability**
   - Requires: Neo4j currently available (can be enhanced with historical success rate tracking)
   - Default threshold: `neo4j_availability_threshold=0.95` (95% success rate)

#### Activation Process

1. **Evaluate**: Admin checks eligibility
   - `is_graph_revision_eligible_for_activation(db)` returns `(eligible, reasons)`

2. **Activate** (if eligible):
   - `POST /v1/admin/graph-revision/activate` with `reason`, `confirmation_phrase="ACTIVATE GRAPH REVISION"`
   - Requires eligibility gates passed (unless `force=true`)
   - Updates runtime config override `"graph_revision": "v1"`
   - Creates audit event in `graph_revision_activation_event`

3. **Deactivate** (kill-switch):
   - `POST /v1/admin/graph-revision/deactivate` with `reason`, `confirmation_phrase="DEACTIVATE GRAPH REVISION"`
   - Always allowed for ADMIN
   - Instantly sets runtime override `"graph_revision": "v0"`
   - Creates audit event

### Graph Revision Runtime Integration

Graph revision is integrated with the algorithm runtime framework as module `"graph_revision"`:

**Runtime Helpers** (in `app.learning_engine.runtime`):
- `get_graph_revision_mode(db, runtime_cfg, snapshot_cfg)`: Get graph_revision mode (`"v0"`, `"shadow"`, `"v1"`)
  - Respects session snapshot if provided
- `is_graph_revision_active_allowed(db, runtime_cfg, snapshot_cfg)`: Check if graph_revision enabled for student operations
  - Returns `True` only if mode is `"v1"` AND `graph_revision.active` flag is `true` AND not frozen

**Module Override Values:**
- `"v0"`: Disabled (baseline FSRS only)
- `"shadow"`: Can compute/store shadow plans + evaluation, but not used in any student-facing logic
- `"v1"`: Allowed to influence ordering/augmentation of revision plans (still session snapshot rule)

**Freeze Mode:**
- When `freeze_updates=true`, shadow plan computation is blocked
- Plans return `None` (not stored)
- No state mutations when frozen

**Session Snapshot:**
- Graph revision usage must respect session snapshot (`algo_profile_at_start`, `algo_overrides_at_start`)
- All graph revision reads use snapshot config

### Why Shadow?

- Graph revision is used to **augment revision plans** with prerequisite knowledge, improving learning efficiency without disrupting FSRS core scheduling.
- **Shadow-first approach** ensures we can evaluate injection rates, coverage, and learning outcomes before affecting student queues.
- Even when activated, graph revision **does not mutate FSRS state**; it only re-orders/selects items for today's plan, maintaining FSRS as the authoritative scheduler.

---

## Algorithm Runtime Profiles & Kill Switch

### Overview

The system supports **instant, reversible switching** between algorithm versions via runtime profiles. This allows falling back to v0 (baseline) if v1 algorithms misbehave, without disrupting active students.

### Runtime Profiles

**V1_PRIMARY** (default):
- Mastery: BKT v1
- Revision: FSRS v1
- Difficulty: ELO v1
- Adaptive: Bandit v1
- Mistakes: ML v1

**V0_FALLBACK**:
- Mastery: Weighted accuracy heuristic v0
- Revision: Rules-based spaced repetition v0
- Difficulty: ELO-lite v0 (or keep v1 if safe)
- Adaptive: Deterministic rules v0
- Mistakes: Rule classifier v0

### Per-Module Overrides

You can override specific modules while keeping others on v1:

```json
{
  "profile": "V1_PRIMARY",
  "overrides": {
    "adaptive": "v0"  // Only adaptive falls back to v0
  }
}
```

### Session Snapshot Rule

**Critical:** Sessions use the algorithm profile captured at creation time.

- When a session is created, current `algo_runtime_config` is snapshotted
- Stored in `test_sessions.algo_profile_at_start` and `algo_overrides_at_start`
- All learning updates during session use snapshot config
- New sessions after switch use new config
- **No mid-session algorithm switching**

### Canonical State Store

Both v0 and v1 read/write the same canonical tables, enabling seamless transitions:

- **`user_theme_stats`**: Theme-level aggregates (attempts, correct, last_attempt_at)
- **`user_mastery_state`**: Canonical mastery score (0..1) + model-specific state
- **`user_revision_state`**: Canonical due dates + v0/v1 state fields

**Migration Strategy:**
- Existing `user_theme_mastery` populates `user_mastery_state.mastery_score`
- Existing `revision_queue` populates `user_revision_state.due_at`
- Incremental updates maintain canonical state

### State Bridging

When switching profiles, state is automatically bridged:

**v1 → v0:**
- Mastery: Use canonical `mastery_score` directly (no recompute)
- Revision: Derive v0 interval/stage from canonical `due_at`
- No cold start - state preserved

**v0 → v1:**
- Mastery: Initialize BKT from canonical `mastery_score` (non-trivial priors)
- Revision: Map v0 interval to FSRS stability/difficulty
- Preserves `due_at` continuity

**Bridging is:**
- **Lazy**: Triggered on first request after switch (per-user)
- **Idempotent**: Running twice produces same result
- **Batch**: Optional backfill job processes all active users

### Safe Mode

**Emergency freeze:** `freeze_updates=true` enables read-only mode:
- No state mutations
- Read-only decisions using cached state
- All decisions logged as "frozen"

### Admin API

- `GET /v1/admin/algorithms/runtime` - Get current config
- `POST /v1/admin/algorithms/runtime/switch` - Switch profile
- `POST /v1/admin/algorithms/runtime/freeze_updates` - Emergency freeze
- `POST /v1/admin/algorithms/runtime/unfreeze_updates` - Unfreeze
- `GET /v1/admin/algorithms/bridge/status` - Bridge job status

See `docs/runbook.md` for operational procedures.

### ALGO_BRIDGE_SPEC_v1

The bridge specification defines exact mapping rules for converting state between v1 and v0 algorithms. All mappings are **config-driven** (stored in `algo_bridge_config`) and **idempotent**.

**Key Principles:**
1. **Canonical State First**: Both v0 and v1 read/write the same canonical tables
2. **Preserve Continuity**: `due_at` and `mastery_score` are preserved across switches
3. **Non-Trivial Initialization**: v1 algorithms initialize from canonical state, not default priors
4. **Config-Driven**: All thresholds and mappings stored in DB, not hardcoded

**Mastery Bridging:**
- **v0 Computation**: Recency-weighted accuracy with configurable decay (`MASTERY_RECENCY_TAU_DAYS`)
- **BKT Initialization**: Direct mapping or shrinkage toward prior (`BKT_INIT_PRIOR_FROM_MASTERY`)

**Revision Bridging:**
- **v1→v0**: Preserves `due_at`, derives `v0_interval_days` and `v0_stage` from time intervals
- **v0→v1**: Preserves `due_at`, maps `v0_interval_days` to FSRS `stability` (monotonic_log/linear/sqrt)

**Bandit Initialization:**
- Beta prior from mastery: `alpha = 1 + mastery_score * S`, `beta = 1 + (1-mastery_score) * S`
- Strength `S` clipped between `BANDIT_PRIOR_STRENGTH_MIN` and `BANDIT_PRIOR_STRENGTH_MAX`

**Full Specification:** See `docs/ALGO_BRIDGE_SPEC_v1.md`

---

**END OF ALGORITHMS DOCUMENTATION**
