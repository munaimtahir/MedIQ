#!/bin/bash
# Failure Injection Script for Exam-Day Rehearsal
# Simulates various failure scenarios during load testing

set -e

COMPOSE_FILE="infra/docker/compose/docker-compose.prod.yml"
SCENARIO=${1:-help}

case "$SCENARIO" in
  redis-stop)
    echo "=== Injecting Redis Failure ==="
    echo "Stopping Redis container for 60 seconds..."
    docker compose -f "$COMPOSE_FILE" stop redis
    sleep 60
    echo "Restarting Redis..."
    docker compose -f "$COMPOSE_FILE" start redis
    echo "✓ Redis failure injection complete"
    ;;
    
  redis-staging-stop)
    echo "=== Injecting Staging Redis Failure ==="
    echo "Stopping staging Redis container for 60 seconds..."
    docker compose -f "$COMPOSE_FILE" stop redis_staging
    sleep 60
    echo "Restarting staging Redis..."
    docker compose -f "$COMPOSE_FILE" start redis_staging
    echo "✓ Staging Redis failure injection complete"
    ;;
    
  backend-restart)
    echo "=== Injecting Backend Worker Restart ==="
    echo "Restarting one backend container..."
    docker compose -f "$COMPOSE_FILE" restart backend
    echo "✓ Backend restart complete"
    ;;
    
  backend-staging-restart)
    echo "=== Injecting Staging Backend Worker Restart ==="
    echo "Restarting one staging backend container..."
    docker compose -f "$COMPOSE_FILE" restart backend_staging
    echo "✓ Staging backend restart complete"
    ;;
    
  network-delay)
    echo "=== Injecting Network Delay ==="
    echo "Adding 500ms delay to backend container (requires tc/netem)..."
    BACKEND_CONTAINER=$(docker compose -f "$COMPOSE_FILE" ps -q backend)
    if [ -z "$BACKEND_CONTAINER" ]; then
      echo "❌ Backend container not found"
      exit 1
    fi
    docker exec "$BACKEND_CONTAINER" sh -c "
      apk add --no-cache iproute2 2>/dev/null || apt-get update && apt-get install -y iproute2 2>/dev/null || true
      tc qdisc add dev eth0 root netem delay 500ms 2>/dev/null || echo 'tc not available in container'
    " || echo "⚠️  Network delay injection requires host-level tc (use proxy instead)"
    echo "Delay will persist until container restart"
    ;;
    
  postgres-slow)
    echo "=== Injecting Postgres Slow Queries ==="
    echo "This requires manual intervention or pg_stat_statements manipulation"
    echo "Consider using: SELECT pg_sleep(1) in a transaction"
    ;;
    
  traefik-restart)
    echo "=== Injecting Traefik Restart ==="
    echo "⚠️  WARNING: This will cause brief service interruption"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      docker compose -f "$COMPOSE_FILE" restart traefik
      echo "✓ Traefik restart complete"
    fi
    ;;
    
  full-backend-restart)
    echo "=== Injecting Full Backend Restart ==="
    echo "Restarting all backend containers..."
    docker compose -f "$COMPOSE_FILE" restart backend backend_staging
    echo "✓ Full backend restart complete"
    ;;
    
  help|*)
    echo "Usage: $0 <scenario>"
    echo ""
    echo "Available scenarios:"
    echo "  redis-stop           - Stop Redis for 60s (production)"
    echo "  redis-staging-stop   - Stop Redis for 60s (staging)"
    echo "  backend-restart      - Restart backend container (production)"
    echo "  backend-staging-restart - Restart backend container (staging)"
    echo "  network-delay        - Add 500ms network delay (experimental)"
    echo "  postgres-slow        - Info about slow query injection"
    echo "  traefik-restart      - Restart Traefik (WARNING: brief interruption)"
    echo "  full-backend-restart - Restart all backend containers"
    echo ""
    echo "Example:"
    echo "  $0 redis-stop"
    exit 1
    ;;
esac
