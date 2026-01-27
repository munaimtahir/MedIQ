# Property-Based Tests

This directory contains property-based tests using [Hypothesis](https://hypothesis.readthedocs.io/).

## Overview

Property-based tests generate random inputs and verify that invariants hold across all generated cases. This helps discover edge cases and ensures mathematical properties are maintained.

## Test Suites

### `test_session_invariants.py`

Tests session state machine and submission invariants:

- **Session State Machine Validity**: Sessions transition ACTIVE → SUBMITTED/EXPIRED (cannot go backwards)
- **Cannot Submit for Non-Existent Question**: Answers can only be submitted for questions in the session
- **Duplicate Submit Idempotency**: Submitting the same answer multiple times creates only one answer record

### `test_scoring_invariants.py`

Tests scoring and learning algorithm invariants:

### `test_cms_invariants.py` ✅ **NEW**

Tests CMS workflow invariants:

- **Finite and Bounded Values**: All numeric outputs are finite (no NaN/Inf)
- **Probability Bounds**: Probabilities remain in [0, 1]
- **Mastery Bounds**: Mastery scores remain in [0, 1]
- **Elo Non-Explosion**: Elo ratings do not explode after N updates
- **Freeze Updates Mode**: When freeze_updates is enabled, learning state does not change

## Running Tests

### Run All Property Tests

```bash
pytest tests/property/ -v
```

### Run Specific Test Suite

```bash
pytest tests/property/test_session_invariants.py -v
pytest tests/property/test_scoring_invariants.py -v
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

## Configuration

Hypothesis settings are configured per-test using `@settings`:

- `max_examples`: Number of examples to generate (default: 50-100)
- `deadline`: Time limit per example (None = disabled for CI)
- `print_blob`: Print generated data for debugging

## Invariants Documented

### Session Invariants

1. **State Machine**: ACTIVE → SUBMITTED/EXPIRED (one-way)
2. **Question Validation**: Cannot submit answer for question not in session
3. **Idempotency**: Duplicate submits create only one answer record

### Scoring/Learning Invariants

1. **Finite Values**: No NaN or Inf in any numeric output
2. **Probability Bounds**: All probabilities in [0, 1]
3. **Mastery Bounds**: Mastery scores in [0, 1]
4. **Elo Stability**: Ratings remain within reasonable bounds after N updates
5. **Freeze Mode**: State unchanged when freeze_updates=true

### CMS Workflow Invariants ✅ **NEW**

1. **Immutability After Publish**: Published questions maintain state
2. **Status Transitions**: Valid workflow enforced (DRAFT -> IN_REVIEW -> APPROVED -> PUBLISHED)

## Adding New Property Tests

1. Create test function with `@given` decorator
2. Use Hypothesis strategies (`st.integers()`, `st.floats()`, etc.)
3. Add `@settings` for CI-friendly configuration
4. Document invariants in docstring
5. Use clear assertion messages

Example:

```python
@settings(max_examples=50, deadline=None)
@given(value=st.floats(min_value=0.0, max_value=1.0))
def test_invariant(value: float) -> None:
    """Property: Function always returns finite value."""
    result = my_function(value)
    assert math.isfinite(result), f"Result must be finite, got {result}"
```
