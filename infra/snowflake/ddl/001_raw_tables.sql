-- Snowflake RAW schema DDL
-- These tables receive data from Postgres exports (JSONL files)
-- Schema version: v1

-- RAW_FACT_ATTEMPT
CREATE TABLE IF NOT EXISTS RAW_FACT_ATTEMPT (
    attempt_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    question_id VARCHAR(36) NOT NULL,
    attempted_at TIMESTAMP_NTZ NOT NULL,
    is_correct BOOLEAN NOT NULL,
    
    -- Optional fields
    concept_id INTEGER,
    theme_id INTEGER,
    block_id INTEGER,
    year INTEGER,
    selected_index INTEGER,
    correct_index INTEGER,
    time_spent_ms INTEGER,
    changed_answer_count INTEGER,
    marked_for_review BOOLEAN,
    difficulty_snapshot VARCHAR(20),
    difficulty_value FLOAT,
    elo_user_before FLOAT,
    elo_user_after FLOAT,
    elo_question_before FLOAT,
    elo_question_after FLOAT,
    algo_profile VARCHAR(50) NOT NULL,
    algo_versions OBJECT,
    
    -- Metadata
    _export_version VARCHAR(10),
    _generated_at TIMESTAMP_NTZ,
    _source_commit VARCHAR(40),
    _loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY (attempted_at, user_id);

-- Unique constraint on attempt_id
ALTER TABLE RAW_FACT_ATTEMPT ADD CONSTRAINT PK_RAW_FACT_ATTEMPT PRIMARY KEY (attempt_id);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS IDX_RAW_FACT_ATTEMPT_USER_ATTEMPTED ON RAW_FACT_ATTEMPT (user_id, attempted_at);
CREATE INDEX IF NOT EXISTS IDX_RAW_FACT_ATTEMPT_QUESTION ON RAW_FACT_ATTEMPT (question_id);
CREATE INDEX IF NOT EXISTS IDX_RAW_FACT_ATTEMPT_SESSION ON RAW_FACT_ATTEMPT (session_id);


-- RAW_FACT_EVENT
CREATE TABLE IF NOT EXISTS RAW_FACT_EVENT (
    event_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_at TIMESTAMP_NTZ NOT NULL,
    payload OBJECT,
    client_meta OBJECT,
    ingested_at TIMESTAMP_NTZ NOT NULL,
    
    -- Metadata
    _export_version VARCHAR(10),
    _generated_at TIMESTAMP_NTZ,
    _source_commit VARCHAR(40),
    _loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY (event_at, user_id);

-- Unique constraint on event_id
ALTER TABLE RAW_FACT_EVENT ADD CONSTRAINT PK_RAW_FACT_EVENT PRIMARY KEY (event_id);

-- Indexes
CREATE INDEX IF NOT EXISTS IDX_RAW_FACT_EVENT_USER_EVENT ON RAW_FACT_EVENT (user_id, event_at);
CREATE INDEX IF NOT EXISTS IDX_RAW_FACT_EVENT_SESSION ON RAW_FACT_EVENT (session_id);
CREATE INDEX IF NOT EXISTS IDX_RAW_FACT_EVENT_TYPE ON RAW_FACT_EVENT (event_type);


-- RAW_SNAPSHOT_MASTERY
CREATE TABLE IF NOT EXISTS RAW_SNAPSHOT_MASTERY (
    snapshot_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    concept_id VARCHAR(36) NOT NULL,
    snapshot_at TIMESTAMP_NTZ NOT NULL,
    mastery_prob FLOAT NOT NULL,
    attempts_total INTEGER NOT NULL,
    correct_total INTEGER,
    last_attempt_at TIMESTAMP_NTZ,
    bkt_params OBJECT,
    algo_profile VARCHAR(50) NOT NULL,
    algo_version_mastery VARCHAR(20) NOT NULL,
    
    -- Metadata
    _export_version VARCHAR(10),
    _generated_at TIMESTAMP_NTZ,
    _source_commit VARCHAR(40),
    _loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY (snapshot_at, user_id);

-- Unique constraint on snapshot_id
ALTER TABLE RAW_SNAPSHOT_MASTERY ADD CONSTRAINT PK_RAW_SNAPSHOT_MASTERY PRIMARY KEY (snapshot_id);

-- Indexes
CREATE INDEX IF NOT EXISTS IDX_RAW_SNAPSHOT_MASTERY_USER_SNAPSHOT ON RAW_SNAPSHOT_MASTERY (user_id, snapshot_at);
CREATE INDEX IF NOT EXISTS IDX_RAW_SNAPSHOT_MASTERY_CONCEPT ON RAW_SNAPSHOT_MASTERY (concept_id);


-- RAW_SNAPSHOT_REVISION_QUEUE_DAILY
CREATE TABLE IF NOT EXISTS RAW_SNAPSHOT_REVISION_QUEUE_DAILY (
    snapshot_date DATE NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    due_today_count INTEGER NOT NULL,
    overdue_count INTEGER NOT NULL,
    next_due_at TIMESTAMP_NTZ,
    algo_profile VARCHAR(50) NOT NULL,
    algo_version_revision VARCHAR(20) NOT NULL,
    
    -- Metadata
    _export_version VARCHAR(10),
    _generated_at TIMESTAMP_NTZ,
    _source_commit VARCHAR(40),
    _loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY (snapshot_date, user_id);

-- Composite primary key
ALTER TABLE RAW_SNAPSHOT_REVISION_QUEUE_DAILY ADD CONSTRAINT PK_RAW_SNAPSHOT_REVISION_QUEUE_DAILY PRIMARY KEY (snapshot_date, user_id);

-- Indexes
CREATE INDEX IF NOT EXISTS IDX_RAW_SNAPSHOT_REVISION_QUEUE_USER ON RAW_SNAPSHOT_REVISION_QUEUE_DAILY (user_id, snapshot_date);


-- RAW_DIM_QUESTION
CREATE TABLE IF NOT EXISTS RAW_DIM_QUESTION (
    question_id VARCHAR(36) NOT NULL,
    question_text TEXT,
    question_type VARCHAR(20),
    difficulty_label VARCHAR(20),
    difficulty_value FLOAT,
    theme_id INTEGER,
    block_id INTEGER,
    year INTEGER,
    created_at TIMESTAMP_NTZ,
    updated_at TIMESTAMP_NTZ,
    
    -- Metadata
    _export_version VARCHAR(10),
    _generated_at TIMESTAMP_NTZ,
    _source_commit VARCHAR(40),
    _loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY (question_id);

-- Unique constraint
ALTER TABLE RAW_DIM_QUESTION ADD CONSTRAINT PK_RAW_DIM_QUESTION PRIMARY KEY (question_id);

-- Indexes
CREATE INDEX IF NOT EXISTS IDX_RAW_DIM_QUESTION_THEME ON RAW_DIM_QUESTION (theme_id);
CREATE INDEX IF NOT EXISTS IDX_RAW_DIM_QUESTION_BLOCK ON RAW_DIM_QUESTION (block_id);


-- RAW_DIM_SYLLABUS
CREATE TABLE IF NOT EXISTS RAW_DIM_SYLLABUS (
    year INTEGER NOT NULL,
    block_id INTEGER NOT NULL,
    block_name VARCHAR(200),
    theme_id INTEGER NOT NULL,
    theme_name VARCHAR(200),
    concept_id VARCHAR(36),
    concept_name VARCHAR(200),
    concept_level VARCHAR(20),
    is_active BOOLEAN,
    created_at TIMESTAMP_NTZ,
    updated_at TIMESTAMP_NTZ,
    
    -- Metadata
    _export_version VARCHAR(10),
    _generated_at TIMESTAMP_NTZ,
    _source_commit VARCHAR(40),
    _loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY (year, block_id, theme_id);

-- Composite primary key (year, block_id, theme_id, concept_id)
ALTER TABLE RAW_DIM_SYLLABUS ADD CONSTRAINT PK_RAW_DIM_SYLLABUS PRIMARY KEY (year, block_id, theme_id, concept_id);

-- Indexes
CREATE INDEX IF NOT EXISTS IDX_RAW_DIM_SYLLABUS_CONCEPT ON RAW_DIM_SYLLABUS (concept_id);
CREATE INDEX IF NOT EXISTS IDX_RAW_DIM_SYLLABUS_THEME ON RAW_DIM_SYLLABUS (theme_id);
