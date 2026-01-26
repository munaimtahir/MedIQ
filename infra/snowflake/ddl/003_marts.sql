-- Snowflake MART schema DDL
-- Analytics-ready tables for reporting and dashboards
-- Schema version: v1

-- MART_THEME_PERCENTILES_DAILY
-- Daily percentiles of mastery/performance by theme
CREATE TABLE IF NOT EXISTS MART_THEME_PERCENTILES_DAILY (
    snapshot_date DATE NOT NULL,
    theme_id INTEGER NOT NULL,
    year INTEGER,
    block_id INTEGER,
    
    -- Percentile metrics
    p25_mastery FLOAT,
    p50_mastery FLOAT,
    p75_mastery FLOAT,
    p90_mastery FLOAT,
    p95_mastery FLOAT,
    p99_mastery FLOAT,
    
    -- Counts
    user_count INTEGER,
    active_user_count INTEGER,  -- users with attempts in last 30 days
    
    -- Aggregates
    avg_mastery FLOAT,
    avg_attempts FLOAT,
    avg_correct_rate FLOAT,
    
    -- Metadata
    computed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    algo_profile VARCHAR(50),
    algo_version_mastery VARCHAR(20)
)
CLUSTER BY (snapshot_date, theme_id);

-- Composite primary key
ALTER TABLE MART_THEME_PERCENTILES_DAILY ADD CONSTRAINT PK_MART_THEME_PERCENTILES_DAILY PRIMARY KEY (snapshot_date, theme_id);

-- Indexes
CREATE INDEX IF NOT EXISTS IDX_MART_THEME_PERCENTILES_THEME ON MART_THEME_PERCENTILES_DAILY (theme_id, snapshot_date);
CREATE INDEX IF NOT EXISTS IDX_MART_THEME_PERCENTILES_BLOCK ON MART_THEME_PERCENTILES_DAILY (block_id, snapshot_date);


-- MART_BLOCK_COMPARISONS_DAILY
-- Daily comparisons across blocks (for cohort analysis)
CREATE TABLE IF NOT EXISTS MART_BLOCK_COMPARISONS_DAILY (
    snapshot_date DATE NOT NULL,
    block_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    
    -- Performance metrics
    avg_mastery FLOAT,
    median_mastery FLOAT,
    avg_attempts_per_user FLOAT,
    avg_correct_rate FLOAT,
    
    -- User counts
    total_users INTEGER,
    active_users INTEGER,
    new_users INTEGER,  -- first attempt in this block on this date
    
    -- Theme-level aggregates
    theme_count INTEGER,
    avg_themes_per_user FLOAT,
    
    -- Metadata
    computed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    algo_profile VARCHAR(50),
    algo_version_mastery VARCHAR(20)
)
CLUSTER BY (snapshot_date, block_id, year);

-- Composite primary key
ALTER TABLE MART_BLOCK_COMPARISONS_DAILY ADD CONSTRAINT PK_MART_BLOCK_COMPARISONS_DAILY PRIMARY KEY (snapshot_date, block_id, year);

-- Indexes
CREATE INDEX IF NOT EXISTS IDX_MART_BLOCK_COMPARISONS_BLOCK ON MART_BLOCK_COMPARISONS_DAILY (block_id, snapshot_date);
CREATE INDEX IF NOT EXISTS IDX_MART_BLOCK_COMPARISONS_YEAR ON MART_BLOCK_COMPARISONS_DAILY (year, snapshot_date);


-- MART_RANK_SIM_BASELINE
-- Rank prediction simulation baseline (for A/B testing rank algorithm)
CREATE TABLE IF NOT EXISTS MART_RANK_SIM_BASELINE (
    simulation_date DATE NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    concept_id VARCHAR(36) NOT NULL,
    
    -- Baseline predictions
    baseline_rank_score FLOAT,
    baseline_rank_percentile FLOAT,
    
    -- Actual outcomes (for validation)
    actual_mastery FLOAT,
    actual_attempts INTEGER,
    actual_correct_rate FLOAT,
    
    -- Comparison metrics
    rank_error FLOAT,  -- difference between predicted and actual
    rank_accuracy BOOLEAN,  -- within acceptable threshold
    
    -- Metadata
    computed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    algo_profile VARCHAR(50),
    algo_version_rank VARCHAR(20)
)
CLUSTER BY (simulation_date, user_id);

-- Composite primary key
ALTER TABLE MART_RANK_SIM_BASELINE ADD CONSTRAINT PK_MART_RANK_SIM_BASELINE PRIMARY KEY (simulation_date, user_id, concept_id);

-- Indexes
CREATE INDEX IF NOT EXISTS IDX_MART_RANK_SIM_USER ON MART_RANK_SIM_BASELINE (user_id, simulation_date);
CREATE INDEX IF NOT EXISTS IDX_MART_RANK_SIM_CONCEPT ON MART_RANK_SIM_BASELINE (concept_id, simulation_date);
