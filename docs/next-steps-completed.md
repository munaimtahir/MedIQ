# Next Steps Completed

**Date:** 2026-01-24

## Summary

Completed all next steps except #3 (testing with real data, which is not available yet).

---

## 1. Migration Documentation ✅

**Status:** Documented (migration needs to be run when database is available)

Created comprehensive documentation in `backend/docs/jobs-setup.md` covering:
- Migration instructions
- Crontab setup for Linux/Mac
- Windows Task Scheduler setup
- Docker/container setup
- Manual execution
- Job locking details
- Monitoring and troubleshooting

**Note:** Actual migration (`alembic upgrade head`) should be run when database is available.

---

## 2. Crontab Documentation ✅

**Status:** Complete

Documented in `backend/docs/jobs-setup.md`:
- Crontab/container: use `docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend python -m app.jobs.run revision_queue_regen` (see `backend/docs/jobs-setup.md`).
- Docker/container cron setup
- Logging and error handling

---

## 4. FSRS Training Pipeline ✅

**Status:** Fully Implemented

### Implementation (`backend/app/jobs/fsrs_train_user.py`)

1. **Training Function** (`train_fsrs_for_user`)
   - Loads user's review logs chronologically
   - Splits into train/val (80/20, last 20% for validation)
   - Uses py-fsrs `Optimizer` to fit personalized weights
   - Applies shrinkage (blends with defaults based on log count)
   - Validates on holdout set
   - Computes metrics (logloss, brier)
   - Updates `srs_user_params` with new weights and metrics

2. **Shrinkage Logic**
   - Alpha = min(0.8, sqrt(n_logs / 5000))
   - Blends personalized weights with defaults: `alpha * personalized + (1-alpha) * defaults`
   - Prevents overfitting for users with fewer logs

3. **Job Processing** (`process_fsrs_training_job`)
   - Extracts user_id from job_run metadata
   - Calls training function
   - Handles errors and updates job status

4. **Integration with Optimizer Trigger**
   - Updated `fsrs_optimizer_trigger.py` to store user_id in job_run.stats_json
   - Job can be processed by job runner

### Constants Used
- `FSRS_MIN_LOGS_FOR_TRAINING` (300)
- `FSRS_VALIDATION_SPLIT` (0.2)
- `FSRS_SHRINKAGE_MAX_ALPHA` (0.8)
- `FSRS_SHRINKAGE_TARGET_LOGS` (5000)

---

## 5. User Preferences UI ✅

**Status:** Complete

### Implementation

1. **New Component** (`frontend/components/student/settings/LearningPreferencesCard.tsx`)
   - Form fields for:
     - Revision Daily Target (optional integer)
     - Spacing Multiplier (0.5-2.0, default 1.0)
     - Retention Target Override (0.7-0.95, optional)
   - Validation with error messages
   - Success/error alerts
   - Loading states

2. **Integration**
   - Added to `/student/settings` page
   - Positioned after Practice Preferences card
   - Uses existing API endpoints (`GET/PATCH /v1/users/me/preferences/learning`)

3. **Features**
   - Real-time validation
   - Clear error messages
   - Success feedback
   - Helpful descriptions for each field

---

## 6. FSRS Suite for Eval Harness ✅

**Status:** Complete

### Implementation (`backend/app/learning_engine/eval/suites/fsrs_suite.py`)

1. **FSRSEvalSuite Class**
   - Implements `EvalSuite` interface
   - Async `predict()` method:
     - Loads user params (personalized weights if available)
     - Gets concept state from DB
     - Computes retrievability using FSRS scheduler
     - Returns `ReplayPrediction` with p_correct and p_retrievability
   
   - Async `update()` method:
     - Updates FSRS state after ground-truth outcome
     - Converts outcome to FSRS rating (simplified: Good=3 if correct, Again=1 if wrong)
     - Computes delta_days
     - Calls `compute_next_state_and_due` to update stability/difficulty
     - Stores updated state in algo_state

2. **Integration**
   - Added to `suites/__init__.py`
   - Can be used in evaluation runs alongside BKT suite
   - Supports both global defaults and personalized weights

3. **Async Support**
   - Updated `EvalSuite` interface to use async methods
   - Updated `replay_user_stream` and `replay_dataset` to be async
   - Updated `runner.py` to await replay calls

### Features
- Uses personalized FSRS weights if available (from `srs_user_params`)
- Falls back to defaults if no personalized weights
- Handles concept_id mapping with fallback
- Computes retrievability for predictions
- Updates state deterministically

---

## Files Created/Modified

### New Files
- `backend/docs/jobs-setup.md` - Job system setup documentation
- `backend/app/jobs/fsrs_train_user.py` - FSRS training pipeline
- `backend/app/learning_engine/eval/suites/fsrs_suite.py` - FSRS eval suite
- `frontend/components/student/settings/LearningPreferencesCard.tsx` - Learning preferences UI

### Modified Files
- `backend/app/jobs/fsrs_optimizer_trigger.py` - Store user_id in job metadata
- `backend/app/jobs/run.py` - Added FSRS training job handling
- `backend/app/learning_engine/eval/replay.py` - Made methods async
- `backend/app/learning_engine/eval/suites/bkt_suite.py` - Made methods async
- `backend/app/learning_engine/eval/suites/__init__.py` - Added FSRSEvalSuite
- `backend/app/learning_engine/eval/runner.py` - Await async replay
- `frontend/app/student/settings/page.tsx` - Added LearningPreferencesCard

---

## Testing Notes

### FSRS Training
- Requires at least 300 review logs per user
- Can be triggered manually or via optimizer trigger
- Validates on holdout set (last 20% of logs)
- Stores metrics in `srs_user_params.metrics_json`

### User Preferences
- UI validates input ranges
- API enforces constraints server-side
- Preferences persist in `user_learning_prefs` table

### FSRS Eval Suite
- Can be used in evaluation runs
- Supports both global and personalized weights
- Computes retrievability-based predictions

---

## Next Actions

1. **Run Migration** (when database available):
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Set Up Crontab** (when deploying):
   - Follow instructions in `backend/docs/jobs-setup.md`
   - Test job execution manually first

3. **Test FSRS Training** (when real data available):
   - Trigger training for a user with 300+ logs
   - Verify weights are updated
   - Check metrics in `srs_user_params`

4. **Test User Preferences**:
   - Navigate to `/student/settings`
   - Update learning preferences
   - Verify API calls succeed
   - Check database updates

5. **Test Eval Harness with FSRS**:
   - Create evaluation run with FSRS suite
   - Verify predictions and metrics are computed
   - Check that personalized weights are used when available

---

## Known Limitations

1. **FSRS Training Validation**: Currently simplified - full validation would need complete state tracking across concepts
2. **Rating Conversion**: FSRS suite uses simplified rating (Good/Again) - could be enhanced with telemetry-based rating
3. **Concept Mapping**: Still uses fallback mapping - proper concept→theme mapping needed when concept graph is ready
