#!/bin/bash
# Verify Staging Environment Isolation
# Ensures staging is properly isolated from production

set -e

COMPOSE_FILE="infra/docker/compose/docker-compose.prod.yml"

echo "=== Staging Isolation Verification ==="
echo ""

ERRORS=0

# Check 1: Database URL
echo "1. Checking database isolation..."
DB_URL=$(docker compose -f "$COMPOSE_FILE" exec -T backend_staging env | grep "^DATABASE_URL=" | cut -d'=' -f2- || echo "")
if echo "$DB_URL" | grep -q "postgres_staging"; then
  echo "   ✓ Staging uses postgres_staging"
else
  echo "   ❌ Staging database URL incorrect: $DB_URL"
  ERRORS=$((ERRORS + 1))
fi

# Check 2: Redis URL
echo "2. Checking Redis isolation..."
REDIS_URL=$(docker compose -f "$COMPOSE_FILE" exec -T backend_staging env | grep "^REDIS_URL=" | cut -d'=' -f2- || echo "")
if echo "$REDIS_URL" | grep -q "redis_staging"; then
  echo "   ✓ Staging uses redis_staging"
else
  echo "   ❌ Staging Redis URL incorrect: $REDIS_URL"
  ERRORS=$((ERRORS + 1))
fi

# Check 3: JWT Secret (should be different)
echo "3. Checking JWT secret isolation..."
JWT_SECRET=$(docker compose -f "$COMPOSE_FILE" exec -T backend_staging env | grep "^JWT_SECRET=" | cut -d'=' -f2- || echo "")
JWT_SECRET_PROD=$(docker compose -f "$COMPOSE_FILE" exec -T backend env | grep "^JWT_SECRET=" | cut -d'=' -f2- || echo "")

if [ -n "$JWT_SECRET" ] && [ -n "$JWT_SECRET_PROD" ] && [ "$JWT_SECRET" != "$JWT_SECRET_PROD" ]; then
  echo "   ✓ Staging JWT_SECRET is different from production"
else
  echo "   ❌ Staging JWT_SECRET matches or is missing (security risk!)"
  ERRORS=$((ERRORS + 1))
fi

# Check 4: Token Pepper (should be different)
echo "4. Checking token pepper isolation..."
TOKEN_PEPPER=$(docker compose -f "$COMPOSE_FILE" exec -T backend_staging env | grep "^AUTH_TOKEN_PEPPER=" | cut -d'=' -f2- || echo "")
TOKEN_PEPPER_PROD=$(docker compose -f "$COMPOSE_FILE" exec -T backend env | grep "^AUTH_TOKEN_PEPPER=" | cut -d'=' -f2- || echo "")

if [ -n "$TOKEN_PEPPER" ] && [ -n "$TOKEN_PEPPER_PROD" ] && [ "$TOKEN_PEPPER" != "$TOKEN_PEPPER_PROD" ]; then
  echo "   ✓ Staging AUTH_TOKEN_PEPPER is different from production"
else
  echo "   ❌ Staging AUTH_TOKEN_PEPPER matches or is missing (security risk!)"
  ERRORS=$((ERRORS + 1))
fi

# Check 5: CORS Origins (should be staging domains)
echo "5. Checking CORS configuration..."
CORS_APP=$(docker compose -f "$COMPOSE_FILE" exec -T backend_staging env | grep "^CORS_ALLOW_ORIGINS_APP=" | cut -d'=' -f2- || echo "")
if echo "$CORS_APP" | grep -q "staging"; then
  echo "   ✓ Staging CORS allows staging domains"
else
  echo "   ⚠️  Staging CORS may not be configured correctly: $CORS_APP"
fi

# Check 6: Environment variable
echo "6. Checking environment variable..."
ENV=$(docker compose -f "$COMPOSE_FILE" exec -T backend_staging env | grep "^ENV=" | cut -d'=' -f2- || echo "")
if [ "$ENV" = "staging" ]; then
  echo "   ✓ ENV is set to 'staging'"
else
  echo "   ❌ ENV is not 'staging': $ENV"
  ERRORS=$((ERRORS + 1))
fi

# Check 7: Database connectivity test
echo "7. Testing database connectivity..."
if docker compose -f "$COMPOSE_FILE" exec -T backend_staging python -c "
from app.db.session import SessionLocal
from app.models.user import User
db = SessionLocal()
try:
    count = db.query(User).count()
    print(f'Connected to staging DB, found {count} users')
except Exception as e:
    print(f'Error: {e}')
    exit(1)
finally:
    db.close()
" 2>&1 | grep -q "Connected"; then
  echo "   ✓ Staging backend can connect to staging database"
else
  echo "   ❌ Staging backend cannot connect to staging database"
  ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
if [ $ERRORS -eq 0 ]; then
  echo "=== ✓ All isolation checks passed ==="
  exit 0
else
  echo "=== ❌ Found $ERRORS isolation issue(s) ==="
  echo ""
  echo "Please review the errors above and ensure:"
  echo "  1. Staging uses separate database (postgres_staging)"
  echo "  2. Staging uses separate Redis (redis_staging)"
  echo "  3. Staging uses different secrets (JWT_SECRET_STAGING, AUTH_TOKEN_PEPPER_STAGING)"
  echo "  4. Environment variables are correctly set"
  exit 1
fi
