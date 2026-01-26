#!/bin/bash
# Data Integrity Verification Script
# Runs SQL checks after exam-day rehearsal

set -e

COMPOSE_FILE="infra/docker/compose/docker-compose.prod.yml"
ENV=${1:-prod} # prod or staging

if [ "$ENV" = "staging" ]; then
  DB_CONTAINER="exam_platform_postgres_staging"
  DB_USER="${POSTGRES_USER_STAGING:-exam_user_staging}"
  DB_NAME="${POSTGRES_DB_STAGING:-exam_platform_staging}"
else
  DB_CONTAINER="exam_platform_postgres"
  DB_USER="${POSTGRES_USER:-exam_user}"
  DB_NAME="${POSTGRES_DB:-exam_platform}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="$SCRIPT_DIR/verify-data-integrity.sql"

echo "=== Data Integrity Verification ($ENV) ==="
echo "Database: $DB_CONTAINER"
echo ""

# Check if container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
  echo "❌ Database container $DB_CONTAINER is not running"
  exit 1
fi

# Run verification queries
echo "Running integrity checks..."
docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$SQL_FILE"

echo ""
echo "=== Verification Complete ==="
echo ""
echo "Review the output above for any issues."
echo "Expected: All queries should return 0 rows (no issues found)."
