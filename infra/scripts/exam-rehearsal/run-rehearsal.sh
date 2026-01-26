#!/bin/bash
# Exam-Day Rehearsal Orchestration Script
# Coordinates all phases of the rehearsal

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="infra/docker/compose/docker-compose.prod.yml"
ENV=${1:-staging} # Use staging for rehearsal
API_URL=${2:-"https://api-staging.example.com"}
AUTH_TOKEN=${3:-""}

REPORT_DIR="$SCRIPT_DIR/reports"
mkdir -p "$REPORT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/rehearsal_report_$TIMESTAMP.md"

echo "=== Exam-Day Rehearsal ==="
echo "Environment: $ENV"
echo "API URL: $API_URL"
echo "Report: $REPORT_FILE"
echo ""

# Initialize report
cat > "$REPORT_FILE" <<EOF
# Exam-Day Rehearsal Report

**Date**: $(date)
**Environment**: $ENV
**API URL**: $API_URL

## Executive Summary

[To be filled after rehearsal]

## Phases

EOF

# Phase 1: Pre-Exam Freeze
echo "=== PHASE 1: Pre-Exam Freeze ==="
echo "1. Enabling EXAM_MODE..."
if [ "$ENV" = "staging" ]; then
  export EXAM_MODE=true
  docker compose -f "$COMPOSE_FILE" up -d backend_staging
else
  export EXAM_MODE=true
  docker compose -f "$COMPOSE_FILE" up -d backend
fi

echo "2. Verifying EXAM_MODE behavior..."
"$SCRIPT_DIR/verify-exam-mode.sh" "$ENV" "$API_URL" >> "$REPORT_FILE" 2>&1

sleep 5

# Phase 2: Load Generation
echo ""
echo "=== PHASE 2: Load Generation ==="
echo "Starting load tests..."
echo ""
echo "⚠️  NOTE: Load tests require k6 and authentication token"
echo "   Install k6: https://k6.io/docs/getting-started/installation/"
echo "   Set AUTH_TOKEN environment variable"
echo ""
echo "To run load tests manually:"
echo "  1. Session creation: k6 run --vus 400 --duration 5m $SCRIPT_DIR/load-test-sessions.js"
echo "  2. Answer submissions: k6 run --vus 300 --duration 30m $SCRIPT_DIR/load-test-answers.js"
echo "  3. Submit spike: k6 run --vus 400 --duration 10m $SCRIPT_DIR/load-test-submit.js"
echo ""

read -p "Have you completed load tests? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "✓ Load tests completed"
  echo "### Phase 2: Load Generation" >> "$REPORT_FILE"
  echo "- Load tests completed" >> "$REPORT_FILE"
  echo "- [Add k6 results summary here]" >> "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"
else
  echo "⚠️  Skipping load test phase (run manually)"
fi

# Phase 3: Failure Injection
echo ""
echo "=== PHASE 3: Failure Injection ==="
echo "Available failure scenarios:"
echo "  1. Redis failure"
echo "  2. Backend worker restart"
echo "  3. Network delay"
echo ""

read -p "Inject Redis failure? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  if [ "$ENV" = "staging" ]; then
    "$SCRIPT_DIR/failure-injection.sh" redis-staging-stop
  else
    "$SCRIPT_DIR/failure-injection.sh" redis-stop
  fi
  echo "### Phase 3A: Redis Failure" >> "$REPORT_FILE"
  echo "- Redis stopped for 60 seconds" >> "$REPORT_FILE"
  echo "- [Add observations here]" >> "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"
fi

read -p "Inject backend restart? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  if [ "$ENV" = "staging" ]; then
    "$SCRIPT_DIR/failure-injection.sh" backend-staging-restart
  else
    "$SCRIPT_DIR/failure-injection.sh" backend-restart
  fi
  echo "### Phase 3B: Backend Restart" >> "$REPORT_FILE"
  echo "- Backend container restarted" >> "$REPORT_FILE"
  echo "- [Add observations here]" >> "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"
fi

# Phase 4: Data Integrity
echo ""
echo "=== PHASE 4: Data Integrity Verification ==="
"$SCRIPT_DIR/verify-data-integrity.sh" "$ENV" >> "$REPORT_FILE" 2>&1

# Phase 5: Observability
echo ""
echo "=== PHASE 5: Observability Review ==="
"$SCRIPT_DIR/capture-metrics.sh" "$SCRIPT_DIR/rehearsal-metrics" >> "$REPORT_FILE" 2>&1

# Phase 6: Recovery
echo ""
echo "=== PHASE 6: Recovery Drill ==="
read -p "Perform full backend restart? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  "$SCRIPT_DIR/failure-injection.sh" full-backend-restart
  sleep 10
  echo "Verifying recovery..."
  curl -s -f "$API_URL/health" > /dev/null && echo "✓ Health check passed" || echo "❌ Health check failed"
  curl -s -f "$API_URL/v1/ready" > /dev/null && echo "✓ Ready check passed" || echo "❌ Ready check failed"
  
  echo "### Phase 6: Recovery Drill" >> "$REPORT_FILE"
  echo "- Full backend restart completed" >> "$REPORT_FILE"
  echo "- [Add recovery observations here]" >> "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"
fi

# Final summary
echo ""
echo "=== Rehearsal Complete ==="
echo "Report saved to: $REPORT_FILE"
echo ""
echo "Next steps:"
echo "  1. Review report: $REPORT_FILE"
echo "  2. Complete GO/NO-GO checklist"
echo "  3. Address any blockers before exam day"

cat >> "$REPORT_FILE" <<EOF

## GO/NO-GO Checklist

- [ ] Zero data loss verified
- [ ] No corrupted sessions
- [ ] p95 latency acceptable (< 500ms)
- [ ] Recovery tested and successful
- [ ] Logs sufficient for audit
- [ ] EXAM_MODE verified
- [ ] Failure scenarios handled gracefully

## Sign-Off

**Status**: [ ] GO  [ ] NO-GO

**Blockers**:
[List any blockers here]

**Sign-off by**: _________________  **Date**: _______________

EOF
