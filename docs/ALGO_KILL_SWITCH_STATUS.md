# Algorithm Kill Switch Implementation Status

**Date:** 2026-01-25  
**Status:** 🚧 Core Infrastructure Complete, Integration In Progress

---

## ✅ Completed Components

### 1. Database Schema ✅
- ✅ Migration: `024_add_algo_runtime_kill_switch.py`
- ✅ Tables:
  - `algo_runtime_config` - Singleton runtime configuration
  - `algo_switch_event` - Immutable audit trail
  - `user_theme_stats` - Canonical theme aggregates
  - `user_revision_state` - Canonical revision state (v0/v1 compatible)
  - `user_mastery_state` - Canonical mastery state (v0/v1 compatible)
  - `algo_state_bridge` - Bridge job tracking
- ✅ Added `algo_profile_at_start` and `algo_overrides_at_start` to `test_sessions`

### 2. Database Models ✅
- ✅ `backend/app/models/algo_runtime.py` - All runtime models
- ✅ Updated `backend/app/models/session.py` - Added snapshot fields
- ✅ Models exported in `__init__.py`

### 3. Runtime Helpers ✅
- ✅ `backend/app/learning_engine/runtime.py`:
  - `get_algo_runtime_config()` - Get current config
  - `get_algo_version(module_name)` - Get version for module
  - `is_safe_mode_freeze_updates()` - Check freeze mode
  - `get_session_algo_config()` - Get config for session (uses snapshot)

### 4. Router Layer ✅
- ✅ `backend/app/learning_engine/router.py`:
  - `compute_mastery()` - Routes to v0 or v1
  - `plan_revision()` - Routes to v0 or v1
  - `adaptive_next()` - Routes to v0 or v1
  - `classify_mistakes()` - Routes to v0 or v1
- ✅ All respect session snapshot and safe mode

### 5. Bridge Adapters ✅
- ✅ `backend/app/learning_engine/bridge/adapters.py`:
  - `bridge_v1_to_v0()` - Convert v1 state to v0
  - `bridge_v0_to_v1()` - Convert v0 state to v1
- ✅ Idempotent operations
- ✅ Lazy bridging support

### 6. Admin API Endpoints ✅
- ✅ `backend/app/api/v1/endpoints/admin_algorithms.py`:
  - `GET /v1/admin/algorithms/runtime` - Get current config
  - `POST /v1/admin/algorithms/runtime/switch` - Switch profile
  - `POST /v1/admin/algorithms/runtime/freeze_updates` - Emergency freeze
  - `POST /v1/admin/algorithms/runtime/unfreeze_updates` - Unfreeze
  - `GET /v1/admin/algorithms/bridge/status` - Bridge status
- ✅ Router included in main API router

### 7. Session Snapshot Logic ✅
- ✅ Session creation snapshots algo config
- ✅ Session submit uses snapshot config
- ✅ No mid-session algorithm switching

---

## 🚧 Remaining Integration Work

### 8. Wire Router into Services
- [ ] Update mastery service to use `router.compute_mastery()`
- [ ] Update revision service to use `router.plan_revision()`
- [ ] Update adaptive service to use `router.adaptive_next()`
- [ ] Update mistakes service to use `router.classify_mistakes()`
- [ ] Update difficulty service to check runtime config

### 9. Canonical State Maintenance
- [ ] Create job to maintain `user_theme_stats` from `attempt_events`
- [ ] Create job to sync `user_mastery_state` from `user_theme_mastery`
- [ ] Create job to sync `user_revision_state` from `revision_queue`

### 10. Bridge Backfill Job
- [ ] Create `backend/app/jobs/algo_bridge_backfill.py`
- [ ] Batch process active users
- [ ] Integrate with job system

### 11. Lazy Bridging Integration
- [ ] Add lazy bridge trigger in router functions
- [ ] Check bridge status before routing
- [ ] Auto-trigger bridge on first request after switch

### 12. Tests
- [ ] Session continuity tests
- [ ] Bridging idempotence tests
- [ ] No cold start tests
- [ ] RBAC tests
- [ ] Safe mode tests

### 13. Documentation
- [ ] Update `docs/algorithms.md`
- [ ] Update `docs/runbook.md`
- [ ] Update `docs/observability.md`

---

## 📋 Key Implementation Details

### Session Snapshot Rule

**Critical:** Sessions use the algorithm profile captured at creation time.

**Implementation:**
1. ✅ `create_session()` snapshots current `algo_runtime_config`
2. ✅ Stores `algo_profile_at_start` and `algo_overrides_at_start`
3. ✅ `submit_session()` uses snapshot config for learning updates
4. ✅ New sessions after switch use new config

### Canonical State Strategy

**Principle:** Both v0 and v1 read/write the same canonical tables.

**Tables:**
- `user_theme_stats` - Aggregates (attempts, correct, last_attempt_at)
- `user_mastery_state` - Mastery score (0..1) + model-specific state
- `user_revision_state` - Due dates + v0/v1 state fields

**Migration:**
- Existing tables can populate canonical state
- Incremental updates maintain canonical state

### Bridge Strategy

**Lazy + Batch:**
- Lazy: First request after switch triggers per-user bridge
- Batch: Optional backfill job processes all active users
- Idempotent: Running bridge twice produces same result

---

## 🔗 Files Created/Modified

**Database:**
- `backend/alembic/versions/024_add_algo_runtime_kill_switch.py`
- `backend/app/models/algo_runtime.py`
- `backend/app/models/session.py` (updated)

**Runtime:**
- `backend/app/learning_engine/runtime.py`
- `backend/app/learning_engine/router.py`
- `backend/app/learning_engine/bridge/adapters.py`

**API:**
- `backend/app/api/v1/endpoints/admin_algorithms.py`
- `backend/app/api/v1/router.py` (updated)
- `backend/app/api/v1/endpoints/sessions.py` (updated)

**Services:**
- `backend/app/services/session_engine.py` (updated)

---

## ⚠️ Critical Next Steps

1. **Wire Router into Services** - Replace direct v0/v1 calls with router
2. **Canonical State Maintenance** - Ensure canonical tables stay in sync
3. **Lazy Bridging** - Auto-trigger bridge on first request after switch
4. **Testing** - Comprehensive test coverage

---

## 🎯 Acceptance Criteria Status

- ✅ Admin can toggle V1_PRIMARY ⇄ V0_FALLBACK instantly
- ✅ Active sessions are not affected (session snapshot rule)
- ⏳ Students do not experience "reset" (bridging needed)
- ⏳ Both engines read/write canonical state (integration needed)
- ✅ All toggles are audited and reversible
- ⏳ Tests pass (pending)
