# Algorithm Kill Switch Implementation Summary

**Status:** 🚧 In Progress  
**Date:** 2026-01-25  
**Task:** Reversible Kill Switch + Seamless Fallback (v1 ⇄ v0)

---

## ✅ Completed Components

### 1. Database Schema
- ✅ Migration: `024_add_algo_runtime_kill_switch.py`
- ✅ Tables created:
  - `algo_runtime_config` - Singleton runtime configuration
  - `algo_switch_event` - Immutable audit trail
  - `user_theme_stats` - Canonical theme aggregates
  - `user_revision_state` - Canonical revision state (v0/v1 compatible)
  - `user_mastery_state` - Canonical mastery state (v0/v1 compatible)
  - `algo_state_bridge` - Bridge job tracking
- ✅ Added `algo_profile_at_start` and `algo_overrides_at_start` to `test_sessions`

### 2. Database Models
- ✅ `backend/app/models/algo_runtime.py` - All runtime models
- ✅ Updated `backend/app/models/session.py` - Added snapshot fields

### 3. Runtime Helpers
- ✅ `backend/app/learning_engine/runtime.py` - Core runtime helpers:
  - `get_algo_runtime_config()` - Get current config
  - `get_algo_version(module_name)` - Get version for module (respects overrides)
  - `is_safe_mode_freeze_updates()` - Check freeze mode
  - `get_session_algo_config()` - Get config for session (uses snapshot)

---

## 🚧 Remaining Work

### 4. Router Layer
- [ ] Create `backend/app/learning_engine/router.py`
- [ ] Implement routing functions:
  - `compute_mastery()` - Routes to v0 or v1
  - `plan_revision()` - Routes to v0 or v1
  - `adaptive_next()` - Routes to v0 or v1
  - `classify_mistakes()` - Routes to v0 or v1
- [ ] All must read/write canonical state tables

### 5. Adapters (v1⇄v0 Bridge)
- [ ] Create `backend/app/learning_engine/bridge/` module
- [ ] Implement `v1_to_v0_bridge()` - Convert v1 state to v0
- [ ] Implement `v0_to_v1_bridge()` - Convert v0 state to v1
- [ ] Lazy bridging (on first request after switch)
- [ ] Idempotent operations

### 6. Admin API Endpoints
- [ ] `GET /v1/admin/algorithms/runtime` - Get current config
- [ ] `POST /v1/admin/algorithms/runtime/switch` - Switch profile
- [ ] `POST /v1/admin/algorithms/runtime/freeze_updates` - Emergency freeze
- [ ] `POST /v1/admin/algorithms/runtime/unfreeze_updates` - Unfreeze
- [ ] `GET /v1/admin/algorithms/bridge/status` - Bridge status

### 7. Session Snapshot Logic
- [ ] Update session creation to snapshot algo config
- [ ] Update session submit to use snapshot config
- [ ] Ensure no mid-session algorithm switching

### 8. Bridge Backfill Job
- [ ] Create `backend/app/jobs/algo_bridge_backfill.py`
- [ ] Batch process active users
- [ ] Convert state between profiles
- [ ] Track progress in `algo_state_bridge`

### 9. Integration Points
- [ ] Update mastery service to use router
- [ ] Update revision service to use router
- [ ] Update adaptive service to use router
- [ ] Update mistakes service to use router
- [ ] Update difficulty service to use router

### 10. Tests
- [ ] Session continuity tests
- [ ] Bridging idempotence tests
- [ ] No cold start tests
- [ ] RBAC tests
- [ ] Safe mode tests

### 11. Documentation
- [ ] Update `docs/algorithms.md`
- [ ] Update `docs/runbook.md`
- [ ] Update `docs/observability.md`

---

## 📋 Implementation Notes

### Canonical State Strategy

**Key Principle:** Both v0 and v1 read/write the same canonical tables, enabling seamless transitions.

**Tables:**
- `user_theme_stats` - Aggregates (attempts, correct, last_attempt_at)
- `user_mastery_state` - Mastery score (0..1) + model-specific state
- `user_revision_state` - Due dates + v0/v1 state fields

**Migration Strategy:**
- Existing `user_theme_mastery` can populate `user_mastery_state.mastery_score`
- Existing `revision_queue` can populate `user_revision_state.due_at`
- Incremental updates maintain canonical state

### Session Snapshot Rule

**Critical:** Sessions must use the algorithm profile captured at creation time.

**Implementation:**
1. When session is created, snapshot current `algo_runtime_config`
2. Store `algo_profile_at_start` and `algo_overrides_at_start` in session
3. All learning updates during session use snapshot config
4. New sessions after switch use new config

### Bridge Strategy

**Lazy + Batch:**
- Lazy: First request after switch triggers per-user bridge
- Batch: Optional backfill job processes all active users
- Idempotent: Running bridge twice produces same result

**Bridge Logic:**
- v1→v0: Extract canonical values, derive v0 state
- v0→v1: Initialize v1 state from canonical values

---

## 🔗 Related Files

**Database:**
- `backend/alembic/versions/024_add_algo_runtime_kill_switch.py`
- `backend/app/models/algo_runtime.py`
- `backend/app/models/session.py` (updated)

**Runtime:**
- `backend/app/learning_engine/runtime.py`

**To Be Created:**
- `backend/app/learning_engine/router.py`
- `backend/app/learning_engine/bridge/`
- `backend/app/api/v1/endpoints/admin_algorithms.py`
- `backend/app/jobs/algo_bridge_backfill.py`

---

## ⚠️ Critical Requirements

1. **No Mid-Session Switching** - Sessions use snapshot config
2. **No Cold Start** - State preserved across switches
3. **Reversible** - Can switch back and forth
4. **Audited** - All switches logged
5. **Safe Mode** - Emergency freeze capability
