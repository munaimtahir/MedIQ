# Evaluation Harness

**Status:** Implemented (Task 123)  
**Module:** `backend/app/learning_engine/eval/`  
**Purpose:** Offline replay and metrics computation for learning algorithms

---

## Overview

The Evaluation Harness is a production-grade subsystem for evaluating learning algorithms offline. It provides:

1. **Offline replay** of learning/session logs deterministically
2. **Metrics computation** for:
   - Learning gain proxies
   - Stability
   - Calibration (probability calibration)
3. **Admin interface** to run and inspect evaluations
4. **Run registry** to compare algorithm versions over time

---

## Architecture

### Components

- **`dataset.py`** - Dataset builders, cohort slicing, event canonicalization
- **`replay.py`** - Deterministic replay runners (per user stream, per session stream)
- **`metrics/`** - Metrics library:
  - `calibration.py` - ECE, Brier, logloss, reliability curves
  - `stability.py` - Drift, variance, rank stability, recommendation overlap
  - `gains.py` - Learning gain proxies, time-to-mastery proxies
  - `utils.py` - Utility functions
- **`registry.py`** - DB read/write for eval runs + metrics + artifacts
- **`runner.py`** - Orchestrates: load dataset → replay → metrics → store results
- **`cli.py`** - Command-line interface
- **`api.py`** - Admin API endpoints

---

## Database Schema

### `eval_run`

Evaluation run metadata and configuration.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `created_at` | Timestamp | Creation time |
| `started_at` | Timestamp | Start time |
| `finished_at` | Timestamp | Completion time |
| `status` | String | QUEUED, RUNNING, SUCCEEDED, FAILED |
| `suite_name` | String | Suite name (e.g., "bkt_v1") |
| `suite_versions` | JSONB | Algorithm versions |
| `dataset_spec` | JSONB | Dataset specification |
| `config` | JSONB | Evaluation configuration |
| `git_sha` | String | Git commit SHA |
| `random_seed` | Integer | Random seed for reproducibility |
| `notes` | Text | Optional notes |
| `error` | Text | Error message if failed |

### `eval_metric`

Computed metrics per evaluation run.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `run_id` | UUID | FK to eval_run |
| `metric_name` | String | Metric name (e.g., "logloss", "ece") |
| `scope_type` | String | GLOBAL, YEAR, BLOCK, THEME, CONCEPT, USER |
| `scope_id` | String | Scope identifier |
| `value` | Numeric | Metric value |
| `n` | Integer | Number of observations |
| `extra` | JSONB | Additional metadata |

### `eval_artifact`

Generated artifacts (reports, summaries).

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `run_id` | UUID | FK to eval_run |
| `artifact_type` | String | REPORT_MD, RELIABILITY_BINS, CONFUSION, RAW_SUMMARY |
| `path` | Text | Path to artifact file |
| `created_at` | Timestamp | Creation time |

### `eval_curve`

Curve data (reliability curves, etc.).

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `run_id` | UUID | FK to eval_run |
| `curve_name` | String | Curve name |
| `data` | JSONB | Curve data points |
| `created_at` | Timestamp | Creation time |

---

## Dataset Builder

### Event Canonicalization

The dataset builder converts stored events into canonical `EvalEvent` format:

```python
class EvalEvent(BaseModel):
    event_id: UUID
    user_id: UUID
    session_id: UUID
    question_id: UUID
    timestamp: datetime
    is_correct: bool | None
    response_time_ms: int | None
    option_change_count: int | None
    mark_for_review: bool | None
    pause_blur_count: int | None
    year: int | None
    block_id: UUID | None
    theme_id: UUID | None
    cognitive_level: str | None
    question_difficulty: str | None
    action_propensity: float | None  # For bandit OPE
    event_sequence: int | None
```

### Split Strategies

1. **Time-based split**: Train window then eval window (rolling-origin supported)
2. **User holdout**: Per-user last-K holdout (e.g., last 20% attempts)

---

## Replay Engine

### Deterministic Replay

The replay engine processes events in order:
1. For each answered event:
   - Compute predictions **BEFORE** state update
   - Store predictions (p_correct, p_mastery, etc.)
   - Update algorithm state with ground-truth outcome
2. Maintain lightweight trace (aggregates per scope)

### Suite Interface

Algorithms implement the `EvalSuite` interface:

```python
class EvalSuite(ABC):
    def predict(state: ReplayState, event_context: EvalEvent) -> ReplayPrediction
    def update(state: ReplayState, outcome: bool, event_context: EvalEvent) -> ReplayState
    def init_state(user_id: UUID) -> ReplayState
```

---

## Metrics

### Calibration Metrics

- **Log Loss** (binary cross-entropy): Measures probability prediction quality
- **Brier Score**: Mean squared error of probabilities
- **ECE (Expected Calibration Error)**: Calibration error with fixed binning
- **Reliability Curve**: Plot of predicted vs actual probabilities
- **Calibration Slope/Intercept**: Linear fit of logit(predicted) ~ logit(actual)

### Stability Metrics

- **Parameter Drift**: Compare model parameters across rolling windows
- **Recommendation Stability**: Jaccard overlap of top-N recommendations
- **Rank Stability**: Spearman correlation of user ranks across windows

### Learning Gain Proxies

- **Time-to-Mastery**: Attempts needed to cross mastery threshold
- **Mastery Delta**: Change in mastery over evaluation window
- **Retention Proxy**: Predicted vs actual recall for revisited items

### Guardrails

- **Difficulty Shift**: Ensure improvements aren't due to easier questions

---

## Bandit OPE Support

The harness is prepared for bandit off-policy evaluation:

- If `action_propensity` is present in events → implement IPS, SNIPS, DR
- If missing → clearly label OPE as "unavailable"

**Important:** When implementing adaptive selection, log action propensity (or enough info to reconstruct it) for offline evaluation.

---

## Usage

### CLI

```bash
# Run evaluation
python -m app.learning_engine.eval.cli run \
    --suite bkt_v1 \
    --time-min 2024-01-01T00:00:00Z \
    --time-max 2024-12-31T23:59:59Z \
    --split time \
    --seed 42

# List runs
python -m app.learning_engine.eval.cli list

# Show run details
python -m app.learning_engine.eval.cli show <run_id>
```

### API

```bash
# Create evaluation run
POST /v1/admin/eval/runs
{
  "suite_name": "bkt_v1",
  "suite_versions": {"bkt": "1.0.0"},
  "dataset_spec": {
    "time_min": "2024-01-01T00:00:00Z",
    "time_max": "2024-12-31T23:59:59Z",
    "split_strategy": "time"
  },
  "config": {
    "calibration_bins": 10,
    "mastery_threshold": 0.85
  }
}

# List runs
GET /v1/admin/eval/runs?suite_name=bkt_v1&status=SUCCEEDED

# Get run details
GET /v1/admin/eval/runs/{run_id}
```

### Admin UI

Navigate to `/admin/evaluation` to:
- View list of evaluation runs
- See run status and metrics
- View detailed run information

---

## Limitations

1. **Synchronous execution**: Runs execute inline (can be moved to background jobs later)
2. **Placeholder suites**: Actual algorithm suites need to be implemented
3. **Limited metrics**: Core metrics implemented; can be extended
4. **No real-time updates**: UI doesn't auto-refresh during runs

---

## Future Enhancements

- Background job execution for long-running evaluations
- Real-time progress updates
- Comparison view (compare multiple runs)
- Automated evaluation scheduling
- Export to CSV/JSON for external analysis

---

## Testing

Run tests with:

```bash
pytest backend/tests/test_eval_harness.py
```

Tests cover:
- Calibration metrics correctness
- Dataset split strategies
- Determinism (same inputs → same outputs)
- Run registry operations
