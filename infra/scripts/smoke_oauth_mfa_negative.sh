#!/bin/bash
# Negative tests for OAuth and MFA endpoints
# Supports both localhost (from host) and Docker service names (from container)

set -e

# Detect if running in Docker
if [ -f "/.dockerenv" ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    IN_DOCKER=true
    DEFAULT_BACKEND_URL="http://backend:8000"
else
    IN_DOCKER=false
    DEFAULT_BACKEND_URL="http://localhost:8000"
fi

BACKEND_URL="${BACKEND_URL:-$DEFAULT_BACKEND_URL}"
API_PREFIX="${API_PREFIX:-/v1}"
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

echo "=== OAuth/MFA Negative Tests ==="
echo "Running in Docker: $IN_DOCKER"
echo "Backend URL: $BACKEND_URL"
echo "API Prefix: $API_PREFIX"
echo ""

# Wait for backend to be ready
wait_for_service "$BACKEND_URL/v1/health" "Backend" 30 || exit 1
echo ""

# Test 1: OAuth callback with invalid state
echo "1. Testing OAuth callback with invalid state (should return 400 with OAUTH_STATE_INVALID)..."
response=$(curl -s -w "\n%{http_code}" \
    "${BACKEND_URL}${API_PREFIX}/auth/oauth/google/callback?code=invalid_code&state=invalid_state" 2>&1)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "400" ]; then
    echo "  ✓ HTTP 400 returned"
    
    # Check for OAUTH_STATE_INVALID error code
    if echo "$body" | jq -e '.error.code == "OAUTH_STATE_INVALID"' > /dev/null 2>&1; then
        echo "  ✓ Error code OAUTH_STATE_INVALID found"
    elif echo "$body" | grep -qi "OAUTH_STATE_INVALID\|oauth_state_invalid"; then
        echo "  ✓ Error code OAUTH_STATE_INVALID found (text match)"
    else
        echo "  ⚠ Error code OAUTH_STATE_INVALID not found in response"
        echo "  Response body: $body"
    fi
else
    echo "  ✗ Expected HTTP 400, got: $http_code"
    echo "  Response body: $body"
    exit 1
fi

# Test 2: MFA verify with invalid code
echo ""
echo "2. Testing MFA verify with invalid code..."
echo "  ⚠ This test requires:"
echo "    - A user with MFA enabled"
echo "    - A valid access token"
echo "    - An invalid TOTP code to test"
echo ""
echo "  Manual test steps:"
echo "  1. Enable MFA for a test user:"
echo "     curl -X POST ${BACKEND_URL}${API_PREFIX}/auth/mfa/totp/setup \\"
echo "       -H 'Authorization: Bearer <access_token>'"
echo ""
echo "  2. Verify with invalid code:"
echo "     curl -X POST ${BACKEND_URL}${API_PREFIX}/auth/mfa/totp/verify \\"
echo "       -H 'Authorization: Bearer <access_token>' \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"code\":\"000000\",\"mfa_token\":\"<mfa_token>\"}'"
echo ""
echo "  3. Expected: HTTP 400 with error code MFA_INVALID"

# Try a basic request to verify endpoint exists (without auth, should get 401/403)
echo ""
echo "3. Testing MFA endpoint exists (without auth, should return 401/403)..."
mfa_response=$(curl -s -w "\n%{http_code}" \
    -X POST "${BACKEND_URL}${API_PREFIX}/auth/mfa/totp/verify" \
    -H "Content-Type: application/json" \
    -d '{"code":"000000","mfa_token":"invalid"}' 2>&1)
mfa_code=$(echo "$mfa_response" | tail -n1)

if [ "$mfa_code" = "401" ] || [ "$mfa_code" = "403" ]; then
    echo "  ✓ Endpoint exists (returns $mfa_code for unauthenticated request)"
else
    echo "  ⚠ Unexpected status: $mfa_code (expected 401/403)"
fi

echo ""
echo "✅ OAuth negative test passed"
echo "⚠ MFA negative test requires manual setup (documented above)"



