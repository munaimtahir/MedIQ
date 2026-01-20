# Constants Calibration Plan

**Purpose:** Define how temporary heuristic constants will be replaced with data-driven calibrations.

**Status:** Awaiting production data accumulation

---

## Overview

Several constants in the learning algorithms are currently set to **temporary heuristics** and require calibration from actual user data. This document specifies:

- Which constants need calibration
- Minimum data requirements
- Calibration methodology
- Success criteria
- Implementation timeline

---

## Constants Requiring Calibration

###  1. Rating Mapper Thresholds (HIGH PRIORITY)

**Constants:**
- `RATING_FAST_ANSWER_MS` (currently 15 seconds)
- `RATING_SLOW_ANSWER_MS` (currently 90 seconds)
- `RATING_MAX_CHANGES_FOR_CONFIDENT` (currently 0)

**Current Issue:**
These thresholds determine how MCQ telemetry maps to FSRS ratings (1-4). Current values are arbitrary and may not reflect actual user behavior patterns.

**Data Requirements:**
- **Minimum:** 1,000 users with 100+ attempts each
- **Preferred:** 5,000 users with 100+ attempts each
- **Features needed:** time_spent_ms, change_count, marked_for_review, correctness

**Calibration Method:**

1. **Fast/Slow Thresholds:**
   ```python
   # Stratify by block (difficulty may vary by medical subject)
   for block_id in blocks:
       times = get_times_for_block(block_id, correct_only=True)
       
       # Use percentiles to set thresholds
       FAST_THRESHOLD[block_id] = percentile(times, 25)  # p25
       SLOW_THRESHOLD[block_id] = percentile(times, 75)  # p75
   
   # Global defaults are median across blocks
   RATING_FAST_ANSWER_MS_NEW = median(FAST_THRESHOLD.values())
   RATING_SLOW_ANSWER_MS_NEW = median(SLOW_THRESHOLD.values())
   ```

2. **Max Changes Threshold:**
   ```python
   # Analyze relationship between change_count and eventual correctness
   df = get_attempts_with_changes()
   
   # Find change_count where accuracy still high
   for n_changes in range(0, 5):
       accuracy = df[df.change_count == n_changes].correct.mean()
       if accuracy >= 0.85:  # Still confident threshold
           MAX_CHANGES_NEW = n_changes
           break
   ```

**Success Criteria:**
- Calibrated thresholds improve FSRS prediction accuracy (lower logloss on validation set)
- Distribution of ratings (1-4) is reasonable (not all 3s, not all 1s/4s)
- Per-block thresholds show expected patterns (e.g., harder blocks have longer times)

**Timeline:**
- **Phase 1** (Month 3): Collect baseline data, log feature distributions
- **Phase 2** (Month 6): Run calibration analysis with first 1K users
- **Phase 3** (Month 9): Deploy calibrated thresholds, monitor improvements

---

### 2. Difficulty Weights (MEDIUM PRIORITY)

**Constants:**
- `MASTERY_DIFFICULTY_WEIGHT_EASY` (currently 0.90)
- `MASTERY_DIFFICULTY_WEIGHT_HARD` (currently 1.10)

**Current Issue:**
These weights adjust mastery scores based on question difficulty. Current values are symmetric (±10%) but actual difficulty impact may be asymmetric.

**Data Requirements:**
- **Minimum:** 500 questions per difficulty level with 100+ attempts each
- **Features needed:** question_id, difficulty_level, correctness, user_id

**Calibration Method:**

1. **Fit from Pass Rates:**
   ```python
   # Compute pass rate by difficulty
   pass_rates = {
       'easy': df[df.difficulty == 'easy'].correct.mean(),
       'medium': df[df.difficulty == 'medium'].correct.mean(),
       'hard': df[df.difficulty == 'hard'].correct.mean(),
   }
   
   # Normalize so medium = 1.0
   WEIGHT_EASY_NEW = pass_rates['medium'] / pass_rates['easy']
   WEIGHT_HARD_NEW = pass_rates['medium'] / pass_rates['hard']
   ```

2. **Validate with IRT (Item Response Theory):**
   ```python
   # Use 2PL IRT model to get discrimination/difficulty parameters
   # Weights should correlate with IRT difficulty parameters
   ```

**Success Criteria:**
- Weights reflect actual difficulty differences
- Mastery scores correlate better with exam performance
- No systematic bias (e.g., overestimating mastery on easy-heavy themes)

**Timeline:**
- **Phase 1** (Month 6): Sufficient question attempt data
- **Phase 2** (Month 9): Run IRT analysis and calibrate weights
- **Phase 3** (Month 12): Deploy and validate

---

### 3. Training Pipeline Thresholds (LOW PRIORITY)

**Constants:**
- `FSRS_MIN_LOGS_FOR_TRAINING` (currently 300)
- `BKT_MIN_ATTEMPTS_PER_CONCEPT` (currently 10)
- `BKT_MIN_USERS_PER_CONCEPT` (currently 3)

**Current Issue:**
These determine when per-user/per-concept training is triggered. Too low = overfitting, too high = delayed personalization.

**Data Requirements:**
- **Minimum:** 100 users with varying amounts of review logs (from 50 to 1000+)
- **Features needed:** Full review history for training/validation split

**Calibration Method:**

1. **FSRS Training Threshold:**
   ```python
   # Test training with varying amounts of data
   thresholds = [100, 200, 300, 500, 1000]
   
   for threshold in thresholds:
       users = get_users_with_logs_between(threshold, threshold + 100)
       
       for user in users:
           # Split data at threshold
           train = user.logs[:threshold]
           val = user.logs[threshold:]
           
           # Fit weights on train, evaluate on val
           weights = fit_fsrs(train)
           logloss_user = evaluate(weights, val)
           logloss_global = evaluate(GLOBAL_WEIGHTS, val)
           
           # Record improvement
           improvement[threshold].append(logloss_global - logloss_user)
   
   # Choose threshold where median improvement > 5%
   THRESHOLD_NEW = min(t for t in thresholds if median(improvement[t]) > 0.05)
   ```

2. **BKT Thresholds:**
   ```python
   # Similar approach: test parameter stability with varying data amounts
   # Choose thresholds where parameters converge (low variance across splits)
   ```

**Success Criteria:**
- Personalized models improve performance (lower logloss) by ≥5%
- Parameter estimates are stable (low variance across train/val splits)
- No evidence of overfitting (train vs val performance gap < 10%)

**Timeline:**
- **Phase 1** (Month 12): Sufficient users with varied log counts
- **Phase 2** (Month 15): Run threshold calibration analysis
- **Phase 3** (Month 18): Deploy adjusted thresholds

---

## Data Collection Infrastructure

### Required Telemetry

**Already Logged:**
✅ `time_spent_ms` (via attempt_events)
✅ `change_count` (via attempt_events)
✅ `marked_for_review` (via session_answers)
✅ `correctness` (via session_answers)

**Needs Enhancement:**
- ⚠️ Block/theme context in telemetry (for stratified analysis)
- ⚠️ Question difficulty metadata (for difficulty weight calibration)
- ⚠️ User demographic data (for population stratification, optional)

### Analysis Pipeline

**Tools:**
- Jupyter notebooks for exploratory analysis
- Python scripts for automated calibration
- SQL queries for data extraction

**Storage:**
- Raw data: PostgreSQL (existing tables)
- Analysis results: JSON files + version control
- Calibrated constants: `backend/app/learning_engine/config.py`

---

## Implementation Process

### Step 1: Data Readiness Check
```bash
# Check if we have sufficient data
python scripts/check_calibration_readiness.py --constant RATING_FAST_ANSWER_MS
```

Output:
```
Constant: RATING_FAST_ANSWER_MS
Status: NOT READY
Current users: 234 (need 1000)
Current attempts: 15,234 (need 100,000)
Estimated ready date: 2026-04-15
```

### Step 2: Run Calibration Analysis
```bash
# Run calibration for specific constant
python scripts/calibrate_constant.py --constant RATING_FAST_ANSWER_MS --output calibration_results.json
```

### Step 3: Review & Validate
```bash
# Generate validation report
python scripts/validate_calibration.py --input calibration_results.json
```

### Step 4: Deploy New Constants
```python
# Update config.py with calibrated values
RATING_FAST_ANSWER_MS = SourcedValue(
    value=18500,  # Updated from 15000
    source="Calibrated from 5,000 users (2026-04-15)",
    notes="P25 of time distribution across all blocks. Improves FSRS logloss by 8%.",
    validated=True
)
```

### Step 5: A/B Test
- Deploy to 10% of users first
- Monitor metrics (FSRS logloss, user engagement)
- Roll out to 100% if successful

---

## Monitoring & Re-Calibration

**Triggers for Re-Calibration:**
1. **Drift Detection:** Distribution of features shifts > 20%
2. **Scheduled:** Annual re-calibration
3. **Expansion:** New blocks/themes added
4. **Performance:** Model performance degrades > 10%

**Continuous Monitoring:**
```python
# Log feature distributions monthly
monitor_distributions(
    features=['time_spent_ms', 'change_count'],
    frequency='monthly',
    alert_threshold=0.2  # 20% shift
)
```

---

## Constants NOT Requiring Calibration

The following constants are **sourced from research/standards** and do NOT need data calibration:

✅ **FSRS_DEFAULT_WEIGHTS** - From py-fsrs population defaults
✅ **FSRS_DESIRED_RETENTION** - From Anki/FSRS standards
✅ **BKT_DEFAULT_L0/T/S/G** - From pyBKT + BKT literature
✅ **BKT_MASTERY_THRESHOLD** - From BKT standard practice (0.95)
✅ **BKT_EPSILON/MAX_PROB** - Numerical stability standards
✅ **MASTERY_LOOKBACK_DAYS** - From spaced repetition literature

These should only be changed based on:
- New research findings
- Upstream library updates
- Domain expert recommendations

---

## Summary Timeline

| Month | Milestone | Constants Ready |
|-------|-----------|-----------------|
| 0 | System launch, begin data collection | None |
| 3 | 1K users baseline | Feature analysis |
| 6 | 5K users | Rating thresholds, Difficulty weights |
| 9 | 10K users | Deploy Phase 1 calibrations |
| 12 | 20K users | Training thresholds |
| 18 | 50K users | Full calibration suite |
| Annual | Re-calibration | All constants reviewed |

---

## References

- **Rating Calibration:** Inspired by Anki's ease factor calibration
- **IRT for Difficulty:** Rasch, G. (1960). "Probabilistic Models for Some Intelligence and Attainment Tests"
- **Threshold Selection:** Standard ML practice (grid search + cross-validation)
- **A/B Testing:** Standard product experimentation methodology
