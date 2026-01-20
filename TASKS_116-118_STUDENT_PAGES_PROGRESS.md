# Tasks 116-118: Student Pages (Revision, Mistakes, Bookmarks) — IN PROGRESS

**Implementation Date:** January 21, 2026  
**Status:** Backend Complete, Frontend In Progress  
**Dependencies:** Learning Engine (101-115), Sessions (83-86), Telemetry (91-94)

---

## Progress Summary

### ✅ Backend Complete (100%)

**Completed:**
1. ✅ Revision Queue API (`GET /v1/revision/queue`, `PATCH /v1/revision/queue/{id}`)
2. ✅ Mistakes API (`GET /v1/mistakes/summary`, `GET /v1/mistakes/list`)
3. ✅ Bookmarks API (already existed from previous task)
4. ✅ Pydantic schemas for all endpoints
5. ✅ Router wiring in main API
6. ✅ Pytest tests for ownership, filters, validation

**Files Created:**
- `backend/app/schemas/revision.py` - Revision queue schemas
- `backend/app/schemas/mistakes.py` - Mistakes schemas
- `backend/app/api/v1/endpoints/revision.py` - Revision endpoints
- `backend/app/api/v1/endpoints/mistakes.py` - Mistakes endpoints
- `backend/tests/test_revision_mistakes_api.py` - Comprehensive tests

**Files Modified:**
- `backend/app/api/v1/router.py` - Added mistakes router

### 🔄 Frontend In Progress (40%)

**Completed:**
1. ✅ `frontend/lib/api/revisionApi.ts` - Revision API client
2. ✅ `frontend/lib/api/mistakesApi.ts` - Mistakes API client
3. ✅ Bookmarks API client (already existed)

**Remaining:**
1. ⏳ `/student/revision` page with Today/Upcoming tabs
2. ⏳ `/student/mistakes` page with filters and summary
3. ⏳ `/student/bookmarks` page with list

---

## Backend Implementation Details

### Revision Queue API

**GET /v1/revision/queue**
- Query params: `scope` (today/week), `status` (DUE/DONE/SNOOZED/SKIPPED/ALL)
- Returns list of revision items with theme/block info
- Ordered by priority_score DESC, due_date ASC
- Enforces user ownership

**PATCH /v1/revision/queue/{id}**
- Actions: DONE, SKIP, SNOOZE
- DONE: Only if due_date <= today
- SNOOZE: Updates due_date by snooze_days (1-3)
- Validates ownership and action constraints

### Mistakes API

**GET /v1/mistakes/summary**
- Query param: `range_days` (1-365, default 30)
- Returns:
  - Total wrong count
  - Counts by mistake type
  - Top 5 themes with most mistakes
  - Top 5 blocks with most mistakes

**GET /v1/mistakes/list**
- Query params: `range_days`, `block_id`, `theme_id`, `mistake_type`, `page`, `page_size`
- Returns paginated list with:
  - Question stem preview (140 chars)
  - Theme/block info
  - Evidence JSON (time_spent, changes, etc.)
- Ordered by created_at DESC

### Test Coverage

**Revision Tests:**
- ✅ Queue returns only user's items
- ✅ DONE action updates status
- ✅ Snooze days validated (1-3)

**Mistakes Tests:**
- ✅ List filtered by mistake_type
- ✅ List filtered by block_id
- ✅ List filtered by theme_id

---

## Frontend API Clients

### revisionApi.ts

```typescript
export async function getRevisionQueue(
  scope: 'today' | 'week',
  status: 'DUE' | 'DONE' | 'SNOOZED' | 'SKIPPED' | 'ALL'
): Promise<RevisionQueueListResponse>

export async function updateRevisionQueueItem(
  itemId: string,
  request: RevisionQueueUpdateRequest
): Promise<RevisionQueueItem>
```

### mistakesApi.ts

```typescript
export async function getMistakesSummary(
  rangeDays: number
): Promise<MistakesSummaryResponse>

export async function getMistakesList(params: {
  rangeDays?: number;
  blockId?: string;
  themeId?: string;
  mistakeType?: string;
  page?: number;
  pageSize?: number;
}): Promise<MistakesListResponse>
```

---

## Frontend Pages (To Be Implemented)

### Task 116: /student/revision

**UI Requirements:**
- Title: "Revision"
- Tabs: Today | Upcoming (7 days)
- List of revision items as Cards:
  - Theme name + block badge
  - Recommended count
  - Priority label (High/Medium/Low based on priority_score)
  - "Why" line from reason_json
- Actions per item:
  - Primary: "Start" → `/student/practice/build?theme_id=...&mode=revision&count=...`
  - Secondary: "Done" → PATCH action DONE
  - Optional: Snooze dropdown (1/2/3 days) → PATCH action SNOOZE
- Empty state: "No revision due today"

**Components Needed:**
- `RevisionCard.tsx` - Single revision item
- `RevisionList.tsx` - List with tabs
- `SnoozeDropdown.tsx` - Snooze action selector

### Task 117: /student/mistakes

**UI Requirements:**
- Title: "Mistakes"
- Controls:
  - Range selector (7/30/90 days)
  - Optional filters: block, mistake type
- Summary cards:
  - Total wrong
  - Top mistake type
  - Top weak theme
- List/Table:
  - Columns: Date | Block | Theme | Type | Why
  - "Why" opens popover with evidence_json
  - Button per row: "Practice this theme"
- Empty state: "No mistakes logged yet"

**Components Needed:**
- `MistakesSummary.tsx` - Summary cards
- `MistakesTable.tsx` - Paginated table
- `EvidencePopover.tsx` - Shows evidence details

### Task 118: /student/bookmarks

**UI Requirements:**
- Title: "Bookmarks"
- Table/List:
  - Question stem preview
  - Block/theme badges
  - Date saved
  - Remove button (trash icon)
- Empty state: "No bookmarks yet"

**Components Needed:**
- `BookmarksList.tsx` - List with pagination
- `BookmarkItem.tsx` - Single bookmark row

---

## Key Design Decisions

### 1. Revision Queue Ownership

**Why:** Students should only see their own revision items
**Implementation:** Filter by `user_id == current_user.id` in all queries

### 2. Snooze Validation

**Why:** Prevent abuse and ensure reasonable postponement
**Implementation:** Validate snooze_days (1-3) in Pydantic schema and endpoint

### 3. Mistakes Stem Preview

**Why:** Show context without loading full question
**Implementation:** Truncate to 140 chars with "..." suffix

### 4. Pagination for Mistakes/Bookmarks

**Why:** Large lists would be slow and overwhelming
**Implementation:** Default page_size=20, max=50

### 5. Evidence JSON in Popover

**Why:** Technical details shouldn't clutter main view
**Implementation:** Popover on "Why" column shows formatted evidence

---

## API Response Examples

### Revision Queue Item

```json
{
  "id": "uuid",
  "due_date": "2026-01-22",
  "status": "DUE",
  "priority_score": 87.5,
  "recommended_count": 15,
  "block": {"id": "uuid", "name": "Anatomy"},
  "theme": {"id": "uuid", "name": "Cardiovascular System"},
  "reason": {
    "mastery_score": 0.41,
    "mastery_band": "medium",
    "days_since_last": 6
  }
}
```

### Mistakes Summary

```json
{
  "range_days": 30,
  "total_wrong": 42,
  "counts_by_type": {
    "FAST_WRONG": 10,
    "KNOWLEDGE_GAP": 18,
    "CHANGED_ANSWER_WRONG": 8,
    "TIME_PRESSURE_WRONG": 6
  },
  "top_themes": [
    {"theme": {"id": "uuid", "name": "Inflammation"}, "wrong": 9}
  ],
  "top_blocks": [
    {"block": {"id": "uuid", "name": "Pathology"}, "wrong": 14}
  ]
}
```

### Mistake Item

```json
{
  "created_at": "2026-01-21T10:30:00Z",
  "mistake_type": "FAST_WRONG",
  "severity": 1,
  "theme": {"id": "uuid", "name": "Inflammation"},
  "block": {"id": "uuid", "name": "Pathology"},
  "question": {"id": "uuid", "stem_preview": "A 45-year-old patient presents with..."},
  "evidence": {
    "time_spent_sec": 18,
    "change_count": 0,
    "blur_count": 0,
    "rule_fired": "FAST_WRONG",
    "thresholds": {"fast_wrong_sec": 20}
  }
}
```

---

## Next Steps

### Immediate (Complete Tasks 116-118)

1. Create `/student/revision` page
   - Implement tabs (Today/Upcoming)
   - Build revision cards with actions
   - Handle Start/Done/Snooze actions
   - Add loading/empty/error states

2. Create `/student/mistakes` page
   - Implement range selector and filters
   - Build summary cards
   - Create mistakes table with pagination
   - Add evidence popover

3. Create `/student/bookmarks` page
   - Implement bookmarks list
   - Add remove action
   - Handle pagination
   - Add empty state

### Future Enhancements (Out of Scope)

- **Revision Calendar View:** Visual calendar showing due dates
- **Mistakes Trends:** Charts showing mistake patterns over time
- **Bookmark Collections:** Organize bookmarks into folders
- **Export Features:** Download mistakes/bookmarks as CSV
- **Smart Notifications:** Remind students of due revisions

---

## Files Summary

### Backend (Complete)
- `backend/app/schemas/revision.py` (80 lines)
- `backend/app/schemas/mistakes.py` (90 lines)
- `backend/app/api/v1/endpoints/revision.py` (200 lines)
- `backend/app/api/v1/endpoints/mistakes.py` (250 lines)
- `backend/tests/test_revision_mistakes_api.py` (400 lines)

### Frontend (Partial)
- `frontend/lib/api/revisionApi.ts` (70 lines) ✅
- `frontend/lib/api/mistakesApi.ts` (110 lines) ✅
- `frontend/app/student/revision/page.tsx` (pending)
- `frontend/app/student/mistakes/page.tsx` (pending)
- `frontend/app/student/bookmarks/page.tsx` (pending)

---

## Acceptance Criteria

### Backend ✅
- [x] Revision queue GET/PATCH endpoints exist
- [x] Mistakes summary/list endpoints exist
- [x] Bookmarks endpoints exist (from previous task)
- [x] Student ownership enforced
- [x] Filters work correctly
- [x] Pagination implemented
- [x] Tests pass

### Frontend ⏳
- [x] API clients created
- [ ] Revision page renders with tabs
- [ ] Revision actions work (Start/Done/Snooze)
- [ ] Mistakes page shows summary and list
- [ ] Mistakes filters work
- [ ] Bookmarks page shows list
- [ ] Loading/empty/error states consistent
- [ ] Theme consistency with existing pages

---

**Status:** Backend complete, frontend API clients complete, frontend pages pending.

**Next:** Implement the three student pages with full UI components.

---

**END OF PROGRESS SUMMARY**
