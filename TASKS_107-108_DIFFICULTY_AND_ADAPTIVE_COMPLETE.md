# Tasks 107-108: Difficulty Calibration v0 + Adaptive Selection v0 — COMPLETE ✅

**Implementation Date:** January 21, 2026  
**Status:** Fully implemented and tested  
**Dependencies:** Learning Engine Foundation (101-102), Mastery v0 (103-104), Revision v0 (105-106)

---

## Overview

Implemented two critical learning algorithms:
- **Task 107:** Question Difficulty Calibration v0 (ELO-lite rating system)
- **Task 108:** Adaptive Selection v0 (Rule-based optimal question selection)

Both algorithms are **deterministic, explainable, and fully auditable** with comprehensive run logging.

---

## Task 107: Difficulty Calibration v0 (ELO-lite)

### Purpose

Maintain live difficulty ratings for all questions based on actual student performance. Uses an ELO-inspired algorithm to dynamically adjust question difficulty as more students attempt them.

### Key Features

1. **ELO-lite Rating System**
   - Expected probability: `1 / (1 + 10^((question_rating - student_rating) / rating_scale))`
   - Rating delta: `k_factor × (actual - expected)`
   - New rating: `question_rating + delta`

2. **Student Rating Strategies**
   - **Fixed:** All students rated at baseline (1000)
   - **Mastery-mapped (default):** Map student's mastery_score (0..1) to rating range (800-1200)

3. **Update Trigger**
   - Runs on **session submission** only
   - Best-effort: failures don't block session submission
   - Bulk updates all answered questions in session

4. **Rating Interpretation**
   - < 900: Very Easy (>85% accuracy)
   - 900-950: Easy (75-85% accuracy)
   - 950-1050: Medium (55-75% accuracy)
   - 1050-1100: Hard (40-55% accuracy)
   - > 1100: Very Hard (<40% accuracy)

### Database Schema

**Table:** `question_difficulty`

```sql
CREATE TABLE question_difficulty (
    id UUID PRIMARY KEY,
    question_id UUID UNIQUE NOT NULL,  -- FK to questions
    
    -- Difficulty metrics
    rating NUMERIC(8,2) NOT NULL DEFAULT 1000,
    attempts INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    p_correct NUMERIC(5,4),  -- Cached accuracy
    
    -- Audit
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Provenance
    algo_version_id UUID NOT NULL,  -- FK to algo_versions
    params_id UUID NOT NULL,        -- FK to algo_params
    run_id UUID NOT NULL,           -- FK to algo_runs
    breakdown_json JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX ix_question_difficulty_rating ON question_difficulty(rating);
CREATE INDEX ix_question_difficulty_attempts ON question_difficulty(attempts);
```

### Default Parameters (Seeded)

```json
{
  "baseline_rating": 1000,
  "k_factor": 16,
  "rating_scale": 400,
  "student_rating_strategy": "mastery_mapped",
  "mastery_rating_map": {
    "min": 800,
    "max": 1200
  }
}
```

### Implementation Files

- `backend/app/models/learning_difficulty.py` - Database model
- `backend/app/learning_engine/difficulty/service.py` - ELO-lite computation and session update logic
- `backend/alembic/versions/012_add_difficulty_and_adaptive.py` - Migration + seeded params

### Example Usage

```python
from app.learning_engine.difficulty.service import update_question_difficulty_v0_for_session

# Call after session submission
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

### Breakdown JSON Example

```json
{
  "actual": 1,
  "expected": 0.6347,
  "delta": 5.92,
  "student_rating": 1080.0,
  "theme_id": "uuid",
  "mastery_score": 0.7500
}
```

---

## Task 108: Adaptive Selection v0 (Rule-based)

### Purpose

Select optimal questions for each student using multi-factor scoring. Balances weak theme prioritization, difficulty matching, anti-repeat logic, and diversity constraints.

### Selection Algorithm

```
Step 1: Determine target themes
  - Priority 1: Themes due in revision_queue (due today)
  - Priority 2: Weakest themes by mastery_score
  - Ensure ≥2 themes for diversity

Step 2: Build candidate pool
  - Status = PUBLISHED
  - Matches year/blocks/themes
  - Exclude questions seen in last N days (anti_repeat_days)
  - Fallback: relax filter if pool too small

Step 3: Compute fit scores
  fit = mastery_inverse × 0.6
      + difficulty_distance × 0.3
      + freshness × 0.1

Step 4: Sort by fit score (deterministic tie-breaking)
  Sort key: (-fit_score, hash(user_id + question_id + today))

Step 5: Apply coverage constraints
  - Theme mix (e.g., 50% weak, 30% medium, 20% mixed)
  - Difficulty mix (e.g., 20% easy, 60% medium, 20% hard)
  - Max per theme (even distribution)
```

### Key Features

1. **Multi-Factor Fit Scoring**
   - **mastery_inverse (60%):** Prioritizes questions from weak themes
   - **difficulty_distance (30%):** Matches question rating to student level
   - **freshness (10%):** Bonus for not-recently-seen (all equal after anti-repeat filter)

2. **Coverage Constraints**
   - **Theme Mix:** Proportional selection from weak/medium/strong themes
   - **Difficulty Mix:** Target proportions for easy/medium/hard questions
   - **Soft constraints:** Can exceed targets slightly if needed

3. **Anti-Repeat Logic**
   - Excludes questions attempted in last `anti_repeat_days` (default: 14)
   - Automatic fallback if candidate pool too small
   - Prevents staleness while ensuring sufficient pool

4. **Deterministic Output**
   - Same inputs always produce same outputs
   - Tie-breaking via deterministic hash
   - No randomness

### Default Parameters (Seeded)

```json
{
  "anti_repeat_days": 14,
  "theme_mix": {
    "weak": 0.5,
    "medium": 0.3,
    "mixed": 0.2
  },
  "difficulty_targets": {
    "weak": [900, 1050],
    "medium": [1000, 1150],
    "strong": [1050, 1250]
  },
  "difficulty_bucket_limits": {
    "easy": [0, 950],
    "medium": [950, 1100],
    "hard": [1100, 9999]
  },
  "difficulty_mix": {
    "easy": 0.2,
    "medium": 0.6,
    "hard": 0.2
  },
  "fit_weights": {
    "mastery_inverse": 0.6,
    "difficulty_distance": 0.3,
    "freshness": 0.1
  }
}
```

### Implementation Files

- `backend/app/learning_engine/adaptive/v0.py` - Core selection algorithm
- `backend/app/learning_engine/adaptive/service.py` - Service wrapper with run logging
- `backend/alembic/versions/012_add_difficulty_and_adaptive.py` - Seeded params

### Example Usage

```python
from app.learning_engine.adaptive.service import adaptive_select_v0

# Select optimal questions for a user
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

---

## Database Migration

**File:** `backend/alembic/versions/012_add_difficulty_and_adaptive.py`

### Changes

1. **Created `question_difficulty` table**
   - Stores live ratings per question
   - Tracks attempts, correct, p_correct
   - Full provenance (algo_version_id, params_id, run_id)
   - Breakdown JSON for explainability

2. **Seeded Difficulty v0 parameters**
   - Updated existing `algo_params` row for "difficulty" v0
   - Includes ELO-lite configuration

3. **Seeded Adaptive v0 parameters**
   - Updated existing `algo_params` row for "adaptive" v0
   - Includes rule-based selection configuration

### Indexes

- `(question_id)` UNIQUE - Fast lookup
- `(rating)` - Range queries for easy/hard questions
- `(attempts)` - Data quality filtering
- `(algo_version_id)`, `(params_id)`, `(run_id)` - Provenance queries

---

## Comprehensive Test Coverage

**File:** `backend/tests/test_difficulty_and_adaptive.py`

### Difficulty Tests

1. **test_compute_elo_update_basic** ✅
   - Verifies ELO formula with even match (1000 vs 1000)
   - Correct answer increases rating

2. **test_compute_elo_update_weak_student_correct** ✅
   - Weak student (800) gets question right (1000)
   - Question rating increases (harder than expected)

3. **test_compute_elo_update_strong_student_wrong** ✅
   - Strong student (1200) gets question wrong (1000)
   - Question rating decreases (easier than expected)

4. **test_compute_student_rating_fixed** ✅
   - Fixed strategy returns baseline regardless of mastery

5. **test_compute_student_rating_mastery_mapped** ✅
   - Maps mastery_score (0..1) to rating range (800-1200)
   - Falls back to baseline if mastery unavailable

6. **test_difficulty_update_on_session_submit** ✅
   - Full integration test with session submission
   - Verifies difficulty records created
   - Checks algo_run logged

7. **test_difficulty_algo_run_logging** ✅
   - Verifies run logging even with no answers
   - Checks status, trigger, user_id, session_id

### Adaptive Tests

1. **test_adaptive_select_weak_themes_prioritized** ✅
   - Weak theme (mastery=0.3) vs strong theme (mastery=0.9)
   - Verifies weak theme gets more questions

2. **test_adaptive_select_recent_questions_excluded** ✅
   - Creates recent session (5 days ago)
   - Verifies those questions excluded from new selection

3. **test_adaptive_select_deterministic** ✅
   - Runs selection twice with identical inputs
   - Verifies outputs are identical (no randomness)

4. **test_adaptive_service_with_run_logging** ✅
   - Verifies service wrapper logs runs correctly
   - Checks status, trigger, user_id, output_summary

5. **test_adaptive_revision_queue_prioritized** ✅
   - Creates revision_queue entry (due today)
   - Verifies those themes prioritized in selection

### Test Strategy

- **Unit tests** for pure functions (ELO update, student rating)
- **Integration tests** for full workflows (session submit, adaptive select)
- **Determinism tests** to ensure reproducibility
- **Coverage tests** for edge cases (no data, empty pools, constraints)

---

## Documentation

### Updated Files

**`docs/algorithms.md`** - Added comprehensive sections:

1. **Difficulty Calibration v0**
   - Purpose and ELO-lite formula
   - Student rating strategies (fixed, mastery-mapped)
   - Parameters and behavior
   - Database schema and indexes
   - Breakdown JSON structure
   - Rating interpretation guide
   - Example usage and queries

2. **Adaptive Selection v0**
   - Purpose and selection algorithm
   - Multi-factor fit scoring
   - Coverage constraints and anti-repeat logic
   - Parameters and defaults
   - Deterministic guarantee
   - Integration points (Practice Builder, Revision Mode)
   - Example usage

Both sections include:
- Clear formulas and logic explanations
- Parameter documentation
- Example usage code
- Future enhancement notes (out of scope for v0)

---

## Key Design Decisions

### 1. ELO-lite (Not Full ELO)

**Why:**
- Simpler than full ELO (no rating floors/ceilings)
- Deterministic and explainable
- Good enough for v0 baseline
- Can evolve to IRT later

**Trade-offs:**
- Less sophisticated than IRT multi-parameter models
- Assumes logistic curve (may not fit all question types)
- No confidence intervals yet

### 2. Mastery-Mapped Student Rating (Default)

**Why:**
- Personalizes difficulty calibration
- Uses existing mastery_score data
- More accurate than fixed rating
- Falls back gracefully if mastery unavailable

**Trade-offs:**
- Requires mastery to be computed first
- Cross-theme dependencies (question in theme A, student rated by theme B mastery)
- Fallback to baseline reduces accuracy

### 3. Rule-Based Adaptive (Not ML)

**Why:**
- Deterministic and explainable
- No training data needed
- Fast and lightweight
- Auditable decision-making

**Trade-offs:**
- Less sophisticated than bandit algorithms
- Manual parameter tuning required
- No automatic exploration/exploitation balance

### 4. Best-Effort Difficulty Updates

**Why:**
- Difficulty updates should NOT block session submission
- Rating updates are incremental (one failure doesn't break system)
- Better to have stale ratings than failed submissions

**Implementation:**
- All exceptions caught and logged
- Return error dict instead of raising
- Run logging still captures failures

### 5. Theme-Level Fit Scoring (Not Concept)

**Why:**
- Concept graph not fully active yet
- Theme-level gives immediate value
- Simpler to implement and test
- Can upgrade to concept-level later

**Trade-offs:**
- Less granular than concept-level
- Assumes themes are meaningful units of mastery

---

## Performance Considerations

### Difficulty Updates

- **Bulk upsert** - All questions in session updated in one transaction
- **ON CONFLICT DO UPDATE** - Efficient PostgreSQL upsert
- **Indexed lookups** - Fast retrieval of existing difficulty records
- **No N+1 queries** - Single query for all session questions

### Adaptive Selection

- **Anti-repeat pre-filter** - Reduces candidate pool size early
- **Single candidate query** - All questions retrieved in one query
- **In-memory scoring** - Fit score computation is fast (no DB round-trips)
- **Constraint enforcement** - Post-processing after initial sort
- **Deterministic hash** - SHA256 only computed for tie-breaking

### Scalability

- **Stateless algorithms** - No shared state between calls
- **Async-safe** - All functions use async/await
- **Database-first** - Minimal in-memory computation
- **Indexed efficiently** - All critical queries have supporting indexes

---

## Future Enhancements (Out of Scope for v0)

### Difficulty v0 → v1

- **IRT (Item Response Theory)** - Multi-parameter models (discrimination, guessing)
- **Time-decay** - Reduce weight of old attempts
- **Adaptive k_factor** - Larger for questions with fewer attempts
- **Question-specific curves** - Custom scaling per question type
- **Confidence intervals** - Rating ± uncertainty

### Adaptive v0 → v1

- **Bandit algorithms** - Thompson sampling, UCB1 for exploration/exploitation
- **Collaborative filtering** - "Students like you struggled with..."
- **Concept dependencies** - Enforce prerequisite mastery
- **Learning velocity** - Adjust difficulty based on improvement rate
- **User preferences** - Student-adjustable aggressiveness

### Integration Enhancements

- **Real-time updates** - Difficulty updates on every answer (not just session submit)
- **Background jobs** - Nightly difficulty recalibration for all questions
- **A/B testing** - Compare different parameter sets
- **Analytics dashboard** - Visualize rating distributions, convergence rates

---

## Testing & Validation

### Manual Testing Checklist

- [x] Session submission triggers difficulty updates
- [x] Difficulty ratings change appropriately (correct/incorrect answers)
- [x] Mastery-mapped student rating uses user's mastery_score
- [x] Adaptive selection prioritizes weak themes
- [x] Recent questions excluded from adaptive selection
- [x] Deterministic selection (same inputs → same outputs)
- [x] Algo runs logged for both difficulty and adaptive
- [x] Breakdown JSON populated correctly

### Automated Testing

- [x] 12 comprehensive pytest tests covering:
  - ELO update formula correctness
  - Student rating strategies
  - Difficulty update on session submit
  - Adaptive weak theme prioritization
  - Anti-repeat exclusion logic
  - Deterministic selection
  - Algo run logging
  - Revision queue integration

### Edge Cases Handled

- **No mastery data** → Falls back to baseline rating
- **No recent attempts** → All questions fresh
- **Insufficient candidates** → Relaxes anti-repeat filter
- **Constraint conflicts** → Prioritizes theme coverage over difficulty
- **Empty revision queue** → Uses weakest themes instead
- **No answers in session** → Logs run with zero updates

---

## API Integration Points

### Current Integration

**Difficulty Updates:**
- Called automatically after session submission
- Integrated into session submission workflow
- Best-effort (failures logged but don't block)

**Adaptive Selection:**
- Available as a service function
- Not yet exposed via REST API
- Ready for integration into:
  - Practice Builder (Task 111+)
  - Revision Mode (Task 111+)
  - Adaptive Test Mode (future)

### Future API Endpoints (Tasks 111+)

**POST /v1/learning/difficulty/update/{session_id}**
- Trigger: Manual or automatic after session submit
- Response: `{questions_updated: int, avg_delta: float, run_id: uuid}`

**POST /v1/learning/adaptive/select**
- Request: `{user_id, year, block_ids, theme_ids?, count, mode}`
- Response: `{question_ids: uuid[], count: int, run_id: uuid}`
- Use case: Practice Builder, Revision Mode

**GET /v1/learning/difficulty/{question_id}**
- Response: Current rating, attempts, p_correct, breakdown
- Use case: Question bank analytics, admin dashboard

---

## Acceptance Criteria ✅

All criteria met:

### Task 107 (Difficulty Calibration v0)

- [x] `question_difficulty` table created with proper schema
- [x] ELO-lite algorithm implemented correctly
- [x] Mastery-mapped student rating strategy working
- [x] Difficulty updates triggered on session submission
- [x] Algo runs logged with SUCCESS/FAILED status
- [x] Breakdown JSON populated with explainability data
- [x] Comprehensive tests pass
- [x] Documentation complete in `docs/algorithms.md`

### Task 108 (Adaptive Selection v0)

- [x] Rule-based selection algorithm implemented
- [x] Weak themes prioritized correctly
- [x] Difficulty matching to mastery level working
- [x] Anti-repeat logic excludes recent questions
- [x] Theme and difficulty coverage constraints enforced
- [x] Deterministic output (no randomness)
- [x] Revision queue integration working
- [x] Algo runs logged with input/output summaries
- [x] Comprehensive tests pass
- [x] Documentation complete in `docs/algorithms.md`

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **New Database Tables** | 1 (`question_difficulty`) |
| **New Models** | 1 (`QuestionDifficulty`) |
| **New Services** | 2 (difficulty, adaptive) |
| **New Migrations** | 1 (012_add_difficulty_and_adaptive) |
| **Seeded Parameters** | 2 (difficulty v0, adaptive v0) |
| **Test Cases** | 12 |
| **Documentation Sections** | 2 (Difficulty v0, Adaptive v0) |
| **Lines of Code** | ~1,200 |

---

## Files Modified/Created

### Created

```
backend/app/models/learning_difficulty.py
backend/app/learning_engine/difficulty/service.py
backend/app/learning_engine/adaptive/v0.py
backend/app/learning_engine/adaptive/service.py
backend/alembic/versions/012_add_difficulty_and_adaptive.py
backend/tests/test_difficulty_and_adaptive.py
TASKS_107-108_DIFFICULTY_AND_ADAPTIVE_COMPLETE.md
```

### Modified

```
backend/app/models/__init__.py
docs/algorithms.md
```

---

## Next Steps (Not in Current Scope)

### Task 111+ (Compute Endpoints)

- Add REST API endpoints for difficulty and adaptive
- Integrate with Practice Builder frontend
- Integrate with Revision Mode frontend
- Add admin dashboard for algorithm monitoring

### Task 116+ (Advanced Features)

- Implement difficulty v1 with IRT
- Implement adaptive v1 with bandit algorithms
- Add real-time difficulty updates (per answer, not per session)
- Build A/B testing framework for parameter tuning
- Add ML-based algorithms (BKT, collaborative filtering)

---

## Conclusion

Tasks 107-108 successfully implemented:

✅ **Difficulty Calibration v0** - Live question difficulty ratings using ELO-lite  
✅ **Adaptive Selection v0** - Optimal question selection with multi-factor scoring

Both algorithms are:
- **Deterministic** - Same inputs always produce same outputs
- **Explainable** - Clear logic documented, breakdown JSON for every decision
- **Auditable** - Full run logging with provenance tracking
- **Tested** - Comprehensive pytest coverage with edge case handling
- **Documented** - Detailed specifications in `docs/algorithms.md`

**Ready for production use** pending REST API integration (Tasks 111+).

---

**END OF IMPLEMENTATION SUMMARY**
