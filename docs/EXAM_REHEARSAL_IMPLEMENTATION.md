# Exam-Day Rehearsal Implementation Summary

## Overview

This document summarizes the implementation of the exam-day rehearsal framework, including load testing scripts, failure injection procedures, verification tools, and documentation.

## Implementation Date

January 2026

## Components

### 1. Load Testing Scripts (k6)

**Location**: `infra/scripts/exam-rehearsal/`

#### `load-test-sessions.js`
- **Purpose**: Simulates session creation burst (300-400 users within 5 minutes)
- **Usage**: `k6 run --vus 400 --duration 5m load-test-sessions.js`
- **Metrics**: Session creation success rate, p50/p95/p99 latency

#### `load-test-answers.js`
- **Purpose**: Simulates steady answer submissions (300 users over 30 minutes)
- **Usage**: `k6 run --vus 300 --duration 30m load-test-answers.js`
- **Metrics**: Answer submission success rate, latency

#### `load-test-submit.js`
- **Purpose**: Simulates final submit spike (400 users in last 10 minutes)
- **Usage**: `k6 run --vus 400 --duration 10m load-test-submit.js`
- **Metrics**: Submit success rate, double-submit handling (idempotency)

### 2. Failure Injection Scripts

#### `failure-injection.sh`
- **Purpose**: Injects various failure scenarios during load testing
- **Scenarios**:
  - Redis failure (60 seconds)
  - Backend worker restart
  - Full backend restart
  - Network delay (experimental)
- **Usage**: `./failure-injection.sh <scenario>`

### 3. Verification Scripts

#### `verify-exam-mode.sh`
- **Purpose**: Verifies `EXAM_MODE=true` disables heavy operations
- **Checks**:
  - EXAM_MODE environment variable
  - Background job processes
  - EXAM_MODE usage in logs
  - Critical endpoints accessibility

#### `verify-data-integrity.sh`
- **Purpose**: Runs SQL checks to verify no data loss or corruption
- **Checks**:
  - Orphaned answers
  - Duplicate submits
  - Missing answers
  - Unscored sessions
  - Answer/question mismatches
  - Orphaned events
  - Inconsistent status
  - Duplicate mastery updates

#### `capture-metrics.sh`
- **Purpose**: Captures observability metrics during/after rehearsal
- **Captures**:
  - Database connection pool usage
  - Slow queries
  - Slow requests
  - Error rates
  - Redis statistics
  - Container resource usage
  - Traefik metrics
  - Session statistics

### 4. Orchestration

#### `run-rehearsal.sh`
- **Purpose**: Orchestrates all phases of the rehearsal
- **Phases**:
  1. Pre-Exam Freeze (EXAM_MODE verification)
  2. Load Generation (manual k6 runs)
  3. Failure Injection (interactive)
  4. Data Integrity Verification
  5. Observability Review
  6. Recovery Drill
- **Output**: Generates rehearsal report

### 5. Documentation

#### `docs/EXAM_DAY_RUNBOOK.md`
- **Purpose**: Step-by-step procedures for exam day operations
- **Sections**:
  - Pre-Exam Checklist (24 hours before)
  - Exam-Day Freeze (1 hour before)
  - During Exam (monitoring, common issues)
  - Post-Exam (data integrity, disable exam mode)
  - Emergency Procedures
  - Recovery Verification

#### `docs/EXAM_REHEARSAL_REPORT_TEMPLATE.md`
- **Purpose**: Template for documenting rehearsal results
- **Sections**:
  - Executive Summary
  - Phase-by-phase results
  - Risk Register
  - GO/NO-GO Checklist
  - Sign-Off

#### `infra/scripts/exam-rehearsal/README.md`
- **Purpose**: Usage guide for rehearsal scripts
- **Contents**:
  - Prerequisites
  - Script descriptions
  - Workflow
  - Troubleshooting

## EXAM_MODE Implementation

### Configuration

**Setting**: `EXAM_MODE` (boolean, default: `false`)
- **Location**: `backend/app/core/config.py`
- **Environment Variable**: `EXAM_MODE=true/false`

### Protected Operations

The following operations are blocked when `EXAM_MODE=true`:

1. **Background Jobs** (`backend/app/jobs/run.py`):
   - `revision_queue_regen` - Revision queue regeneration
   - `warehouse_incremental_export` - Warehouse exports
   - Jobs exit with status 0 (skipped)

2. **Admin Bulk Operations**:
   - **BKT Recompute** (`backend/app/api/v1/endpoints/bkt.py`):
     - POST `/v1/admin/bkt/recompute` - Returns 403
   - **Rank Runs** (`backend/app/api/v1/endpoints/admin_rank.py`):
     - POST `/v1/admin/rank/runs` - Returns 403
   - **IRT Calibration** (`backend/app/api/v1/endpoints/admin_irt.py`):
     - POST `/v1/admin/irt/runs` - Returns 403
   - **Email Outbox Drain** (`backend/app/api/v1/endpoints/admin_email.py`):
     - POST `/v1/admin/email/outbox/drain` - Returns 403
   - **Notification Broadcast** (`backend/app/api/v1/endpoints/admin_notifications.py`):
     - POST `/v1/admin/notifications/broadcast` - Returns 403
   - **Bulk Question Import** (`backend/app/api/v1/endpoints/admin_import.py`):
     - POST `/v1/admin/import/questions` - Returns 403 (dry_run allowed)

### Allowed Operations

The following operations continue to work during `EXAM_MODE=true`:
- Session creation
- Answer submission
- Session submit
- Revision reads
- User authentication
- Health/readiness checks

## Files Modified

### Application Code
1. `backend/app/core/config.py` - Added `EXAM_MODE` setting (already present)
2. `backend/app/jobs/run.py` - Added EXAM_MODE check before running jobs
3. `backend/app/api/v1/endpoints/bkt.py` - Added EXAM_MODE check to recompute endpoint
4. `backend/app/api/v1/endpoints/admin_rank.py` - Added EXAM_MODE check to rank runs
5. `backend/app/api/v1/endpoints/admin_irt.py` - Added EXAM_MODE check to IRT runs
6. `backend/app/api/v1/endpoints/admin_email.py` - Added EXAM_MODE check to email drain
7. `backend/app/api/v1/endpoints/admin_notifications.py` - Added EXAM_MODE check to broadcast, fixed imports
8. `backend/app/api/v1/endpoints/admin_import.py` - Added EXAM_MODE check to bulk import
9. `backend/app/services/session_engine.py` - Made submit idempotent (already done)
10. `backend/app/api/v1/endpoints/sessions.py` - Updated submit endpoint for idempotency (already done)

### Scripts
11. `infra/scripts/exam-rehearsal/load-test-sessions.js` - k6 load test for sessions
12. `infra/scripts/exam-rehearsal/load-test-answers.js` - k6 load test for answers
13. `infra/scripts/exam-rehearsal/load-test-submit.js` - k6 load test for submits
14. `infra/scripts/exam-rehearsal/failure-injection.sh` - Failure injection script
15. `infra/scripts/exam-rehearsal/verify-data-integrity.sql` - SQL verification queries
16. `infra/scripts/exam-rehearsal/verify-data-integrity.sh` - Data integrity verification script
17. `infra/scripts/exam-rehearsal/capture-metrics.sh` - Metrics capture script
18. `infra/scripts/exam-rehearsal/verify-exam-mode.sh` - EXAM_MODE verification script
19. `infra/scripts/exam-rehearsal/run-rehearsal.sh` - Orchestration script
20. `infra/scripts/exam-rehearsal/README.md` - Usage guide

### Documentation
21. `docs/EXAM_DAY_RUNBOOK.md` - Exam day procedures
22. `docs/EXAM_REHEARSAL_REPORT_TEMPLATE.md` - Report template
23. `docs/EXAM_REHEARSAL_IMPLEMENTATION.md` - This file

## Usage

### Quick Start

1. **Prepare Staging Environment**:
   ```bash
   # Ensure staging is running
   docker compose -f infra/docker/compose/docker-compose.prod.yml ps
   ```

2. **Get Authentication Token**:
   ```bash
   export AUTH_TOKEN="your-jwt-token"
   export API_URL="https://api-staging.example.com"
   ```

3. **Run Orchestrated Rehearsal**:
   ```bash
   cd infra/scripts/exam-rehearsal
   ./run-rehearsal.sh staging "$API_URL" "$AUTH_TOKEN"
   ```

4. **Or Run Individual Tests**:
   ```bash
   # Session creation
   k6 run --vus 400 --duration 5m load-test-sessions.js
   
   # Answer submissions
   k6 run --vus 300 --duration 30m load-test-answers.js
   
   # Submit spike
   export SESSION_IDS="id1,id2,id3,..."
   k6 run --vus 400 --duration 10m load-test-submit.js
   ```

### Verification

```bash
# Verify EXAM_MODE
./verify-exam-mode.sh staging "$API_URL"

# Verify data integrity
./verify-data-integrity.sh staging

# Capture metrics
./capture-metrics.sh ./rehearsal-metrics
```

## Expected Results

### Performance Targets
- **p95 latency**: < 500ms (API endpoints)
- **Error rate**: < 1%
- **Database pool**: < 80% usage
- **Zero data loss**: All sessions and answers preserved

### Failure Scenarios
- **Redis failure**: Graceful degradation, no crashes
- **Backend restart**: Seamless failover, no lost data
- **Network delay**: Timeouts protect backend, clients retry

### Data Integrity
- Zero orphaned answers
- Zero duplicate submits
- Zero missing answers
- All sessions properly scored

## GO/NO-GO Criteria

### GO if ALL true:
- [ ] Zero data loss verified
- [ ] No corrupted sessions
- [ ] p95 latency acceptable (< 500ms)
- [ ] Recovery tested and successful
- [ ] Logs sufficient for audit
- [ ] EXAM_MODE verified
- [ ] Failure scenarios handled gracefully

### NO-GO if ANY:
- [ ] Lost answers
- [ ] Duplicate submits
- [ ] Silent failures
- [ ] Manual DB fixes needed
- [ ] p95 latency > 500ms consistently
- [ ] Error rate > 1%

## Next Steps

1. **Run Full Rehearsal**:
   - Execute on staging environment
   - Document all findings
   - Address any blockers

2. **Update Runbook**:
   - Add lessons learned
   - Update procedures based on findings
   - Refine emergency contacts

3. **Production Readiness**:
   - Complete GO/NO-GO checklist
   - Obtain sign-off
   - Schedule exam day

## Related Documentation

- `docs/EXAM_DAY_RUNBOOK.md` - Exam day procedures
- `docs/EXAM_REHEARSAL_REPORT_TEMPLATE.md` - Report template
- `docs/PRODUCTION_HARDENING_SUMMARY.md` - Performance hardening
- `docs/runbook.md` - General operations
- `infra/scripts/exam-rehearsal/README.md` - Script usage guide
