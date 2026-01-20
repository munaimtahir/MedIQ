# Constants Audit Report
**Generated:** 2026-01-21  
**Purpose:** Identify all magic numbers and constants requiring provenance

## Executive Summary

This audit identifies **23 constants** across BKT and FSRS implementations that require proper sourcing and centralization.

**Current Status:**
- ❌ **0 of 23** have documented provenance
- ❌ **0 of 23** are centralized in a registry
- ❌ **0 of 23** have validation tests

---

## FSRS Constants (Task 120)

### FSRS-6 Default Weights

**Location:** `backend/app/learning_engine/srs/fsrs_adapter.py:21-26`  
**Variable:** `DEFAULT_FSRS_6_WEIGHTS`  
**Current Value:** Array of 19 floats  
```python
[0.4072, 1.1829, 3.1262, 15.4722, 7.2102,
 0.5316, 1.0651, 0.0234, 1.616, 0.1544,
 1.0824, 1.9813, 0.0953, 0.2975, 2.2042,
 0.2407, 2.9466, 0.5034, 0.6567]
```
**Used For:** Default FSRS scheduler weights when no personalized weights trained  
**Source:** ❌ NO - Claimed to be "from the FSRS paper" but no specific citation  
**Issue:** Prompt mentions FSRS-6 should have 21 parameters, not 19. Need to verify correct version.

### Desired Retention Default

**Location:** `backend/app/learning_engine/srs/fsrs_adapter.py:28`  
**Variable:** `DEFAULT_DESIRED_RETENTION`  
**Current Value:** `0.90`  
**Used For:** Target retention probability (90%)  
**Source:** ❌ NO - No documented source  
**Issue:** Need to verify this matches py-fsrs defaults or PDFs

### Retention Range for Optimal Computation

**Location:** `backend/app/learning_engine/srs/fsrs_adapter.py:209-210`  
**Variables:** `max_retention`, `min_retention`  
**Current Values:** `0.95`, `0.70`  
**Used For:** Bounds for computing optimal retention  
**Source:** ❌ NO  
**Issue:** Arbitrary bounds without justification

### User Params Default

**Location:** `backend/app/learning_engine/srs/service.py:60`  
**Value:** `desired_retention=0.90`  
**Used For:** Initial user param when creating new SRS user  
**Source:** ❌ NO - Duplicates DEFAULT_DESIRED_RETENTION

---

## Rating Mapper Constants (Task 120)

### Fast Answer Threshold

**Location:** `backend/app/learning_engine/srs/rating_mapper.py:23`  
**Variable:** `FAST_ANSWER_MS`  
**Current Value:** `15000` (15 seconds)  
**Used For:** Threshold for rating 4 (Easy) - "fast answer"  
**Source:** ❌ NO - Arbitrary threshold  
**Issue:** Should be calibrated from actual data or sourced from research

### Slow Answer Threshold

**Location:** `backend/app/learning_engine/srs/rating_mapper.py:24`  
**Variable:** `SLOW_ANSWER_MS`  
**Current Value:** `90000` (90 seconds)  
**Used For:** Threshold for rating 2 (Hard) - "slow answer"  
**Source:** ❌ NO - Arbitrary threshold  
**Issue:** Should be calibrated from actual data

### Max Changes for Confident

**Location:** `backend/app/learning_engine/srs/rating_mapper.py:25`  
**Variable:** `MAX_CHANGES_FOR_CONFIDENT`  
**Current Value:** `0`  
**Used For:** Max answer changes to still be considered "confident" (Easy)  
**Source:** ❌ NO - Arbitrary  
**Issue:** Possibly too strict (any change → not confident)

### Telemetry Validation Thresholds

**Location:** `backend/app/learning_engine/srs/rating_mapper.py:172-173`  
**Values:** `3600000` (1 hour max), `500` (0.5 seconds min)  
**Used For:** Detecting suspiciously long/short times  
**Source:** ❌ NO - Arbitrary bounds

**Location:** `backend/app/learning_engine/srs/rating_mapper.py:183-184`  
**Value:** `20` (max changes cap)  
**Used For:** Capping extreme change_count values  
**Source:** ❌ NO - Arbitrary cap

---

## BKT Constants (Task 119)

### Numerical Stability Constants

**Location:** `backend/app/learning_engine/bkt/core.py:18-19`  
**Variables:** `EPSILON`, `MAX_PROB`  
**Current Values:** `1e-10`, `1.0 - 1e-10`  
**Used For:** Clamping probabilities to avoid numerical issues  
**Source:** ❌ NO - Standard practice but not documented  
**Issue:** Reasonable values but should document why 1e-10 chosen

### BKT Default Parameters

**Location:** `backend/app/learning_engine/bkt/service.py:35-40`  
**Variable:** `DEFAULT_BKT_PARAMS`  
**Current Values:**
```python
{
    "p_L0": 0.1,  # 10% prior mastery
    "p_T": 0.2,   # 20% learning rate
    "p_S": 0.1,   # 10% slip rate
    "p_G": 0.2    # 20% guess rate
}
```
**Used For:** Fallback BKT parameters when no fitted params exist  
**Source:** ❌ NO - No documented source  
**Issue:** Need to verify these are reasonable starting points from literature

### BKT Mastery Threshold

**Location:** `backend/app/learning_engine/bkt/service.py:351`  
**Value:** `0.95`  
**Used For:** Threshold for considering a concept "mastered"  
**Source:** ❌ NO - Claimed to be "default threshold" but no citation  
**Issue:** User mentioned 0.95 might be in PDFs - need to verify and cite

### BKT Training Constraints

**Location:** `backend/app/learning_engine/bkt/training.py:248-249`  
**Values:** `0.001` (min), `0.999` (max)  
**Used For:** Default min/max bounds for BKT parameter constraints  
**Source:** ❌ NO - Arbitrary bounds  
**Issue:** Too loose? Should these be tighter based on research?

---

## Mastery v0 Constants (Task 103-104)

### Difficulty Weights

**Location:** `backend/app/learning_engine/params.py:52-54`  
**Location:** `backend/app/learning_engine/mastery/service.py:73-75`  
**Values:**
```python
{
    "easy": 0.90,
    "medium": 1.00,
    "hard": 1.10
}
```
**Used For:** Weighting mastery scores by difficulty  
**Source:** ❌ NO - Arbitrary multipliers  
**Issue:** Should be calibrated or sourced

### Mastery v0 Default Params

**Location:** `backend/app/learning_engine/params.py:18-55`  
**Values:**
- `lookback_days`: 90
- `min_attempts`: 3
- `recency_buckets`: [0, 7, 30, 90] days
- `use_difficulty`: False

**Source:** ❌ NO - No documented rationale

---

## Training Pipeline Constants

### SRS Training Thresholds

**Mentioned in docs but not yet implemented:**
- Minimum review logs: 300
- Validation split: 0.2 (20%)
- Shrinkage alpha formula: `min(0.8, log(n)/log(5000))`

**Source:** ❌ NO - No source for these specific values

### BKT Training Thresholds

**Location:** Various in `backend/app/learning_engine/bkt/training.py`
- Minimum attempts per concept: 10
- Minimum users: 3

**Source:** ❌ NO - Arbitrary thresholds

---

## Summary by Category

| Category | Count | Has Source | Needs Calibration |
|----------|-------|------------|-------------------|
| FSRS Weights | 1 | ❌ | ❌ |
| FSRS Thresholds | 3 | ❌ | ❌ |
| Rating Mapper | 5 | ❌ | ✅ (from data) |
| BKT Parameters | 4 | ❌ | ⚠️ (some) |
| BKT Constraints | 2 | ❌ | ❌ |
| Mastery Weights | 3 | ❌ | ✅ (from data) |
| Training Thresholds | 5 | ❌ | ⚠️ (some) |
| **TOTAL** | **23** | **0** | **varies** |

---

## Priority Actions

### HIGH PRIORITY (Correctness Issues)
1. **Verify FSRS-6 weights** - Confirm 19 vs 21 parameters and match py-fsrs exactly
2. **Verify BKT mastery threshold** - Check PDFs for 0.95 or other value
3. **Centralize all constants** - Create single source of truth registry

### MEDIUM PRIORITY (Research Required)
4. **Document FSRS desired_retention** - Find authoritative default
5. **Document BKT default params** - Find literature sources or pyBKT guidance
6. **Document numerical stability constants** - Standard practice documentation

### LOW PRIORITY (Calibration Plans)
7. **Rating mapper thresholds** - Create calibration plan for when data available
8. **Difficulty weights** - Create calibration plan
9. **Training thresholds** - Document rationale or plan to tune

---

## Recommendations

1. **Create `backend/app/learning_engine/constants.py`**
   - Use `SourcedValue` dataclass with mandatory `source` field
   - All constants must have provenance
   - Add validation on import

2. **Create `docs/constants.md`**
   - Document each constant with source, rationale, and impact
   - Link to PDFs, papers, or upstream docs

3. **Add `docs/calibration-plan.md`**
   - For constants requiring data calibration
   - Specify when/how they'll be updated

4. **Add provenance tests**
   - `backend/tests/test_constants_provenance.py`
   - Enforce all constants have non-empty sources

5. **Add verification script**
   - `backend/scripts/verify_constants.py`
   - Runtime checks for all constants

---

## Next Steps

1. ✅ Audit complete
2. ⏳ Implement constants registry
3. ⏳ Source FSRS-6 weights from py-fsrs
4. ⏳ Source BKT values from PDFs/literature
5. ⏳ Refactor code to use registry
6. ⏳ Add tests and verification
7. ⏳ Update documentation
