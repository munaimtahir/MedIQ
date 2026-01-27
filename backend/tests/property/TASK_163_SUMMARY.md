# Task 163: Property-Based Testing with Hypothesis - COMPLETE

## Summary

Added property-based tests using Hypothesis to verify session and scoring invariants across randomly generated inputs.

## Files Added

### Property Test Suites
- `tests/property/__init__.py`
- `tests/property/test_session_invariants.py` (3 property tests)
- `tests/property/test_scoring_invariants.py` (6 property tests)
- `tests/property/test_cms_invariants.py` (2 property tests) ✅ **NEW**
- `tests/property/README.md` (documentation)

## Dependencies Added

- `hypothesis==6.124.0`
- `hypothesis[pytest]==6.124.0`

## Test Coverage

### CMS Workflow Invariants (2 property tests) ✅ **NEW**

1. **CMS Workflow Immutability After Publish**
   - Property: Published questions cannot be modified
   - Property: DRAFT/IN_REVIEW/APPROVED questions can be updated
   - Generates: Random number of updates (0-5) and publish boolean

2. **CMS Status Transitions Validity**
   - Property: Status transitions follow valid workflow (DRAFT -> IN_REVIEW -> APPROVED -> PUBLISHED)
   - Property: Cannot go backwards or skip steps
   - Generates: Random sequences of status transitions

### Session Invariants (3 property tests)

1. **Session State Machine Validity**
   - Property: Sessions transition ACTIVE → SUBMITTED/EXPIRED (cannot go backwards)
   - Property: Cannot submit answer after session ended
   - Property: Re-submitting session is idempotent
   - Generates: Random number of questions (1-20) and answers (0-20)

2. **Cannot Submit for Question Not in Session**
   - Property: Cannot submit answer for a question that was never served in the session
   - Generates: Random question IDs and selected indices

3. **Duplicate Submit Idempotency**
   - Property: Submitting the same answer multiple times creates only one answer record
   - Generates: Random number of submits (1-5) and selected indices

### Scoring/Learning Invariants (6 property tests)

1. **p_correct Finite and Bounded**
   - Property: p_correct always returns finite values within bounds [guess_floor, 1.0]
   - Generates: Random theta, b, guess_floor, scale values

2. **BKT Update Finite and Bounded**
   - Property: BKT update always returns finite mastery in [0, 1]
   - Generates: Random p_L, p_S, p_G, p_T, and correct boolean

3. **Elo Update Finite and Non-Negative**
   - Property: Elo rating updates remain finite and within reasonable bounds
   - Generates: Random theta, b, k_u, k_q, delta values

4. **Elo Ratings Do Not Explode After N Updates**
   - Property: After N updates, ratings remain within sane bounds (< 10000.0)
   - Generates: Random number of updates (1-20) and correct/incorrect outcomes

5. **Mastery Computation Finite and Bounded**
   - Property: Mastery computation always returns finite values in [0, 1]
   - Generates: Random lists of attempts with is_correct, answered_at, difficulty

6. **Freeze Updates Prevents State Change**
   - Property: When freeze_updates is enabled, learning state does not change
   - Generates: Random correct/incorrect and freeze_enabled boolean

## Invariants Verified

### CMS Workflow Invariants ✅ **NEW**
- ✅ Immutability: Published questions cannot be updated
- ✅ Status transitions: Valid workflow enforced (no backwards/skip)

### Session Invariants
- ✅ State machine: ACTIVE → SUBMITTED/EXPIRED (one-way)
- ✅ Question validation: Cannot submit for question not in session
- ✅ Idempotency: Duplicate submits create only one answer record

### Scoring/Learning Invariants
- ✅ Finite values: No NaN or Inf in any numeric output
- ✅ Probability bounds: All probabilities in [0, 1]
- ✅ Mastery bounds: Mastery scores in [0, 1]
- ✅ Elo stability: Ratings remain within reasonable bounds after N updates
- ✅ Freeze mode: State unchanged when freeze_updates=true

## Commands to Run

### Run All Property Tests
```bash
cd backend
pytest tests/property/ -v
```

### Run Specific Test Suite
```bash
pytest tests/property/test_session_invariants.py -v
pytest tests/property/test_scoring_invariants.py -v
pytest tests/property/test_cms_invariants.py -v
```

### Run with Hypothesis Statistics
```bash
pytest tests/property/ -v --hypothesis-show-statistics
```

### Reproduce Failing Example
If a test fails, Hypothesis will print a seed. Reproduce with:
```bash
pytest tests/property/test_*.py::test_name --hypothesis-seed=1234567890
```

### Run in CI Mode (Faster)
```bash
pytest tests/property/ -v --hypothesis-max-examples=20
```

## Configuration

Hypothesis settings are configured per-test using `@settings`:

- `max_examples`: Number of examples to generate (50-100 for most tests)
- `deadline`: Time limit per example (None = disabled for CI compatibility)
- `print_blob`: Print generated data for debugging

## Test Design

- **Service-layer focus**: Tests call service functions directly for speed and determinism
- **Deterministic**: Uses seed helpers and transaction rollback for isolation
- **Reproducible**: Failing examples can be reproduced with printed seeds
- **CI-friendly**: Deadline disabled, reasonable max_examples

## Verification

All tests:
- Use Hypothesis strategies for random input generation
- Verify invariants hold across all generated cases
- Include clear assertion messages
- Are documented with property descriptions

## TODO Checklist for Task 164

- [x] Add property tests for CMS workflow invariants ✅
- [ ] Add property tests for analytics computation invariants
- [ ] Add property tests for revision queue invariants
- [ ] Add property tests for adaptive question selection invariants
- [ ] Add property tests for BKT parameter validation
- [ ] Add property tests for FSRS/SRS invariants
- [ ] Add property tests for IRT calibration invariants
- [ ] Add property tests for ranking invariants
- [ ] Add property tests for concept graph invariants
- [ ] Add property tests for search indexing invariants

**Note**: CMS workflow invariants property tests have been added in `test_cms_invariants.py`:
- Immutability after publish
- Status transition validity

## TODO Checklist for Task 165

- [ ] Add integration tests spanning multiple services
- [ ] Add end-to-end tests for complete user workflows
- [ ] Add performance/load tests for critical endpoints
- [ ] Add chaos engineering tests (network failures, DB timeouts)
- [ ] Add security tests (SQL injection, XSS, CSRF)
- [ ] Add API contract tests
- [ ] Add backward compatibility tests
- [ ] Add migration tests
- [ ] Add deployment smoke tests
- [ ] Add monitoring/alerting tests
