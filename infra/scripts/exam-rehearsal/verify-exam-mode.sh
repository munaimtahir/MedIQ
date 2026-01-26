#!/bin/bash
# Verify EXAM_MODE Behavior
# Checks that EXAM_MODE=true disables heavy operations

set -e

COMPOSE_FILE="infra/docker/compose/docker-compose.prod.yml"
ENV=${1:-prod} # prod or staging

if [ "$ENV" = "staging" ]; then
  BACKEND_CONTAINER="exam_platform_backend_staging"
else
  BACKEND_CONTAINER="exam_platform_backend"
fi

echo "=== Verifying EXAM_MODE Behavior ($ENV) ==="
echo ""

# Check if EXAM_MODE is set
EXAM_MODE=$(docker exec "$BACKEND_CONTAINER" printenv EXAM_MODE || echo "false")
echo "EXAM_MODE: $EXAM_MODE"

if [ "$EXAM_MODE" != "true" ]; then
  echo "⚠️  WARNING: EXAM_MODE is not set to 'true'"
  echo "   Set EXAM_MODE=true in docker-compose.prod.yml before exam day"
fi

# Check for background jobs/cron (should be disabled in EXAM_MODE)
echo ""
echo "Checking for background jobs..."
if docker exec "$BACKEND_CONTAINER" ps aux | grep -E "(cron|celery|worker|scheduler)" | grep -v grep; then
  echo "⚠️  WARNING: Background job processes detected"
  echo "   These should be disabled during EXAM_MODE"
else
  echo "✓ No background job processes detected"
fi

# Check application logs for EXAM_MODE checks
echo ""
echo "Checking application logs for EXAM_MODE usage..."
if docker logs "$BACKEND_CONTAINER" --tail 1000 2>&1 | grep -i "exam_mode" | head -5; then
  echo "✓ EXAM_MODE is being checked in application code"
else
  echo "⚠️  WARNING: No EXAM_MODE checks found in recent logs"
  echo "   Verify that heavy operations check settings.EXAM_MODE"
fi

# Verify critical endpoints still work
echo ""
echo "Verifying critical endpoints..."
API_URL=${2:-"https://api.example.com"}

# Health check
if curl -s -f "$API_URL/health" > /dev/null; then
  echo "✓ Health endpoint accessible"
else
  echo "❌ Health endpoint not accessible"
fi

# Ready check
if curl -s -f "$API_URL/v1/ready" > /dev/null; then
  echo "✓ Ready endpoint accessible"
else
  echo "❌ Ready endpoint not accessible"
fi

echo ""
echo "=== EXAM_MODE Verification Complete ==="
echo ""
echo "Next steps:"
echo "  1. Ensure EXAM_MODE=true is set in production environment"
echo "  2. Verify heavy operations check EXAM_MODE before running"
echo "  3. Disable any cron jobs or scheduled tasks"
echo "  4. Test that analytics recompute is disabled"
