#!/bin/bash
# Staging Environment Deployment Script
# Usage: ./deploy-staging.sh [--migrate] [--rebuild]

set -e

COMPOSE_FILE="infra/docker/compose/docker-compose.prod.yml"
MIGRATE=false
REBUILD=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --migrate)
      MIGRATE=true
      shift
      ;;
    --rebuild)
      REBUILD=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--migrate] [--rebuild]"
      exit 1
      ;;
  esac
done

echo "=== Staging Environment Deployment ==="
echo ""

# Check if staging services are already running
if docker compose -f "$COMPOSE_FILE" ps postgres_staging 2>/dev/null | grep -q "Up"; then
  echo "⚠️  Staging services are already running"
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Step 1: Start infrastructure
echo "1. Starting staging infrastructure (postgres_staging, redis_staging)..."
docker compose -f "$COMPOSE_FILE" up -d postgres_staging redis_staging

# Wait for postgres to be healthy
echo "   Waiting for postgres_staging to be healthy..."
timeout=60
elapsed=0
while ! docker compose -f "$COMPOSE_FILE" ps postgres_staging | grep -q "healthy"; do
  sleep 2
  elapsed=$((elapsed + 2))
  if [ $elapsed -ge $timeout ]; then
    echo "   ❌ Timeout waiting for postgres_staging to be healthy"
    exit 1
  fi
done
echo "   ✓ postgres_staging is healthy"

# Step 2: Run migrations (if requested)
if [ "$MIGRATE" = true ]; then
  echo ""
  echo "2. Running database migrations..."
  docker compose -f "$COMPOSE_FILE" run --rm backend_staging alembic upgrade head
  echo "   ✓ Migrations completed"
fi

# Step 3: Start application services
echo ""
if [ "$REBUILD" = true ]; then
  echo "3. Rebuilding and starting staging application services..."
  docker compose -f "$COMPOSE_FILE" up -d --build backend_staging frontend_staging
else
  echo "3. Starting staging application services..."
  docker compose -f "$COMPOSE_FILE" up -d backend_staging frontend_staging
fi

# Wait for services to be ready
echo "   Waiting for services to start..."
sleep 5

# Step 4: Verify services are running
echo ""
echo "4. Verifying services..."
if docker compose -f "$COMPOSE_FILE" ps backend_staging | grep -q "Up"; then
  echo "   ✓ backend_staging is running"
else
  echo "   ❌ backend_staging failed to start"
  docker compose -f "$COMPOSE_FILE" logs backend_staging --tail=20
  exit 1
fi

if docker compose -f "$COMPOSE_FILE" ps frontend_staging | grep -q "Up"; then
  echo "   ✓ frontend_staging is running"
else
  echo "   ❌ frontend_staging failed to start"
  docker compose -f "$COMPOSE_FILE" logs frontend_staging --tail=20
  exit 1
fi

# Step 5: Check Traefik routers
echo ""
echo "5. Checking Traefik routers..."
if docker logs exam_platform_traefik --tail=50 2>&1 | grep -qi "staging"; then
  echo "   ✓ Staging routers detected in Traefik logs"
else
  echo "   ⚠️  No staging routers found in Traefik logs (may need a moment to register)"
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Staging URLs:"
echo "  Frontend: https://staging.\${DOMAIN}"
echo "  Backend:  https://api-staging.\${DOMAIN}"
echo ""
echo "Next steps:"
echo "  1. Verify DNS: dig staging.\${DOMAIN} +short"
echo "  2. Test access: curl https://api-staging.\${DOMAIN}/health"
echo "  3. Run smoke tests: ./infra/scripts/smoke-test-traefik.sh \${DOMAIN} --staging"
echo ""
