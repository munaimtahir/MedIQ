# ALGO_BRIDGE_SPEC_v1 — Algorithm State Bridging Specification

**Version:** 1.0  
**Date:** 2026-01-25  
**Status:** Active

---

## Overview

This specification defines the exact mapping rules for converting algorithm state between v1 (BKT/FSRS/ELO/Bandit) and v0 (rule-based baseline) implementations. The goal is **seamless fallback** without student disruption: no resets, no loss of due dates, no mastery history loss.

---

## Principles

1. **Canonical State First**: Both v0 and v1 read/write the same canonical tables
2. **Preserve Continuity**: `due_at` and `mastery_score` are preserved across switches
3. **Non-Trivial Initialization**: v1 algorithms initialize from canonical state, not default priors
4. **Idempotent**: Running bridge twice produces identical results
5. **Config-Driven**: All thresholds and mappings are stored in `algo_bridge_config`, not hardcoded

---

## Configuration Parameters

All parameters are stored in `algo_bridge_config.config_json`:

### Mastery Parameters
- `MASTERY_FLOOR`: Minimum mastery score (default: 0.01)
- `MASTERY_CEIL`: Maximum mastery score (default: 0.99)
- `MASTERY_MIN_ATTEMPTS_FOR_CONFIDENCE`: Minimum attempts before reporting mastery (default: 10)
- `MASTERY_RECENCY_TAU_DAYS`: Recency decay time constant (default: 21)

### Revision Parameters
- `V0_INTERVAL_BINS_DAYS`: Array of interval bins for v0 staging (default: [1,3,7,14,30,60,120])
- `V0_STAGE_MAX`: Maximum v0 stage number (default: 6)
- `DUE_AT_PRESERVATION_MODE`: "preserve" | "preserve_if_reasonable" | "recompute" (default: "preserve")

### BKT Initialization Parameters
- `BKT_INIT_PRIOR_FROM_MASTERY`: "direct" | "shrink_to_prior" (default: "direct")
- `BKT_PRIOR_SHRINK_ALPHA`: Shrinkage factor for shrink_to_prior mode (default: 0.15)
- `BKT_MIN_OBS_FOR_STRONG_INIT`: Minimum observations for strong initialization (default: 20)

### FSRS Initialization Parameters
- `FSRS_STABILITY_FROM_INTERVAL_MODE`: "monotonic_log" | "linear" | "sqrt" (default: "monotonic_log")
- `FSRS_DIFFICULTY_FROM_ERROR_RATE_MODE`: "linear_clip" | "sigmoid" (default: "linear_clip")
- `FSRS_DIFFICULTY_MIN`: Minimum difficulty (default: 0.05)
- `FSRS_DIFFICULTY_MAX`: Maximum difficulty (default: 0.95)

### Bandit Initialization Parameters
- `BANDIT_PRIOR_FROM_MASTERY_MODE`: "beta_from_mastery" (default: "beta_from_mastery")
- `BANDIT_PRIOR_STRENGTH_MIN`: Minimum prior strength (default: 5)
- `BANDIT_PRIOR_STRENGTH_MAX`: Maximum prior strength (default: 50)

---

## Mastery Bridging

### v0 Mastery Computation (from aggregates)

**Function:** `compute_v0_mastery_from_aggregates(attempts_total, correct_total, last_attempt_at, now, cfg)`

**Algorithm:**
1. If `attempts_total < MASTERY_MIN_ATTEMPTS_FOR_CONFIDENCE`:
   - Return `mastery_score = 0.5` (neutral)
2. Compute accuracy: `p = correct_total / attempts_total`
3. Compute recency: `delta_days = (now - last_attempt_at).days`
   - `r = exp(-delta_days / MASTERY_RECENCY_TAU_DAYS)`
4. Compute raw mastery: `mastery_raw = r * p + (1 - r) * 0.5`
5. Clip: `mastery_score = clip(mastery_raw, MASTERY_FLOOR, MASTERY_CEIL)`

**Output:** `mastery_score` (float 0..1)

### BKT Initialization (from mastery_score)

**Function:** `init_bkt_from_mastery(mastery_score, p_prior, attempts_total, cfg)`

**Modes:**

**1. "direct" mode:**
- `bkt_p_mastered = clip(mastery_score, 0.1, 0.9)`
- `bkt_state_json = {"p_L0": bkt_p_mastered, "n_attempts": attempts_total, "initialized_from_mastery": true}`

**2. "shrink_to_prior" mode:**
- `bkt_p_mastered = (1 - BKT_PRIOR_SHRINK_ALPHA) * mastery_score + BKT_PRIOR_SHRINK_ALPHA * p_prior`
- If `attempts_total >= BKT_MIN_OBS_FOR_STRONG_INIT`:
  - Use stronger initialization (less shrinkage)
- `bkt_state_json = {"p_L0": bkt_p_mastered, "n_attempts": attempts_total, "shrinkage_alpha": BKT_PRIOR_SHRINK_ALPHA, "initialized_from_mastery": true}`

**Output:** `(bkt_p_mastered, bkt_state_json)`

---

## Revision Bridging

### v1 → v0 Revision Bridge

**Function:** `v1_to_v0_revision_bridge(user_revision_state, user_theme_stats, cfg, now)`

**Rules:**
1. **Preserve `due_at`** (unless invalid per `DUE_AT_PRESERVATION_MODE`)
2. If `v0_interval_days` is NULL:
   - If `due_at` exists and `last_review_at` exists:
     - `interval_days = (due_at - last_review_at).days`
   - Else if `due_at` exists:
     - `interval_days = max(1, (due_at - now).days)`
   - Else if `last_attempt_at` exists:
     - `interval_days = max(1, (now - last_attempt_at).days)`
   - Else:
     - `interval_days = 1` (default)
   - Bin to nearest: `v0_interval_days = nearest_bin(interval_days, V0_INTERVAL_BINS_DAYS)`
3. If `v0_stage` is NULL:
   - `v0_stage = stage_from_interval(v0_interval_days, V0_INTERVAL_BINS_DAYS, V0_STAGE_MAX)`

**Output:** Updated `user_revision_state` with v0 fields populated

### v0 → v1 Revision Bridge

**Function:** `v0_to_v1_revision_bridge(user_revision_state, user_theme_stats, cfg, now)`

**Rules:**
1. **Preserve `due_at`** (unless invalid)
2. If `stability` is NULL and `v0_interval_days` exists:
   - Compute stability using `FSRS_STABILITY_FROM_INTERVAL_MODE`:
     - **"monotonic_log"**: `stability = log(1 + v0_interval_days) * (I_max / log(1 + I_max))` where `I_max = max(V0_INTERVAL_BINS_DAYS)`
     - **"linear"**: `stability = v0_interval_days * (I_max / max(V0_INTERVAL_BINS_DAYS))`
     - **"sqrt"**: `stability = sqrt(v0_interval_days) * (I_max / sqrt(max(V0_INTERVAL_BINS_DAYS)))`
   - Clip stability to reasonable bounds (e.g., 1.0 to 365.0)
3. If `difficulty` is NULL and `user_theme_stats` exists:
   - Compute error rate: `err_rate = 1 - (correct_total / attempts_total)` if `attempts_total > 0` else `0.5`
   - Compute difficulty using `FSRS_DIFFICULTY_FROM_ERROR_RATE_MODE`:
     - **"linear_clip"**: `difficulty = clip(err_rate, FSRS_DIFFICULTY_MIN, FSRS_DIFFICULTY_MAX)`
     - **"sigmoid"**: `difficulty = sigmoid(err_rate) * (FSRS_DIFFICULTY_MAX - FSRS_DIFFICULTY_MIN) + FSRS_DIFFICULTY_MIN`
4. If `due_at` is NULL and `v0_interval_days` exists:
   - `due_at = now + timedelta(days=v0_interval_days)`

**Output:** Updated `user_revision_state` with FSRS fields populated

### Helper Functions

**`nearest_bin(days, bins)`** → Returns the bin value closest to `days`

**`stage_from_interval(interval_days, bins, stage_max)`** → Returns stage number (1..stage_max) based on which bin contains `interval_days`

---

## Bandit Initialization

### Beta Prior from Mastery

**Function:** `init_bandit_beta_from_mastery(mastery_score, attempts_total, cfg)`

**Algorithm:**
1. Compute strength: `S = clip(attempts_total, BANDIT_PRIOR_STRENGTH_MIN, BANDIT_PRIOR_STRENGTH_MAX)`
2. Compute alpha: `alpha = 1 + mastery_score * S`
3. Compute beta: `beta = 1 + (1 - mastery_score) * S`

**Output:** `(alpha, beta)` tuple

---

## Bridge Execution Rules

### Idempotence
- Bridge operations are idempotent: running twice produces identical results
- Only populate NULL/missing fields
- Never overwrite existing non-NULL values unless explicitly invalid

### Invalid State Handling

**Invalid `due_at`:**
- NULL → invalid
- Far in past (> 1 year ago) → invalid if `DUE_AT_PRESERVATION_MODE == "preserve_if_reasonable"`
- Far in future (> 1 year ahead) → invalid if `DUE_AT_PRESERVATION_MODE == "preserve_if_reasonable"`

**Invalid mastery:**
- NULL → compute from aggregates
- Out of bounds (< 0 or > 1) → clip to [MASTERY_FLOOR, MASTERY_CEIL]

### Bridge Order (v1 → v0)
1. Ensure `mastery_score` exists (compute if missing)
2. Preserve `due_at` (unless invalid)
3. Populate `v0_interval_days` and `v0_stage` if missing

### Bridge Order (v0 → v1)
1. Initialize BKT from `mastery_score` if missing
2. Preserve `due_at` (unless invalid)
3. Initialize FSRS fields from v0 state if missing
4. Initialize bandit priors from `mastery_score` if missing

---

## Testing Requirements

All bridge functions must be:
- **Pure**: No side effects (except DB writes in bridge_runner)
- **Deterministic**: Same inputs → same outputs
- **Idempotent**: Running twice → same result
- **Config-driven**: All parameters from `algo_bridge_config`

---

## Version History

- **v1.0** (2026-01-25): Initial specification
