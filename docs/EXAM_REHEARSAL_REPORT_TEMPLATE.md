# Exam-Day Rehearsal Report

**Date**: [Date]
**Environment**: [staging/prod]
**API URL**: [URL]
**Conducted By**: [Name]

---

## Executive Summary

**Status**: [ ] GO  [ ] NO-GO

**Overall Assessment**: [Brief summary]

**Key Findings**:
- [Finding 1]
- [Finding 2]
- [Finding 3]

---

## Phase 1: Pre-Exam Freeze

### EXAM_MODE Verification

**EXAM_MODE Status**: [true/false]

**Background Jobs**:
- [ ] No cron jobs running
- [ ] No scheduled tasks active
- [ ] Heavy analytics disabled

**Critical Endpoints**:
- [ ] `/health` accessible
- [ ] `/v1/ready` accessible
- [ ] Session creation works
- [ ] Answer submission works

**Issues Found**: [List any issues]

---

## Phase 2: Load Generation

### Test Parameters

- **Concurrent Users**: [Number]
- **Duration**: [Duration]
- **Test Type**: [Session creation / Answer submission / Submit spike]

### Results

**Session Creation**:
- Total requests: [Number]
- Success rate: [Percentage]
- p50 latency: [ms]
- p95 latency: [ms]
- p99 latency: [ms]
- Errors: [Number] ([Percentage]%)

**Answer Submissions**:
- Total requests: [Number]
- Success rate: [Percentage]
- p50 latency: [ms]
- p95 latency: [ms]
- p99 latency: [ms]
- Errors: [Number] ([Percentage]%)

**Session Submits**:
- Total requests: [Number]
- Success rate: [Percentage]
- p50 latency: [ms]
- p95 latency: [ms]
- p99 latency: [ms]
- Errors: [Number] ([Percentage]%)

### Database Connection Pool

- Peak connections: [Number]
- Pool size: [Number]
- Max overflow: [Number]
- Pool exhaustion: [ ] Yes  [ ] No

### Redis Status

- Connection failures: [Number]
- Reconnect attempts: [Number]
- Degradation handled: [ ] Yes  [ ] No

**Issues Found**: [List any issues]

---

## Phase 3: Failure Injection

### A) Redis Failure

**Scenario**: Redis stopped for [Duration] seconds

**Expected Behavior**:
- [ ] Rate limits temporarily bypassed
- [ ] Auth still works
- [ ] No request crashes
- [ ] Warnings logged

**Actual Behavior**: [Description]

**Recovery Time**: [Duration]

**Issues Found**: [List any issues]

### B) Backend Worker Restart

**Scenario**: One backend container restarted

**Expected Behavior**:
- [ ] Other workers serve traffic
- [ ] No lost answers
- [ ] Clients retry safely

**Actual Behavior**: [Description]

**Recovery Time**: [Duration]

**Issues Found**: [List any issues]

### C) Network Delay

**Scenario**: [Description]

**Expected Behavior**: [Description]

**Actual Behavior**: [Description]

**Issues Found**: [List any issues]

---

## Phase 4: Data Integrity Verification

### Verification Results

**Orphaned Answers**: [Number] (Expected: 0)

**Duplicate Submits**: [Number] (Expected: 0)

**Missing Answers**: [Number] (Expected: 0)

**Unscored Sessions**: [Number] (Expected: 0)

**Answer/Question Mismatches**: [Number] (Expected: 0)

**Orphaned Events**: [Number] (Expected: 0)

**Inconsistent Status**: [Number] (Expected: 0)

**Duplicate Mastery Updates**: [Number] (Expected: 0)

### Summary Statistics

- Total sessions: [Number]
- Submitted sessions: [Number]
- Total answers: [Number]
- Total events: [Number]
- Sessions with submit event: [Number]

**Issues Found**: [List any issues]

---

## Phase 5: User Experience Validation

### Frontend Checks

- [ ] No spinner hangs
- [ ] Graceful error messages on retries
- [ ] Resume works after refresh
- [ ] Timer behaves correctly

### Auth Checks

- [ ] Token refresh does not interrupt session
- [ ] Logout does not delete active attempt state

**Issues Found**: [List any issues]

---

## Phase 6: Observability Review

### Metrics Captured

**Request Duration**:
- p50: [ms]
- p95: [ms]
- p99: [ms]

**Database Query Duration**:
- Slow queries (>100ms): [Number]
- Very slow queries (>300ms): [Number]

**Error Rates**:
- Total errors: [Number]
- 5xx errors: [Number]
- Error rate: [Percentage]%

**Database Pool Usage**:
- Peak usage: [Percentage]%
- Average usage: [Percentage]%

**Redis Reconnects**: [Number]

**Request ID Traceability**: [ ] Yes  [ ] No

**Issues Found**: [List any issues]

---

## Phase 7: Recovery Drill

### Full Backend Restart

**Restart Time**: [Duration]

**Recovery Time**: [Duration]

**Services Restored**:
- [ ] Health endpoint
- [ ] Ready endpoint
- [ ] Session creation
- [ ] Answer submission
- [ ] Session submit

**Data Consistency**: [ ] Verified  [ ] Issues found

**Issues Found**: [List any issues]

---

## Risk Register

### Observed Weak Points

1. **Risk**: [Description]
   - **Impact**: [High/Medium/Low]
   - **Likelihood**: [High/Medium/Low]
   - **Mitigation**: [Plan]

2. **Risk**: [Description]
   - **Impact**: [High/Medium/Low]
   - **Likelihood**: [High/Medium/Low]
   - **Mitigation**: [Plan]

### Mitigation Plan

[Detailed mitigation steps for each risk]

---

## GO/NO-GO Decision

### Hard Gates

- [ ] Zero data loss verified
- [ ] No corrupted sessions
- [ ] p95 latency acceptable (< 500ms)
- [ ] Recovery tested and successful
- [ ] Logs sufficient for audit
- [ ] EXAM_MODE verified
- [ ] Failure scenarios handled gracefully

### Blockers

[List any blockers that prevent GO decision]

### Decision

**Status**: [ ] GO  [ ] NO-GO

**Rationale**: [Explanation]

**Conditions**: [Any conditions for GO decision]

---

## Sign-Off

**Conducted By**: _________________  **Date**: _______________

**Reviewed By**: _________________  **Date**: _______________

**Approved By**: _________________  **Date**: _______________

---

## Appendices

### A) Load Test Scripts
[Location of k6 scripts]

### B) Failure Injection Logs
[Location of failure injection logs]

### C) Data Integrity SQL Results
[Location of SQL verification results]

### D) Observability Metrics
[Location of captured metrics]

### E) System Logs
[Location of system logs during rehearsal]
