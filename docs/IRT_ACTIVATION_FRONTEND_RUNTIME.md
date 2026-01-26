# IRT Activation Frontend UI & Runtime Integration

**Status:** ✅ Complete  
**Date:** 2026-01-25  
**Task:** Frontend UI and Runtime Integration for IRT Activation

---

## ✅ Completed Components

### 1. Frontend API Routes
Created BFF (Backend for Frontend) routes for all activation endpoints:

- ✅ `frontend/app/api/admin/irt/activation/evaluate/route.ts` - Evaluate activation gates
- ✅ `frontend/app/api/admin/irt/activation/activate/route.ts` - Activate IRT
- ✅ `frontend/app/api/admin/irt/activation/deactivate/route.ts` - Deactivate IRT (kill-switch)
- ✅ `frontend/app/api/admin/irt/activation/status/route.ts` - Get activation status

All routes use `backendFetch` from `@/lib/server/backendClient` to proxy requests to the backend with proper authentication.

### 2. Frontend UI Component
Created comprehensive activation management page:

- ✅ `frontend/app/admin/irt/activation/page.tsx`
- Features:
  - Current status display (flags, scope, model, shadow)
  - Latest decision summary (eligible/not eligible)
  - Gate evaluation interface (enter run ID, evaluate)
  - Evaluation results modal (shows all 6 gates with pass/fail)
  - Activate button (disabled unless eligible)
  - Deactivate button (always enabled as kill-switch)
  - Recent activation events audit trail
  - Real-time status refresh

### 3. Navigation Integration
- ✅ Added "Activation Management" button to IRT shadow page
- ✅ Links to `/admin/irt/activation`

### 4. Runtime Integration - Selection Module
- ✅ Wired `is_irt_active()` and `get_irt_scope()` into `backend/app/learning_engine/adaptive/service.py`
- ✅ Checks IRT activation status before selection
- ✅ Logs when IRT would be used (but falls back to baseline since IRT selection not yet implemented)
- ✅ Ready for IRT selection module integration

### 5. Runtime Integration - Scoring/Difficulty Module
- ✅ Wired `is_irt_active()` and `get_irt_scope()` into `backend/app/learning_engine/difficulty/service.py`
- ✅ Checks IRT activation status before scoring/difficulty updates
- ✅ Logs when IRT would be used (but falls back to baseline since IRT scoring not yet implemented)
- ✅ Ready for IRT scoring module integration

---

## 🎨 UI Features

### Status Display
- Shows current activation flags (active, scope, model, shadow)
- Displays latest decision eligibility status
- Color-coded badges for status indicators

### Gate Evaluation
- Input field for calibration run ID
- Evaluate button triggers gate evaluation
- Modal displays all 6 gates with:
  - Pass/fail status (visual indicators)
  - Gate notes/explanation
  - Recommended scope and model

### Activation Actions
- **Activate**: Only enabled when `eligible=true`
  - Requires reason input
  - Uses recommended scope/model from evaluation
  - Shows success/error feedback
- **Deactivate**: Always enabled (kill-switch)
  - Requires confirmation
  - Requires reason input
  - Immediately disables IRT

### Audit Trail
- Table of recent activation events
- Shows event type, timestamp, reason
- Last 10 events displayed

---

## 🔧 Runtime Integration Details

### Selection Module (`adaptive/service.py`)

```python
# Check if IRT is active for selection
irt_active = await is_irt_active(db)
irt_scope = await get_irt_scope(db)

# If IRT is active and scope includes selection, use IRT-based selection
if irt_active and irt_scope in ("selection_only", "selection_and_scoring"):
    logger.info("IRT is active, but IRT selection not yet implemented. Falling back to baseline.")
    # TODO: Call IRT selection when implemented
```

**Behavior:**
- Checks IRT activation before every selection call
- Falls back to baseline (adaptive v0) if IRT not active or not implemented
- Logs when IRT would be used (for monitoring)

### Scoring/Difficulty Module (`difficulty/service.py`)

```python
# Check if IRT is active for scoring
irt_active = await is_irt_active(db)
irt_scope = await get_irt_scope(db)

# If IRT is active and scope includes scoring, use IRT-based scoring
if irt_active and irt_scope in ("scoring_only", "selection_and_scoring"):
    logger.info("IRT is active, but IRT scoring not yet implemented. Falling back to baseline.")
    # TODO: Call IRT scoring when implemented
```

**Behavior:**
- Checks IRT activation before every difficulty update
- Falls back to baseline (ELO difficulty) if IRT not active or not implemented
- Logs when IRT would be used (for monitoring)

---

## 📋 Usage Flow

### 1. Evaluate Activation Gates

1. Navigate to `/admin/irt/activation`
2. Enter calibration run ID (UUID)
3. Click "Evaluate"
4. Review gate results in modal:
   - All 6 gates must pass for eligibility
   - See detailed notes for each gate
   - Check recommended scope and model

### 2. Activate IRT (If Eligible)

1. After evaluation shows `eligible=true`:
2. Click "Activate" button (now enabled)
3. Enter reason for activation
4. IRT is activated with recommended scope/model
5. Status updates immediately

### 3. Monitor Status

- View current flags on status card
- Check latest decision eligibility
- Review recent activation events

### 4. Deactivate (Kill-Switch)

1. Click "Deactivate" button (always enabled)
2. Confirm deactivation
3. Enter reason
4. IRT immediately disabled
5. All student-facing endpoints fall back to baseline

---

## 🔗 Integration Points

### When IRT Selection is Implemented

Replace the TODO in `adaptive/service.py`:

```python
if irt_active and irt_scope in ("selection_only", "selection_and_scoring"):
    question_ids = await irt_select_questions(
        db,
        user_id,
        year=year,
        block_ids=block_ids,
        theme_ids=theme_ids,
        count=count,
        mode=mode,
    )
    return {"question_ids": question_ids, ...}
```

### When IRT Scoring is Implemented

Replace the TODO in `difficulty/service.py`:

```python
if irt_active and irt_scope in ("scoring_only", "selection_and_scoring"):
    irt_score = await irt_compute_score(
        db,
        user_id=user_id,
        question_id=question_id,
        score=score,
    )
    # Use IRT score instead of ELO
```

---

## ✅ Acceptance Criteria Status

- ✅ Frontend UI for activation management
- ✅ Show current flag state
- ✅ Show latest run + decision summary with gate pass/fail
- ✅ Buttons: Evaluate, Activate (disabled unless eligible), Deactivate (always enabled)
- ✅ Show last 10 activation events
- ✅ Runtime helpers wired into selection modules
- ✅ Runtime helpers wired into scoring modules
- ✅ Baseline behavior unchanged when inactive
- ⏳ IRT selection/scoring modules (to be implemented separately)

---

## 📝 Notes

- Runtime integration is **non-breaking**: Always falls back to baseline if IRT not active
- Logging added to track when IRT would be used (for monitoring)
- Infrastructure ready for IRT selection/scoring module integration
- Frontend UI provides full activation management workflow
- All actions are audited and logged

---

## 🔗 Related Files

### Frontend
- `frontend/app/admin/irt/activation/page.tsx` - Activation management UI
- `frontend/app/api/admin/irt/activation/*/route.ts` - API route handlers
- `frontend/app/admin/irt/page.tsx` - IRT shadow page (updated with link)

### Backend
- `backend/app/learning_engine/irt/runtime.py` - Runtime helpers
- `backend/app/learning_engine/adaptive/service.py` - Selection integration
- `backend/app/learning_engine/difficulty/service.py` - Scoring integration

---

## 🚀 Next Steps

1. **Implement IRT Selection Module**: Create IRT-based question selection
2. **Implement IRT Scoring Module**: Create IRT-based scoring/difficulty updates
3. **Integration Testing**: Test full activation workflow end-to-end
4. **Monitoring**: Add metrics/telemetry for IRT activation state
