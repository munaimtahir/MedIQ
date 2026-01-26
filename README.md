# Medical Exam Practice Platform

A production-grade skeleton for a medical exam practice platform with Student and Admin web applications.

## Architecture

- **Frontend**: Next.js (App Router) with TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI (Python) with PostgreSQL, Redis, Neo4j, Elasticsearch (optional)
- **Deployment**: Docker Compose
- **Search**: Elasticsearch with Postgres fallback (fail-open design)

## Quick Start

### Prerequisites

- Docker and Docker Compose (all dev, test, and run commands use containers; no local venv)

### Running with Docker Compose

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your local values if needed
   ```

2. **Start all services:**
   ```bash
   docker compose -f infra/docker/compose/docker-compose.dev.yml up -d --build
   ```

This will start:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Neo4j: http://localhost:7474
- Elasticsearch: http://localhost:9200 (optional, disabled by default)

**Note**: Elasticsearch is optional and disabled by default. The system operates normally with Postgres-only search. Enable Elasticsearch via environment variables and admin runtime controls.

The database will be automatically seeded with demo data on first startup. If you need to reseed, call `POST http://localhost:8000/seed`.

**Useful commands:**
```bash
# View logs
docker compose -f infra/docker/compose/docker-compose.dev.yml logs -f

# Stop services
docker compose -f infra/docker/compose/docker-compose.dev.yml down

# Access backend shell
docker compose -f infra/docker/compose/docker-compose.dev.yml exec backend bash
```

### Local Development

**This project uses Docker only.** Do not create virtual environments; run, test, and develop inside containers.

#### Backend (Docker)

```bash
# Start stack (includes backend with hot-reload)
docker compose -f infra/docker/compose/docker-compose.dev.yml up -d --build

# Run tests
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend python -m pytest tests/ -v

# Backend shell
docker compose -f infra/docker/compose/docker-compose.dev.yml exec backend bash
```

#### Frontend

```bash
cd frontend
pnpm install
pnpm run dev
```

## Demo Credentials

- **Student**: Use header `X-User-Id: student-1`
- **Admin**: Use header `X-User-Id: admin-1`

## Project Structure

```
/
├── frontend/          # Next.js app
│   ├── app/          # App Router pages
│   ├── components/   # React components
│   └── lib/          # Utilities and API clients
├── backend/           # FastAPI app
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── search/   # Elasticsearch integration (optional)
│   │   ├── warehouse/  # Warehouse export pipeline
│   │   ├── cohorts/    # Cohort analytics APIs
│   │   ├── learning_engine/  # Adaptive learning algorithms
│   │   └── models/   # SQLAlchemy models
│   └── alembic/      # Database migrations
├── infra/             # Infrastructure configurations
│   ├── docker/
│   │   └── compose/
│   │       └── docker-compose.dev.yml
│   └── snowflake/    # Snowflake DDL and transform scripts
│       ├── ddl/      # Schema definitions (RAW, CURATED, MART)
│       └── transforms/  # SQL transformation scripts
└── docs/              # Architecture documentation
```

## Code Formatting

This project uses automated formatting tools to maintain consistent code style.

### Format All Code

```bash
# Linux/Mac
./infra/scripts/format-all.sh

# Windows PowerShell
.\infra\scripts\format-all.ps1
```

### Check Formatting (CI)

```bash
# Linux/Mac
./infra/scripts/format-check.sh

# Windows PowerShell
.\infra\scripts\format-check.ps1
```

### Individual Services

**Frontend:**
```bash
cd frontend
pnpm run format          # Format code
pnpm run format:check    # Check formatting
pnpm run lint            # Run ESLint
pnpm run typecheck       # TypeScript check
```

**Backend:**
```bash
cd backend
black .                 # Format code
ruff check .            # Lint code
ruff check . --fix      # Auto-fix linting issues
pytest -v               # Run tests
```

### Tools Used

- **Frontend**: Prettier (with Tailwind plugin) + ESLint
- **Backend**: Black (formatting) + Ruff (linting)

## Constants and Configuration Management

### Philosophy

This project enforces strict provenance for all algorithmic constants to ensure scientific rigor and maintainability.

**Core Principles:**
1. **No Magic Numbers:** All constants centralized in `backend/app/learning_engine/config.py`
2. **Source Attribution:** Every constant documents its origin (research paper, library default, or heuristic)
3. **Import-time Validation:** Invalid constants fail at startup, not in production
4. **Calibration Tracking:** Heuristic constants have explicit improvement plans

### Adding New Constants

```python
# In backend/app/learning_engine/config.py

from dataclasses import dataclass

MY_NEW_THRESHOLD = SourcedValue(
    value=42,
    sources=[
        "Smith et al. (2024) - Optimal threshold for X was empirically determined as 42",
        "Validated on 10,000+ student attempts with 95% confidence interval [40, 44]"
    ]
)
```

**Requirements:**
- Must use `SourcedValue` wrapper
- Must include at least one source explaining the value
- Sources must be specific (not just "set to 42")
- For heuristics, mention "placeholder" or "needs calibration"

### Documentation

- **Constants Audit:** `docs/constants-audit.md` - inventory of all 23 constants
- **Calibration Plan:** `docs/calibration-plan.md` - roadmap for tuning heuristic constants
- **Algorithm Docs:** `docs/algorithms.md` - detailed descriptions of all learning algorithms

### Testing

```bash
cd backend
pytest tests/test_constants_provenance.py -v
```

This test suite enforces:
- All constants have non-empty source attribution
- Sources explain reasoning (not just "value is X")
- Heuristic constants mention calibration plans
- FSRS weights have exactly 19 parameters
- BKT constraints satisfy non-degeneracy (S + G < 1)

## Environment Configuration

### Elasticsearch (Optional)

Elasticsearch is **disabled by default** and can be enabled via environment variables:

```bash
# In .env or docker-compose environment
ELASTICSEARCH_ENABLED=true
ELASTICSEARCH_URL=http://elasticsearch:9200
ELASTICSEARCH_INDEX_PREFIX=platform
```

**Important**: The system operates normally without Elasticsearch. Search defaults to Postgres, and CMS publishing never depends on Elasticsearch availability.

### Search Runtime Control

Admins can toggle search engine mode via:
- `/admin/learning-ops` → Search card
- `/admin/search` → Dedicated search operations page

Default mode: **Postgres** (always available, fail-safe)

### Warehouse & Snowflake (OFF by Default)

Warehouse exports and Snowflake integration are **disabled by default**:

```bash
# Warehouse mode (disabled|shadow|active)
# Controlled via admin runtime config, not env vars

# Snowflake (hard OFF switch)
SNOWFLAKE_ENABLED=false  # Must be explicitly enabled
FEATURE_ALLOW_SNOWFLAKE_CONNECT=false  # Additional safety gate
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
SNOWFLAKE_PASSWORD=...
SNOWFLAKE_WAREHOUSE=...
SNOWFLAKE_DATABASE=...
SNOWFLAKE_SCHEMA=RAW

# Readiness gate configuration
FEATURE_TRANSFORMS_OPTIONAL=false  # If true, transforms are optional for activation
WAREHOUSE_PIPELINE_FRESHNESS_HOURS=24  # Max hours since last successful run
WAREHOUSE_ERROR_BUDGET_RUNS=3  # Number of recent runs to check for failures
```

**Important**: 
- Warehouse exports run in **shadow mode** (files/manifests only) by default
- Snowflake loading requires explicit activation via admin UI with **readiness gate checks**
- All warehouse operations require police mode confirmation (typed phrase + reason)
- Cohort analytics APIs are gated and disabled until warehouse is active and Snowflake is ready

### Warehouse Readiness Gate

The system implements a comprehensive **readiness gate** that prevents activation unless all conditions are met:

**Readiness Criteria:**
- ✅ Runtime: Warehouse mode requested is "active"
- ✅ Environment: `SNOWFLAKE_ENABLED=true` and `FEATURE_ALLOW_SNOWFLAKE_CONNECT=true`
- ✅ Credentials: All required Snowflake credentials present
- ✅ Connectivity: Can connect to Snowflake (with timeout)
- ✅ Privileges: Required database/warehouse/schema privileges
- ✅ Stage: External/internal stage exists and is reachable
- ✅ Schema Integrity: RAW tables exist for all required datasets
- ✅ Pipeline Sanity: Last successful export/transform within freshness window
- ✅ Error Budget: No failed runs in recent execution history

**Effective Mode Resolution:**
- `disabled` requested → `disabled` effective
- `shadow` requested → `shadow` effective (no Snowflake connect/load)
- `active` requested:
  - If frozen → `shadow` effective + warning
  - If not ready → `shadow` effective + blocking reasons
  - If ready → `active` effective

**Admin UI Guardrails:**
- "Switch to Active" button disabled until all readiness checks pass
- Tooltip displays blocking reasons when not ready
- Readiness status badge (READY/NOT READY) with detailed breakdown
- Police mode confirmation required for all mode switches

## Documentation

- **Architecture**: `docs/architecture.md` - System design and patterns
- **API Contracts**: `docs/api-contracts.md` - API specifications
- **Algorithms**: `docs/algorithms.md` - Learning engine algorithms
- **Runbook**: `docs/runbook.md` - Operational procedures
- **Observability**: `docs/observability.md` - Logging and monitoring

## Recent Updates

### Warehouse & Analytics (Tasks 138-141)
- ✅ Warehouse export pipeline (Postgres → files/manifests in shadow mode)
- ✅ Snowflake schema definitions (DDL + transform scripts, OFF by default)
- ✅ Cohort analytics APIs (percentiles, comparisons, rank simulation)
- ✅ Admin warehouse ops console (`/admin/warehouse`)
- ✅ Cohort analytics console (`/admin/cohorts`)
- ✅ **Shadow readiness gates** (comprehensive activation policy with fail-open design)
  - Multi-layer readiness checks (runtime, env, connectivity, schema, pipeline, error budget)
  - Effective mode resolution (disabled/shadow/active) with automatic fallback
  - Admin UI guardrails with blocking reasons and disabled controls
  - Readiness API endpoints (`/admin/warehouse/readiness`, `/admin/warehouse/runtime`)
- ✅ Police mode controls for all warehouse operations

### Search & Indexing (Tasks 128-132)
- ✅ Elasticsearch integration with fail-open design
- ✅ Admin Questions search with facets, filters, and URL state
- ✅ Search runtime toggle (Postgres ↔ Elasticsearch)
- ✅ Performance optimizations (prefetch, caching, keyboard navigation)

### Learning Ops Enhancements
- ✅ Dedicated pages for IRT, Rank, and Graph Revision
- ✅ Change Review workflow for batch operations
- ✅ Operator-grade controls with police mode confirmation

### UX Improvements
- ✅ Instant-feel optimizations (prefetch, scroll preservation)
- ✅ Keyboard-first navigation
- ✅ Degraded mode indicators and warnings

## Key Features

### Admin Portal

- **Questions CMS**: Full CRUD with workflow (Draft → In Review → Approved → Published)
- **Advanced Search**: Elasticsearch-powered search with Postgres fallback
  - Full-text search with relevance ranking
  - Faceted filtering (year, block, theme, cognitive level, difficulty, etc.)
  - URL-based state management for shareable links
  - Keyboard navigation and prefetching for instant feel
- **Learning Ops**: Operator-grade control plane for algorithm runtime
  - Runtime profile switching (V1_PRIMARY ↔ V0_FALLBACK)
  - Module overrides and freeze/unfreeze controls
  - IRT, Rank, and Graph Revision shadow systems
  - Change Review workflow for batch operations
  - Search engine runtime toggle (Postgres ↔ Elasticsearch)
- **Warehouse Ops**: Export pipeline and analytics control
  - Warehouse mode switching (disabled ↔ shadow ↔ active)
  - **Readiness gate dashboard** with comprehensive status checks
    - Real-time readiness evaluation (runtime, env, connectivity, schema, pipeline, error budget)
    - Effective mode display (requested vs. effective mode)
    - Blocking reasons with detailed explanations
    - UI guardrails: "Switch to Active" disabled until all checks pass
  - Export run management (incremental, backfill)
  - Export history and monitoring
  - Police mode confirmation for all mode switches
- **Cohort Analytics**: Cohort comparison and percentile dashboards
  - Gated by warehouse readiness (disabled by default)
  - Percentiles, comparisons, and rank simulation APIs
- **Syllabus Management**: Hierarchical structure (Years → Blocks → Themes → Topics)
- **Import System**: Bulk question import with schema validation
- **Audit Trail**: Comprehensive logging of all admin actions

### Student Portal

- **Adaptive Practice**: BKT-based mastery tracking and FSRS-powered revision scheduling
- **Session Management**: Timed practice sessions with detailed analytics
- **Progress Tracking**: Block and theme-level performance metrics
- **Dashboard**: Personalized recommendations and weak areas identification

### Search & Indexing

- **Elasticsearch Integration** (Optional):
  - Versioned indices with alias-based zero-downtime rebuilds
  - Outbox pattern for reliable indexing (never blocks publishing)
  - Nightly reindex jobs with atomic alias swaps
  - Admin-controlled runtime toggle (Postgres ↔ Elasticsearch)
  - Fail-open design: CMS continues even if ES is down
- **Postgres Fallback**: Always-available baseline search with graceful degradation

### Learning Engine

- **Adaptive Algorithms**: BKT (mastery), FSRS (revision), IRT (difficulty calibration)
- **Runtime Controls**: Operator-safe switching between algorithm versions
- **Shadow Systems**: IRT, Rank Prediction, and Graph Revision for gradual rollout
- **Audit & Compliance**: Full audit trail for all algorithm switches

### Warehouse & Analytics

- **Export Pipeline**: Batch export from Postgres to files/manifests (shadow mode)
  - Incremental exports with watermark tracking
  - Backfill support for historical data
  - Export run logging and monitoring
- **Snowflake Integration** (OFF by default):
  - Schema definitions (RAW, CURATED, MART layers)
  - Transform SQL scripts for data pipelines
  - **Readiness gate system** prevents premature activation
    - Multi-layer checks: runtime, environment, credentials, connectivity, privileges, stage, schema integrity
    - Pipeline sanity checks (freshness windows, error budgets)
    - Effective mode resolution with automatic fallback to shadow mode
    - Cached readiness evaluation (60s TTL) to reduce external dependency load
  - Hard OFF switch: no connections unless explicitly enabled
- **Admin Operations**:
  - Warehouse mode switching (disabled ↔ shadow ↔ active) with readiness validation
  - Readiness status dashboard with detailed check breakdown
  - Blocking reasons display and UI guardrails
  - Police mode confirmation for all critical operations
- **Cohort Analytics** (gated by warehouse readiness):
  - Percentile distributions (p10, p25, p50, p75, p90)
  - Cohort comparisons (year/block/theme)
  - Rank simulation baseline
  - Activation policy: requires active warehouse + Snowflake ready

## Development Roadmap

- Phase 1: ✅ Core Platform (Skeleton, Auth, CMS)
- Phase 2: ✅ Adaptive Learning Engine (BKT, FSRS, IRT)
- Phase 3: ✅ Search & Indexing (Elasticsearch integration)
- Phase 4: ✅ Learning Ops & Runtime Controls
- Phase 5: 🔄 Advanced Analytics & Reporting
- Phase 6: 📋 Mobile App
- Phase 7: 📋 ML/AI Enhancements

