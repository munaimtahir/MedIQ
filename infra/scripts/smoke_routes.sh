#!/bin/bash
# Smoke tests for route redirects (unauthenticated access)
# Supports both localhost (from host) and Docker service names (from container)

set -e

# Detect if running in Docker
if [ -f "/.dockerenv" ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    IN_DOCKER=true
    DEFAULT_FRONTEND_URL="http://frontend:3000"
else
    IN_DOCKER=false
    DEFAULT_FRONTEND_URL="http://localhost:3000"
fi

FRONTEND_URL="${FRONTEND_URL:-$DEFAULT_FRONTEND_URL}"
MAX_RETRIES=3

# Helper: wait for service with retry
wait_for_service() {
    local url=$1
    local name=$2
    local max_wait=${3:-60}
    local elapsed=0
    
    echo "Waiting for $name at $url..."
    while [ $elapsed -lt $max_wait ]; do
        if curl -sf "$url" -o /dev/null 2>/dev/null; then
            echo "  ✓ $name is ready"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo "  ... waiting ($elapsed/${max_wait}s)"
    done
    echo "  ✗ $name not ready after ${max_wait}s"
    return 1
}

echo "=== Route Redirect Smoke Tests ==="
echo "Running in Docker: $IN_DOCKER"
echo "Frontend URL: $FRONTEND_URL"
echo ""

# Wait for frontend to be ready
wait_for_service "$FRONTEND_URL" "Frontend" 60 || exit 1
echo ""

# Test unauthenticated access to /student/dashboard
echo "1. Testing /student/dashboard (should redirect to /login)..."
response=$(curl -sI "$FRONTEND_URL/student/dashboard" 2>&1)
status_code=$(echo "$response" | head -n1 | grep -oP '\d{3}' | head -n1)
location=$(echo "$response" | grep -i "location:" | cut -d' ' -f2- | tr -d '\r')

if [ "$status_code" = "302" ] || [ "$status_code" = "307" ] || [ "$status_code" = "308" ]; then
    if echo "$location" | grep -q "/login"; then
        echo "✓ Redirect to /login (status: $status_code)"
    else
        echo "✗ Unexpected redirect location: $location (expected /login)"
        exit 1
    fi
else
    echo "✗ Expected redirect (302/307/308), got status: $status_code"
    exit 1
fi

# Test unauthenticated access to /admin
echo ""
echo "2. Testing /admin (should redirect to /login)..."
response=$(curl -sI "$FRONTEND_URL/admin" 2>&1)
status_code=$(echo "$response" | head -n1 | grep -oP '\d{3}' | head -n1)
location=$(echo "$response" | grep -i "location:" | cut -d' ' -f2- | tr -d '\r')

if [ "$status_code" = "302" ] || [ "$status_code" = "307" ] || [ "$status_code" = "308" ]; then
    if echo "$location" | grep -q "/login"; then
        echo "✓ Redirect to /login (status: $status_code)"
    else
        echo "✗ Unexpected redirect location: $location (expected /login)"
        exit 1
    fi
else
    echo "✗ Expected redirect (302/307/308), got status: $status_code"
    exit 1
fi

echo ""
echo "✅ All route redirect tests passed"


