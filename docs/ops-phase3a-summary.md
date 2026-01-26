# Phase 3A Ops + Revision UX + Queue Jobs + Admin Monitoring - Implementation Summary

**Status:** Implemented  
**Date:** 2026-01-24

---

## Overview

This implementation adds operational infrastructure, revision UX, job system, admin monitoring, and evaluation dashboard enhancements to the learning engine platform.

---

## Completed Components

### A) Observability + Performance Tracking

1. **Enhanced Request Middleware** (`backend/app/common/request_id.py`)
   - Records request duration, route name, status code, user role, user_id, correlation_id
   - JSON structured logging
   - Performance sampling (5% default, configurable via `PERF_SAMPLE_RATE`)

2. **Metrics Endpoint** (`backend/app/api/v1/endpoints/observability.py`)
   - `GET /v1/admin/observability/metrics`
   - Returns p50/p95 latency per route, error counts, job status summaries
   - DB-backed (no Prometheus dependency)

3. **API Performance Sampling** (`backend/app/models/performance.py`)
   - `api_perf_sample` table for sampled performance data
   - Indexed on (route, occurred_at) for efficient queries

### B) Nightly Job: Regenerate Revision Queues (2AM)

1. **Job System** (`backend/app/jobs/`)
   - `job_run` table: Job execution tracking
   - `job_lock` table: DB-based locking to prevent concurrent execution
   - `lock.py`: Lock acquisition/release mechanism
   - `registry.py`: Job run creation and status updates
   - `run.py`: CLI entry point for job execution

2. **Revision Queue Regeneration** (`backend/app/jobs/revision_queue_regen.py`)
   - Queries FSRS due concepts (due_at <= end_of_today) and overdue
   - Maps concepts → themes (with fallback for missing mappings)
   - Computes theme_due_count per user
   - Writes to `revision_queue_theme` and `revision_queue_user_summary`
   - Writes daily snapshot to `queue_stats_daily`
   - Chunked processing (200 users per batch)

3. **Scheduling**
   - CLI: `python -m app.jobs.run revision_queue_regen`
   - Crontab/container: Docker-based job run documented in `backend/docs/jobs-setup.md` (no venv).

### C) Student UI: /student/revision

1. **Backend Endpoint** (`backend/app/api/v1/endpoints/revision_today.py`)
   - `GET /v1/learning/revision/today`
   - Returns due_today_total, overdue_total, themes list, recommended_theme_ids
   - Recommendation logic: due_count_today first, then BKT mastery (weaker = higher priority)

2. **Frontend Page** (`frontend/app/student/revision/page.tsx`)
   - Summary cards: Due Today, Overdue, Themes
   - Table of due themes with "Start Revision" buttons
   - Calls adaptive selection API with revision mode

### D) Admin Dashboard: Queue Stats + Job Monitoring

1. **Backend Endpoint** (`backend/app/api/v1/endpoints/admin_queues.py`)
   - `GET /v1/admin/queues/stats`
   - Returns global totals, breakdown by theme/block, last regen job status, 7-day trend

2. **Admin UI** (`frontend/app/admin/queues/page.tsx`)
   - Global totals cards
   - Last job run status
   - Top themes by due items table
   - Breakdown by block table

### E) Shadow Evaluation Dashboard

1. **Timeseries Endpoint** (`backend/app/api/v1/endpoints/eval_timeseries.py`)
   - `GET /v1/admin/evaluation/metrics/timeseries?metric=logloss&window=30d`
   - Returns time-series data for logloss, brier, ece metrics

2. **Admin UI** (`frontend/app/admin/evaluation/metrics/page.tsx`)
   - Metric selector (logloss, brier, ece)
   - Time window selector (7d, 30d, 90d)
   - Line chart using Recharts

3. **Eval Harness Enhancement**
   - BKT suite implementation (`backend/app/learning_engine/eval/suites/bkt_suite.py`)
   - Ensures logloss, brier, ece metrics are computed and stored

### F) Auto Optimizer Trigger + A/B Global vs Tuned

1. **SRS User Params Extensions** (`backend/app/models/srs.py`)
   - Added `training_cooldown_until` field
   - Added `assigned_group` field (BASELINE_GLOBAL, TUNED_ELIGIBLE)

2. **Optimizer Trigger** (`backend/app/jobs/fsrs_optimizer_trigger.py`)
   - Eligibility checker: n_review_logs >= 300, cooldown passed
   - A/B assignment: 50/50 split (stable, seeded by user_id hash)
   - Enqueues training job for TUNED_ELIGIBLE users
   - Sets cooldown (weekly, configurable)

3. **Constants** (`backend/app/learning_engine/config.py`)
   - `FSRS_OPTIMIZER_COOLDOWN_DAYS` (7 days)
   - `FSRS_AB_SPLIT_RATIO` (0.5)

### G) End-to-End Tests

1. **E2E Tests** (`backend/tests/test_e2e_smoke.py`)
   - Auth signup/login test
   - Session creation and submission test
   - Telemetry events written test
   - Revision queue endpoint test
   - Nightly job function test

2. **Smoke Script** (`backend/scripts/smoke_e2e.py`)
   - Basic API calls against local docker compose stack
   - Health check, session flow tests

### H) BKT Tag Quality Debt Logging

1. **Tag Quality Module** (`backend/app/learning_engine/tag_quality.py`)
   - `get_concept_id_with_fallback()`: Uses theme_id as pseudo-concept if concept_id missing
   - `log_tag_debt()`: Logs debt to `tag_quality_debt_log` table
   - Fallback behavior: "THEME::<theme_id>" pseudo-concept mapping

2. **Admin Endpoint** (`backend/app/api/v1/endpoints/admin_tag_quality.py`)
   - `GET /v1/admin/tag-quality`
   - Returns total debt (last 7d), breakdown by reason, top themes/questions

3. **Dashboard Widget** (`frontend/components/admin/dashboard/TagQualityDebtCard.tsx`)
   - Shows total debt count
   - Breakdown by reason
   - Top themes with debt
   - Added to admin dashboard

### I) User Preferences: Spacing Multipliers

1. **User Learning Prefs** (`backend/app/models/user_prefs.py`)
   - `user_learning_prefs` table
   - Fields: revision_daily_target, spacing_multiplier (default 1.0), retention_target_override

2. **API Endpoints** (`backend/app/api/v1/endpoints/user_prefs.py`)
   - `GET /v1/users/me/preferences/learning`
   - `PATCH /v1/users/me/preferences/learning`
   - Validation: spacing_multiplier [0.5, 2.0], retention_target_override [0.7, 0.95]

3. **Constants**
   - Spacing multiplier applied in FSRS due calculation (via desired_retention adjustment)

---

## Database Schema

### New Tables

1. **`job_run`** - Job execution tracking
2. **`job_lock`** - Job locking mechanism
3. **`revision_queue_theme`** - Theme-level revision queue aggregation
4. **`revision_queue_user_summary`** - User-level summary
5. **`queue_stats_daily`** - Daily snapshots
6. **`tag_quality_debt_log`** - BKT tag quality debt logging
7. **`api_perf_sample`** - API performance sampling
8. **`user_learning_prefs`** - User learning preferences

### Updated Tables

1. **`srs_user_params`** - Added `training_cooldown_until`, `assigned_group`

---

## Constants Added

All constants added to `backend/app/learning_engine/config.py` with provenance:

- `PERF_SAMPLE_RATE` (0.05) - API performance sampling rate
- `JOB_LOCK_DURATION_MINUTES` (120) - Job lock duration
- `REVISION_QUEUE_REGEN_BATCH_SIZE` (200) - User batch size
- `FSRS_OPTIMIZER_COOLDOWN_DAYS` (7) - FSRS training cooldown
- `FSRS_AB_SPLIT_RATIO` (0.5) - A/B split ratio
- `EVAL_CONFIDENCE_THRESHOLD` (0.5) - Model confidence threshold
- `EVAL_REGRESSION_THRESHOLD_PCT` (0.10) - Regression detection threshold

---

## API Endpoints

### Student
- `GET /v1/learning/revision/today` - Today's due themes

### Admin
- `GET /v1/admin/queues/stats` - Queue statistics
- `GET /v1/admin/observability/metrics` - Performance metrics
- `GET /v1/admin/evaluation/metrics/timeseries` - Evaluation metrics timeseries
- `GET /v1/admin/tag-quality` - Tag quality debt statistics

### User
- `GET /v1/users/me/preferences/learning` - Get learning preferences
- `PATCH /v1/users/me/preferences/learning` - Update learning preferences

---

## Frontend Pages

1. **`/student/revision`** - Student revision page with due themes
2. **`/admin/queues`** - Admin queue statistics page
3. **`/admin/evaluation/metrics`** - Evaluation metrics timeseries dashboard
4. **Admin Dashboard** - Enhanced with Tag Quality Debt widget

---

## Job System

### CLI Usage

```bash
# Run revision queue regeneration
python -m app.jobs.run revision_queue_regen

# Crontab (2am daily) – Docker only, e.g.:
# 0 2 * * * cd /path/to/repo && docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend python -m app.jobs.run revision_queue_regen
```

### Job Keys

- `revision_queue_regen` - Regenerate revision queues
- `fsrs_train_user` - FSRS per-user optimizer training (future)

---

## Testing

### E2E Tests

```bash
pytest backend/tests/test_e2e_smoke.py
```

### Smoke Script

```bash
python backend/scripts/smoke_e2e.py
```

---

## Limitations & Future Work

1. **Concept → Theme Mapping**: Currently uses fallback/hash-based mapping. Proper mapping table needed when concept graph is ready.

2. **FSRS Training Job**: Stub implementation - full training pipeline deferred but scaffolding in place.

3. **Performance Sampling**: DB writes are fire-and-forget (could be moved to background task queue).

4. **Evaluation Suites**: BKT suite implemented; FSRS suite can be added similarly.

5. **User Preferences UI**: Settings page needs to expose learning preferences editor.

---

## Migration

Run migration:

```bash
alembic upgrade head
```

This creates all new tables and adds fields to existing tables.

---

## Acceptance Criteria Status

✅ Nightly regen job runs via CLI and updates revision_queue_theme + summary  
✅ /student/revision shows today due themes and starts revision session  
✅ /admin/queues shows global + breakdown stats and last job status  
✅ /admin/evaluation shows logloss/Brier/ECE trends over time  
✅ Tag quality debt logging exists and dashboard widget displays counts  
✅ Basic backend e2e tests pass  
✅ No arbitrary constants: everything in params/constants with notes
