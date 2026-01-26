#!/bin/bash
# Observability Metrics Capture Script
# Captures key metrics during and after exam-day rehearsal

set -e

COMPOSE_FILE="infra/docker/compose/docker-compose.prod.yml"
OUTPUT_DIR=${1:-./rehearsal-metrics}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$OUTPUT_DIR"

echo "=== Capturing Observability Metrics ==="
echo "Output directory: $OUTPUT_DIR"
echo ""

# 1. Database connection pool usage
echo "1. Capturing database connection pool usage..."
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
SELECT 
    count(*) as active_connections,
    max_conn as max_connections,
    round(100.0 * count(*) / max_conn, 2) as pool_usage_pct
FROM pg_stat_activity, 
     (SELECT setting::int as max_conn FROM pg_settings WHERE name = 'max_connections') mc
WHERE datname = 'exam_platform'
GROUP BY max_conn;
" > "$OUTPUT_DIR/db_pool_usage_$TIMESTAMP.txt"

# 2. Slow queries (last hour)
echo "2. Capturing slow queries..."
docker logs exam_platform_backend --since 1h 2>&1 | grep -i "slow_sql" | tail -100 > "$OUTPUT_DIR/slow_queries_$TIMESTAMP.log" || echo "No slow queries found"

# 3. Slow requests (last hour)
echo "3. Capturing slow requests..."
docker logs exam_platform_backend --since 1h 2>&1 | grep -E "(total_ms|warn|error)" | grep -E "(>500|>1500)" | tail -100 > "$OUTPUT_DIR/slow_requests_$TIMESTAMP.log" || echo "No slow requests found"

# 4. Error rates
echo "4. Capturing error rates..."
docker logs exam_platform_backend --since 1h 2>&1 | grep -E "status_code.*[45][0-9]{2}" | wc -l > "$OUTPUT_DIR/error_count_$TIMESTAMP.txt"
docker logs exam_platform_backend --since 1h 2>&1 | grep -E "status_code.*5[0-9]{2}" | wc -l > "$OUTPUT_DIR/error_5xx_count_$TIMESTAMP.txt"

# 5. Redis connection status
echo "5. Capturing Redis status..."
docker exec exam_platform_redis redis-cli INFO stats | grep -E "(total_connections_received|rejected_connections|keyspace)" > "$OUTPUT_DIR/redis_stats_$TIMESTAMP.txt" || echo "Redis not available"

# 6. Container resource usage
echo "6. Capturing container resource usage..."
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" > "$OUTPUT_DIR/container_resources_$TIMESTAMP.txt"

# 7. Traefik metrics (if available)
echo "7. Capturing Traefik metrics..."
docker logs exam_platform_traefik --since 1h --tail 1000 2>&1 | grep -E "(router|middleware|error)" | tail -50 > "$OUTPUT_DIR/traefik_metrics_$TIMESTAMP.log" || echo "Traefik logs not available"

# 8. Session statistics
echo "8. Capturing session statistics..."
docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "
SELECT 
    status,
    COUNT(*) as count,
    COUNT(CASE WHEN created_at > NOW() - INTERVAL '1 hour' THEN 1 END) as last_hour,
    AVG(EXTRACT(EPOCH FROM (submitted_at - started_at))) as avg_duration_seconds
FROM test_sessions
GROUP BY status;
" > "$OUTPUT_DIR/session_stats_$TIMESTAMP.txt"

# 9. Request ID traceability sample
echo "9. Capturing request ID sample..."
docker logs exam_platform_backend --since 1h 2>&1 | grep -oE "request_id\":\"[^\"]+\"" | head -20 | sort -u > "$OUTPUT_DIR/request_ids_sample_$TIMESTAMP.txt"

echo ""
echo "=== Metrics Capture Complete ==="
echo "All metrics saved to: $OUTPUT_DIR"
echo ""
echo "Summary:"
echo "  - DB pool usage: $OUTPUT_DIR/db_pool_usage_$TIMESTAMP.txt"
echo "  - Slow queries: $OUTPUT_DIR/slow_queries_$TIMESTAMP.log"
echo "  - Slow requests: $OUTPUT_DIR/slow_requests_$TIMESTAMP.log"
echo "  - Error counts: $OUTPUT_DIR/error_count_$TIMESTAMP.txt"
echo "  - Container resources: $OUTPUT_DIR/container_resources_$TIMESTAMP.txt"
echo "  - Session stats: $OUTPUT_DIR/session_stats_$TIMESTAMP.txt"
