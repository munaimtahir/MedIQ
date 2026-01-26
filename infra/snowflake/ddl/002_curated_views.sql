-- Snowflake CURATED schema DDL
-- These views/tables provide deduplicated, normalized data from RAW
-- Schema version: v1

-- CURATED_ATTEMPT
-- Deduplicates attempts, normalizes timestamps, enriches with dimension data
CREATE OR REPLACE VIEW CURATED_ATTEMPT AS
SELECT DISTINCT
    a.attempt_id,
    a.user_id,
    a.session_id,
    a.question_id,
    a.attempted_at,
    a.is_correct,
    
    -- Normalized concept/theme/block/year (prefer concept_id, fallback to theme_id)
    COALESCE(a.concept_id, a.theme_id) AS concept_id,
    a.theme_id,
    a.block_id,
    a.year,
    
    -- Answer details
    a.selected_index,
    a.correct_index,
    a.time_spent_ms,
    a.changed_answer_count,
    a.marked_for_review,
    
    -- Difficulty snapshot
    a.difficulty_snapshot,
    a.difficulty_value,
    
    -- ELO ratings
    a.elo_user_before,
    a.elo_user_after,
    a.elo_question_before,
    a.elo_question_after,
    
    -- Algorithm metadata
    a.algo_profile,
    a.algo_versions,
    
    -- Question dimension enrichment
    q.question_text,
    q.question_type,
    q.difficulty_label AS question_difficulty_label,
    
    -- Metadata
    a._export_version,
    a._generated_at,
    a._loaded_at
FROM RAW_FACT_ATTEMPT a
LEFT JOIN RAW_DIM_QUESTION q ON a.question_id = q.question_id
WHERE a._loaded_at IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY a.attempt_id ORDER BY a._loaded_at DESC) = 1;


-- CURATED_MASTERY
-- Deduplicates mastery snapshots, normalizes concept_id
CREATE OR REPLACE VIEW CURATED_MASTERY AS
SELECT DISTINCT
    m.snapshot_id,
    m.user_id,
    m.concept_id,
    m.snapshot_at,
    m.mastery_prob,
    m.attempts_total,
    m.correct_total,
    m.last_attempt_at,
    m.bkt_params,
    m.algo_profile,
    m.algo_version_mastery,
    
    -- Metadata
    m._export_version,
    m._generated_at,
    m._loaded_at
FROM RAW_SNAPSHOT_MASTERY m
WHERE m._loaded_at IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY m.snapshot_id ORDER BY m._loaded_at DESC) = 1;


-- CURATED_REVISION_QUEUE_DAILY
-- Deduplicates revision queue snapshots
CREATE OR REPLACE VIEW CURATED_REVISION_QUEUE_DAILY AS
SELECT DISTINCT
    r.snapshot_date,
    r.user_id,
    r.due_today_count,
    r.overdue_count,
    r.next_due_at,
    r.algo_profile,
    r.algo_version_revision,
    
    -- Metadata
    r._export_version,
    r._generated_at,
    r._loaded_at
FROM RAW_SNAPSHOT_REVISION_QUEUE_DAILY r
WHERE r._loaded_at IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY r.snapshot_date, r.user_id ORDER BY r._loaded_at DESC) = 1;
