-- Data Integrity Verification Queries
-- Run after exam-day rehearsal to verify no data loss or corruption

-- 1. Check for orphaned session answers (answers without sessions)
SELECT 
    COUNT(*) as orphaned_answers,
    'session_answers without valid session' as issue
FROM session_answers sa
LEFT JOIN test_sessions ts ON sa.session_id = ts.id
WHERE ts.id IS NULL;

-- 2. Check for duplicate submits (sessions with multiple submit events)
SELECT 
    session_id,
    COUNT(*) as submit_count,
    'Multiple submit events' as issue
FROM attempt_events
WHERE event_type = 'SESSION_SUBMITTED'
GROUP BY session_id
HAVING COUNT(*) > 1;

-- 3. Check for sessions with missing answers (sessions with questions but no answers)
SELECT 
    ts.id as session_id,
    ts.total_questions,
    COUNT(DISTINCT sa.id) as answer_count,
    (ts.total_questions - COUNT(DISTINCT sa.id)) as missing_answers,
    'Session with missing answers' as issue
FROM test_sessions ts
LEFT JOIN session_answers sa ON ts.id = sa.session_id
WHERE ts.status IN ('SUBMITTED', 'EXPIRED')
GROUP BY ts.id, ts.total_questions
HAVING COUNT(DISTINCT sa.id) < ts.total_questions;

-- 4. Check for sessions submitted but not scored
SELECT 
    id as session_id,
    status,
    score_correct,
    score_total,
    'Submitted but not scored' as issue
FROM test_sessions
WHERE status IN ('SUBMITTED', 'EXPIRED')
  AND (score_correct IS NULL OR score_total IS NULL);

-- 5. Check for answer count mismatches (answers don't match session questions)
SELECT 
    ts.id as session_id,
    ts.total_questions,
    COUNT(DISTINCT sq.question_id) as question_count,
    COUNT(DISTINCT sa.id) as answer_count,
    'Answer/question count mismatch' as issue
FROM test_sessions ts
LEFT JOIN session_questions sq ON ts.id = sq.session_id
LEFT JOIN session_answers sa ON ts.id = sa.session_id
WHERE ts.status IN ('SUBMITTED', 'EXPIRED')
GROUP BY ts.id, ts.total_questions
HAVING COUNT(DISTINCT sq.question_id) != ts.total_questions
   OR COUNT(DISTINCT sa.id) != COUNT(DISTINCT sq.question_id);

-- 6. Check for telemetry events without sessions (should not happen due to CASCADE)
SELECT 
    COUNT(*) as orphaned_events,
    'Events without valid session' as issue
FROM attempt_events ae
LEFT JOIN test_sessions ts ON ae.session_id = ts.id
WHERE ts.id IS NULL;

-- 7. Check for sessions with inconsistent status (submitted but no submitted_at)
SELECT 
    id as session_id,
    status,
    submitted_at,
    'Inconsistent status' as issue
FROM test_sessions
WHERE status IN ('SUBMITTED', 'EXPIRED')
  AND submitted_at IS NULL;

-- 8. Check for duplicate mastery updates (same user/theme updated multiple times in short window)
SELECT 
    user_id,
    theme_id,
    COUNT(*) as update_count,
    MIN(computed_at) as first_update,
    MAX(computed_at) as last_update,
    'Multiple mastery updates in short window' as issue
FROM user_theme_mastery
WHERE computed_at > NOW() - INTERVAL '1 hour'
GROUP BY user_id, theme_id
HAVING COUNT(*) > 5; -- More than 5 updates in 1 hour suggests duplicate processing

-- 9. Summary: Total sessions, submitted sessions, answers, events
SELECT 
    'Summary' as check_type,
    COUNT(DISTINCT ts.id) as total_sessions,
    COUNT(DISTINCT CASE WHEN ts.status IN ('SUBMITTED', 'EXPIRED') THEN ts.id END) as submitted_sessions,
    COUNT(DISTINCT sa.id) as total_answers,
    COUNT(DISTINCT ae.id) as total_events,
    COUNT(DISTINCT CASE WHEN ae.event_type = 'SESSION_SUBMITTED' THEN ae.session_id END) as sessions_with_submit_event
FROM test_sessions ts
LEFT JOIN session_answers sa ON ts.id = sa.session_id
LEFT JOIN attempt_events ae ON ts.id = ae.session_id;
