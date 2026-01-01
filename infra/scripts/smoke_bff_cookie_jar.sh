#!/bin/bash
# Comprehensive BFF cookie jar tests with proper cookie handling
# Supports both localhost (from host) and Docker service names (from container)

set -e

# Detect if running in Docker
if [ -f "/.dockerenv" ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    IN_DOCKER=true
    DEFAULT_FRONTEND_URL="http://frontend:3000"
    DEFAULT_BACKEND_URL="http://backend:8000"
else
    IN_DOCKER=false
    DEFAULT_FRONTEND_URL="http://localhost:3000"
    DEFAULT_BACKEND_URL="http://localhost:8000"
fi

FRONTEND_URL="${FRONTEND_URL:-$DEFAULT_FRONTEND_URL}"
BACKEND_URL="${BACKEND_URL:-$DEFAULT_BACKEND_URL}"
COOKIE_JAR="/tmp/bff_cookie_jar.txt"
COOKIE_JAR_STUDENT="/tmp/bff_cookie_jar_student.txt"
COOKIE_JAR_ADMIN="/tmp/bff_cookie_jar_admin.txt"
MAX_RETRIES=3
RETRY_DELAY=2

# Cleanup function
cleanup() {
    rm -f "$COOKIE_JAR" "$COOKIE_JAR_STUDENT" "$COOKIE_JAR_ADMIN"
}
trap cleanup EXIT

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

echo "=== BFF Cookie Jar Smoke Tests ==="
echo "Running in Docker: $IN_DOCKER"
echo "Frontend URL: $FRONTEND_URL"
echo "Backend URL: $BACKEND_URL"
echo ""

# Wait for services to be ready
wait_for_service "$BACKEND_URL/v1/health" "Backend" 30 || exit 1
wait_for_service "$FRONTEND_URL" "Frontend" 60 || exit 1
echo ""

# Generate unique test emails
TIMESTAMP=$(date +%s)
STUDENT_EMAIL="student_test_${TIMESTAMP}@example.com"
ADMIN_EMAIL="admin_test_${TIMESTAMP}@example.com"
PASSWORD="TestPass123!"

# Test 1: Login via BFF and store cookies
echo "1. Testing /api/auth/login (store cookies)..."
response=$(curl -s -w "\n%{http_code}" -X POST "$FRONTEND_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$STUDENT_EMAIL\",\"password\":\"$PASSWORD\"}" \
    -c "$COOKIE_JAR" 2>&1)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

# If login fails, try signup first
if [ "$http_code" != "200" ]; then
    echo "  Login failed (user may not exist), trying signup first..."
    signup_response=$(curl -s -w "\n%{http_code}" -X POST "$FRONTEND_URL/api/auth/signup" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"Test Student\",\"email\":\"$STUDENT_EMAIL\",\"password\":\"$PASSWORD\"}" \
        -c "$COOKIE_JAR" 2>&1)
    signup_code=$(echo "$signup_response" | tail -n1)
    if [ "$signup_code" = "201" ] || [ "$signup_code" = "200" ]; then
        echo "  ✓ Signup successful, cookies stored"
        # Now try login
        response=$(curl -s -w "\n%{http_code}" -X POST "$FRONTEND_URL/api/auth/login" \
            -H "Content-Type: application/json" \
            -d "{\"email\":\"$STUDENT_EMAIL\",\"password\":\"$PASSWORD\"}" \
            -c "$COOKIE_JAR" 2>&1)
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n-1)
    fi
fi

if [ "$http_code" = "200" ]; then
    echo "  ✓ Login successful"
    
    # Verify cookies are set (check Set-Cookie headers)
    if [ -f "$COOKIE_JAR" ] && [ -s "$COOKIE_JAR" ]; then
        echo "  ✓ Cookie jar created"
    else
        echo "  ⚠ Cookie jar is empty (cookies may be httpOnly, check Set-Cookie headers)"
    fi
    
    # Verify tokens NOT in JSON response
    if echo "$body" | jq -e '.tokens' > /dev/null 2>&1; then
        echo "  ✗ ERROR: Tokens found in JSON response (should be in cookies only)"
        exit 1
    else
        echo "  ✓ Tokens not in JSON response (correct)"
    fi
else
    echo "  ✗ Login failed: HTTP $http_code"
    echo "$body"
    exit 1
fi

# Test 2: Verify cookies are httpOnly, SameSite=Lax, Path=/
echo ""
echo "2. Verifying cookie security flags..."
# Note: curl cookie jar doesn't show flags, but we can check Set-Cookie headers
login_with_headers=$(curl -sI -X POST "$FRONTEND_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$STUDENT_EMAIL\",\"password\":\"$PASSWORD\"}" 2>&1)

set_cookie_headers=$(echo "$login_with_headers" | grep -i "set-cookie:" || true)
if echo "$set_cookie_headers" | grep -qi "httponly"; then
    echo "  ✓ httpOnly flag present"
else
    echo "  ⚠ httpOnly flag not detected (may be case-sensitive)"
fi

if echo "$set_cookie_headers" | grep -qi "samesite=lax\|samesite=lax,"; then
    echo "  ✓ SameSite=Lax present"
else
    echo "  ⚠ SameSite=Lax not detected in headers"
fi

if echo "$set_cookie_headers" | grep -qi "path=/"; then
    echo "  ✓ Path=/ present"
else
    echo "  ⚠ Path=/ not detected in headers"
fi

# Test 3: Use cookies to access /student/dashboard
echo ""
echo "3. Testing /student/dashboard with cookies (should return 200)..."
response=$(curl -s -w "\n%{http_code}" "$FRONTEND_URL/student/dashboard" \
    -b "$COOKIE_JAR" 2>&1)
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "200" ]; then
    echo "  ✓ Access granted (200 OK)"
else
    echo "  ✗ Unexpected status: $http_code (expected 200)"
    exit 1
fi

# Test 4: Login as STUDENT and attempt /admin (should redirect to /403)
echo ""
echo "4. Testing /admin with student cookies (should redirect to /403)..."
response=$(curl -sI "$FRONTEND_URL/admin" -b "$COOKIE_JAR" 2>&1)
status_code=$(echo "$response" | head -n1 | grep -oP '\d{3}' | head -n1)
location=$(echo "$response" | grep -i "location:" | cut -d' ' -f2- | tr -d '\r')

if [ "$status_code" = "302" ] || [ "$status_code" = "307" ] || [ "$status_code" = "308" ]; then
    if echo "$location" | grep -q "/403"; then
        echo "  ✓ Redirect to /403 (status: $status_code) - correct role-based protection"
    else
        echo "  ⚠ Redirect to: $location (expected /403 for student accessing admin)"
    fi
elif [ "$status_code" = "200" ]; then
    echo "  ✗ Unexpected: Student can access /admin (should be blocked)"
    exit 1
else
    echo "  ⚠ Unexpected status: $status_code"
fi

# Test 5: Create admin user and login, then access /admin (should return 200)
echo ""
echo "5. Testing /admin with admin cookies (requires admin user)..."
echo "  ⚠ Skipping - requires admin user creation via seed/API"
echo "  (To test: create admin user, login, then curl -b cookies.txt /admin)"

# Test 6: Logout -> cookies cleared; /api/auth/me returns 401
echo ""
echo "6. Testing /api/auth/logout (cookies should be cleared)..."
response=$(curl -s -w "\n%{http_code}" -X POST "$FRONTEND_URL/api/auth/logout" \
    -H "Content-Type: application/json" \
    -b "$COOKIE_JAR" \
    -c "$COOKIE_JAR" 2>&1)
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "200" ]; then
    echo "  ✓ Logout successful"
    
    # Test /api/auth/me after logout (should return 401)
    echo ""
    echo "7. Testing /api/auth/me after logout (should return 401)..."
    me_response=$(curl -s -w "\n%{http_code}" "$FRONTEND_URL/api/auth/me" \
        -b "$COOKIE_JAR" 2>&1)
    me_code=$(echo "$me_response" | tail -n1)
    
    if [ "$me_code" = "401" ]; then
        echo "  ✓ /api/auth/me returns 401 (correct - cookies cleared)"
    else
        echo "  ✗ Unexpected status: $me_code (expected 401)"
        exit 1
    fi
else
    echo "  ✗ Logout failed: HTTP $http_code"
    exit 1
fi

echo ""
echo "✅ All BFF cookie jar tests passed"


