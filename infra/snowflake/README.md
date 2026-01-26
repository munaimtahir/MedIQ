# Snowflake Warehouse Schema and Transforms

This directory contains SQL scripts for defining Snowflake schemas and data transformation pipelines. **Snowflake export/load functionality is currently OFF** - these are preparation scripts only.

## Directory Structure

```
infra/snowflake/
├── ddl/
│   ├── 001_raw_tables.sql      # RAW schema tables (fact and dimension tables)
│   ├── 002_curated_views.sql   # CURATED schema views (deduplicated, normalized)
│   └── 003_marts.sql           # MART schema tables (analytics-ready)
├── transforms/
│   ├── curated_attempts.sql    # Transform: RAW_FACT_ATTEMPT → CURATED_ATTEMPT
│   ├── curated_mastery.sql    # Transform: RAW_SNAPSHOT_MASTERY → CURATED_MASTERY
│   ├── mart_percentiles.sql   # Transform: CURATED_MASTERY → MART_THEME_PERCENTILES_DAILY
│   ├── mart_comparisons.sql   # Transform: CURATED_* → MART_BLOCK_COMPARISONS_DAILY
│   └── mart_rank_sim.sql      # Transform: Rank predictions → MART_RANK_SIM_BASELINE
└── README.md                   # This file
```

## Schema Overview

### RAW Schema
Raw data tables that receive exported data from PostgreSQL (via JSONL files):

- **RAW_FACT_ATTEMPT**: Individual question attempts with full context
- **RAW_FACT_EVENT**: Telemetry events (answer_submitted, question_viewed, etc.)
- **RAW_SNAPSHOT_MASTERY**: Mastery probability snapshots over time
- **RAW_SNAPSHOT_REVISION_QUEUE_DAILY**: Daily revision queue snapshots
- **RAW_DIM_QUESTION**: Question dimension data
- **RAW_DIM_SYLLABUS**: Syllabus hierarchy (year → block → theme → concept)

### CURATED Schema
Deduplicated and normalized views/tables:

- **CURATED_ATTEMPT**: Deduplicated attempts with question dimension enrichment
- **CURATED_MASTERY**: Deduplicated mastery snapshots
- **CURATED_REVISION_QUEUE_DAILY**: Deduplicated revision queue snapshots

### MART Schema
Analytics-ready tables for reporting:

- **MART_THEME_PERCENTILES_DAILY**: Daily percentile distributions of mastery by theme
- **MART_BLOCK_COMPARISONS_DAILY**: Daily block-level comparison metrics
- **MART_RANK_SIM_BASELINE**: Rank prediction simulation baseline for A/B testing

## Usage

### Prerequisites

1. **Snowflake account** with appropriate permissions
2. **Database and schema** created in Snowflake
3. **Warehouse** configured for data loading

### Setup Steps

1. **Create schemas** (if not exists):
   ```sql
   CREATE SCHEMA IF NOT EXISTS RAW;
   CREATE SCHEMA IF NOT EXISTS CURATED;
   CREATE SCHEMA IF NOT EXISTS MART;
   ```

2. **Run DDL scripts in order**:
   ```bash
   # From Snowflake worksheet or CLI
   -- Execute 001_raw_tables.sql
   -- Execute 002_curated_views.sql
   -- Execute 003_marts.sql
   ```

3. **Load data** (when export pipeline is enabled):
   - Export pipeline generates JSONL files in `backend/warehouse/exports/`
   - Use Snowflake's `COPY INTO` command or Snowpipe to load JSONL files
   - Example:
     ```sql
     COPY INTO RAW.RAW_FACT_ATTEMPT
     FROM @your_stage/attempts/
     FILE_FORMAT = (TYPE = 'JSON');
     ```

4. **Run transforms** (after data is loaded):
   - Execute transform scripts in `transforms/` directory
   - Run in order: curated → marts
   - Schedule as needed (daily/hourly)

## Configuration

### Environment Variables

Snowflake configuration is controlled via environment variables (all disabled by default):

- `SNOWFLAKE_ENABLED=false` - Master switch (must be `true` to enable)
- `SNOWFLAKE_ACCOUNT` - Snowflake account identifier
- `SNOWFLAKE_USER` - Username
- `SNOWFLAKE_PASSWORD` - Password
- `SNOWFLAKE_WAREHOUSE` - Warehouse name
- `SNOWFLAKE_DATABASE` - Database name
- `SNOWFLAKE_SCHEMA=RAW` - Schema name (default: RAW)
- `FEATURE_ALLOW_SNOWFLAKE_CONNECT=false` - Feature flag to allow actual connections (default: false)

### Readiness Checks

The backend includes a readiness check module (`backend/app/warehouse/snowflake_readiness.py`) that:

1. Checks if `SNOWFLAKE_ENABLED=false` → returns `ready=false, reason="snowflake_disabled"`
2. Checks if `warehouse_mode != "active"` → returns `ready=false, reason="warehouse_not_active"`
3. Checks if `FEATURE_ALLOW_SNOWFLAKE_CONNECT=false` → returns `ready=false, reason="snowflake_connect_disabled"`
4. Only attempts connectivity (future) when all above pass

**By default, no connections are attempted** - the module is hard-disabled.

## Data Flow

```
PostgreSQL (Source)
    ↓
Export Pipeline (Task 139)
    ↓
JSONL Files (backend/warehouse/exports/)
    ↓
[Future: Snowflake Loader]
    ↓
RAW Schema Tables
    ↓
Transform Scripts
    ↓
CURATED Schema Views
    ↓
Transform Scripts
    ↓
MART Schema Tables
    ↓
Analytics/Reporting
```

## Notes

- **No execution in CI**: These scripts are not executed in CI/CD pipelines
- **Manual execution**: Run scripts manually in Snowflake when ready
- **Version control**: Schema changes should be versioned (e.g., `001_raw_tables_v2.sql`)
- **Clustering keys**: Optional clustering keys are defined for performance optimization
- **Primary keys**: All tables have primary key constraints where applicable
- **Metadata columns**: All tables include `_export_version`, `_generated_at`, `_source_commit`, `_loaded_at` for data lineage

## Future Work

- [ ] Implement Snowflake loader (COPY INTO or Snowpipe)
- [ ] Add automated transform scheduling
- [ ] Create data quality checks
- [ ] Add schema versioning/migration scripts
- [ ] Implement incremental load strategies
- [ ] Add monitoring and alerting

## References

- [Snowflake SQL Reference](https://docs.snowflake.com/en/sql-reference-commands.html)
- [Snowflake Data Loading](https://docs.snowflake.com/en/user-guide-data-load.html)
- [Task 139: Batch Export Pipeline](../README.md#task-139)
