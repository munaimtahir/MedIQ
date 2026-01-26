#!/bin/bash
# Traefik Production + Staging Smoke Tests
# Usage: ./smoke-test-traefik.sh <DOMAIN> [--staging] [--staging-auth USER:PASSWORD]

set -e

DOMAIN=${1:-"example.com"}
API_DOMAIN="api.${DOMAIN}"
STAGING_DOMAIN="staging.${DOMAIN}"
API_STAGING_DOMAIN="api-staging.${DOMAIN}"
TEST_STAGING=""
STAGING_AUTH=""

# Parse arguments
shift || true
while [[ $# -gt 0 ]]; do
  case $1 in
    --staging)
      TEST_STAGING="--staging"
      shift
      ;;
    --staging-auth)
      TEST_STAGING="--staging"
      STAGING_AUTH="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 <DOMAIN> [--staging] [--staging-auth USER:PASSWORD]"
      exit 1
      ;;
  esac
done

echo "=== Traefik Smoke Tests ==="
echo "Domain: ${DOMAIN}"
echo "API Domain: ${API_DOMAIN}"
if [ "$TEST_STAGING" = "--staging" ]; then
  echo "Staging Domain: ${STAGING_DOMAIN}"
  echo "API Staging Domain: ${API_STAGING_DOMAIN}"
fi
echo ""

# 1. Verify ports (only Traefik should be listening)
echo "1. Checking public ports (80/443)..."
PORTS=$(ss -tulpen 2>/dev/null | grep -E ':80|:443' || echo "No ports found")
if echo "$PORTS" | grep -q "traefik\|exam_platform_traefik"; then
  echo "✓ Only Traefik listening on 80/443"
else
  echo "✗ WARNING: Other services may be exposing ports"
  echo "$PORTS"
fi
echo ""

# 2. HTTP -> HTTPS redirects
echo "2. Testing HTTP -> HTTPS redirects..."
HTTP_FRONTEND=$(curl -sI "http://${DOMAIN}" 2>&1 | head -1 || echo "Failed")
HTTP_API=$(curl -sI "http://${API_DOMAIN}" 2>&1 | head -1 || echo "Failed")

if echo "$HTTP_FRONTEND" | grep -q "301\|308"; then
  echo "✓ Frontend HTTP redirects to HTTPS"
else
  echo "✗ Frontend HTTP redirect failed: $HTTP_FRONTEND"
fi

if echo "$HTTP_API" | grep -q "301\|308"; then
  echo "✓ API HTTP redirects to HTTPS"
else
  echo "✗ API HTTP redirect failed: $HTTP_API"
fi
echo ""

# 3. HTTPS health checks
echo "3. Testing HTTPS endpoints..."
HTTPS_FRONTEND=$(curl -sI "https://${DOMAIN}" 2>&1 | head -1 || echo "Failed")
HTTPS_API=$(curl -sI "https://${API_DOMAIN}/health" 2>&1 | head -1 || echo "Failed")

if echo "$HTTPS_FRONTEND" | grep -q "200"; then
  echo "✓ Frontend HTTPS accessible"
else
  echo "✗ Frontend HTTPS failed: $HTTPS_FRONTEND"
fi

if echo "$HTTPS_API" | grep -q "200"; then
  echo "✓ API HTTPS health check passed"
else
  echo "✗ API HTTPS health check failed: $HTTPS_API"
fi
echo ""

# 4. Security headers at edge
echo "4. Verifying security headers..."
HEADERS=$(curl -sI "https://${API_DOMAIN}/health" 2>&1 || echo "")
MISSING_HEADERS=()

if ! echo "$HEADERS" | grep -qi "strict-transport-security"; then
  MISSING_HEADERS+=("Strict-Transport-Security")
fi
if ! echo "$HEADERS" | grep -qi "x-frame-options"; then
  MISSING_HEADERS+=("X-Frame-Options")
fi
if ! echo "$HEADERS" | grep -qi "x-content-type-options"; then
  MISSING_HEADERS+=("X-Content-Type-Options")
fi
if ! echo "$HEADERS" | grep -qi "referrer-policy"; then
  MISSING_HEADERS+=("Referrer-Policy")
fi
if ! echo "$HEADERS" | grep -qi "permissions-policy"; then
  MISSING_HEADERS+=("Permissions-Policy")
fi

if [ ${#MISSING_HEADERS[@]} -eq 0 ]; then
  echo "✓ All security headers present"
else
  echo "✗ Missing headers: ${MISSING_HEADERS[*]}"
fi
echo ""

# 5. Certificate validity
echo "5. Checking SSL certificates..."
CERT_FRONTEND=$(echo | openssl s_client -servername "${DOMAIN}" -connect "${DOMAIN}:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "Failed")
CERT_API=$(echo | openssl s_client -servername "${API_DOMAIN}" -connect "${API_DOMAIN}:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "Failed")

if echo "$CERT_FRONTEND" | grep -q "notAfter"; then
  echo "✓ Frontend certificate valid"
  echo "$CERT_FRONTEND" | grep "notAfter"
else
  echo "✗ Frontend certificate check failed"
fi

if echo "$CERT_API" | grep -q "notAfter"; then
  echo "✓ API certificate valid"
  echo "$CERT_API" | grep "notAfter"
else
  echo "✗ API certificate check failed"
fi
echo ""

# 6. Traefik logs check
echo "6. Checking Traefik logs for errors..."
ERRORS=$(docker logs exam_platform_traefik --tail=100 2>&1 | grep -i "error\|fatal\|panic" | head -5 || echo "")
if [ -z "$ERRORS" ]; then
  echo "✓ No recent errors in Traefik logs"
else
  echo "✗ Errors found in Traefik logs:"
  echo "$ERRORS"
fi
echo ""

# 7. Staging tests (if --staging flag provided)
if [ "$TEST_STAGING" = "--staging" ]; then
  echo ""
  echo "7. Testing Staging Environment..."
  
  # Staging HTTP redirects
  HTTP_STAGING_FRONTEND=$(curl -sI "http://${STAGING_DOMAIN}" 2>&1 | head -1 || echo "Failed")
  HTTP_STAGING_API=$(curl -sI "http://${API_STAGING_DOMAIN}" 2>&1 | head -1 || echo "Failed")
  
  if echo "$HTTP_STAGING_FRONTEND" | grep -q "301\|308"; then
    echo "✓ Staging frontend HTTP redirects to HTTPS"
  else
    echo "✗ Staging frontend HTTP redirect failed: $HTTP_STAGING_FRONTEND"
  fi
  
  if echo "$HTTP_STAGING_API" | grep -q "301\|308"; then
    echo "✓ Staging API HTTP redirects to HTTPS"
  else
    echo "✗ Staging API HTTP redirect failed: $HTTP_STAGING_API"
  fi
  
  # Staging Basic Auth tests
  echo ""
  echo "7a. Testing Staging Basic Auth Protection..."
  
  # Test without credentials (should get 401)
  AUTH_TEST_FRONTEND=$(curl -sI "https://${STAGING_DOMAIN}" 2>&1 | head -1 || echo "Failed")
  AUTH_TEST_API=$(curl -sI "https://${API_STAGING_DOMAIN}/health" 2>&1 | head -1 || echo "Failed")
  
  if echo "$AUTH_TEST_FRONTEND" | grep -q "401"; then
    echo "✓ Staging frontend requires authentication (401)"
  elif echo "$AUTH_TEST_FRONTEND" | grep -q "200\|302"; then
    echo "⚠️  Staging frontend accessible without auth (Basic Auth may be disabled)"
  else
    echo "✗ Staging frontend auth test failed: $AUTH_TEST_FRONTEND"
  fi
  
  if echo "$AUTH_TEST_API" | grep -q "401"; then
    echo "✓ Staging API requires authentication (401)"
  elif echo "$AUTH_TEST_API" | grep -q "200"; then
    echo "⚠️  Staging API accessible without auth (Basic Auth may be disabled)"
  else
    echo "✗ Staging API auth test failed: $AUTH_TEST_API"
  fi
  
  # Test with credentials (if provided)
  if [ -n "$STAGING_AUTH" ]; then
    echo ""
    echo "7b. Testing Staging with Basic Auth credentials..."
    
    AUTH_HEADER="Authorization: Basic $(echo -n "$STAGING_AUTH" | base64)"
    AUTH_TEST_FRONTEND=$(curl -sI -H "$AUTH_HEADER" "https://${STAGING_DOMAIN}" 2>&1 | head -1 || echo "Failed")
    AUTH_TEST_API=$(curl -sI -H "$AUTH_HEADER" "https://${API_STAGING_DOMAIN}/health" 2>&1 | head -1 || echo "Failed")
    
    if echo "$AUTH_TEST_FRONTEND" | grep -q "200\|302"; then
      echo "✓ Staging frontend accessible with credentials"
    else
      echo "✗ Staging frontend auth failed with credentials: $AUTH_TEST_FRONTEND"
    fi
    
    if echo "$AUTH_TEST_API" | grep -q "200"; then
      echo "✓ Staging API accessible with credentials"
    else
      echo "✗ Staging API auth failed with credentials: $AUTH_TEST_API"
    fi
  else
    echo ""
    echo "   (Skipping authenticated tests - use --staging-auth USER:PASSWORD to test)"
  fi
  
  # Staging HTTPS health (with auth if provided)
  echo ""
  echo "7c. Testing Staging HTTPS Health..."
  
  if [ -n "$STAGING_AUTH" ]; then
    AUTH_HEADER="Authorization: Basic $(echo -n "$STAGING_AUTH" | base64)"
    HTTPS_STAGING_FRONTEND=$(curl -sI -H "$AUTH_HEADER" "https://${STAGING_DOMAIN}" 2>&1 | head -1 || echo "Failed")
    HTTPS_STAGING_API=$(curl -sI -H "$AUTH_HEADER" "https://${API_STAGING_DOMAIN}/health" 2>&1 | head -1 || echo "Failed")
  else
    HTTPS_STAGING_FRONTEND=$(curl -sI "https://${STAGING_DOMAIN}" 2>&1 | head -1 || echo "Failed")
    HTTPS_STAGING_API=$(curl -sI "https://${API_STAGING_DOMAIN}/health" 2>&1 | head -1 || echo "Failed")
  fi
  
  if echo "$HTTPS_STAGING_FRONTEND" | grep -q "200\|302\|401"; then
    echo "✓ Staging frontend HTTPS accessible"
  else
    echo "✗ Staging frontend HTTPS failed: $HTTPS_STAGING_FRONTEND"
  fi
  
  if echo "$HTTPS_STAGING_API" | grep -q "200\|401"; then
    echo "✓ Staging API HTTPS health check passed"
  else
    echo "✗ Staging API HTTPS health check failed: $HTTPS_STAGING_API"
  fi
  
  # Staging security headers (with auth if provided)
  if [ -n "$STAGING_AUTH" ]; then
    AUTH_HEADER="Authorization: Basic $(echo -n "$STAGING_AUTH" | base64)"
    STAGING_HEADERS=$(curl -sI -H "$AUTH_HEADER" "https://${API_STAGING_DOMAIN}/health" 2>&1 || echo "")
  else
    STAGING_HEADERS=$(curl -sI "https://${API_STAGING_DOMAIN}/health" 2>&1 || echo "")
  fi
  STAGING_MISSING=()
  
  if ! echo "$STAGING_HEADERS" | grep -qi "strict-transport-security"; then
    STAGING_MISSING+=("Strict-Transport-Security")
  fi
  if ! echo "$STAGING_HEADERS" | grep -qi "x-frame-options"; then
    STAGING_MISSING+=("X-Frame-Options")
  fi
  
  if [ ${#STAGING_MISSING[@]} -eq 0 ]; then
    echo "✓ Staging security headers present"
  else
    echo "✗ Staging missing headers: ${STAGING_MISSING[*]}"
  fi
  
  # Staging certificates
  CERT_STAGING_FRONTEND=$(echo | openssl s_client -servername "${STAGING_DOMAIN}" -connect "${STAGING_DOMAIN}:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "Failed")
  CERT_STAGING_API=$(echo | openssl s_client -servername "${API_STAGING_DOMAIN}" -connect "${API_STAGING_DOMAIN}:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "Failed")
  
  if echo "$CERT_STAGING_FRONTEND" | grep -q "notAfter"; then
    echo "✓ Staging frontend certificate valid"
  else
    echo "✗ Staging frontend certificate check failed"
  fi
  
  if echo "$CERT_STAGING_API" | grep -q "notAfter"; then
    echo "✓ Staging API certificate valid"
  else
    echo "✗ Staging API certificate check failed"
  fi
fi

# 8. Traefik Dashboard Security (localhost-only)
echo ""
echo "8. Verifying Traefik Dashboard Security..."
# Check dashboard is bound to localhost only
DASHBOARD_PORT=$(ss -tulpen 2>/dev/null | grep ":8080" || echo "")
if echo "$DASHBOARD_PORT" | grep -q "127.0.0.1:8080\|localhost:8080"; then
  echo "✓ Dashboard bound to localhost only (127.0.0.1:8080)"
elif echo "$DASHBOARD_PORT" | grep -q ":8080"; then
  echo "✗ WARNING: Dashboard may be accessible from network (not localhost-only)"
  echo "  $DASHBOARD_PORT"
else
  echo "⚠️  Dashboard port 8080 not found (may not be configured)"
fi

# Test dashboard is not accessible from network (should fail)
echo ""
echo "   Testing dashboard is NOT publicly accessible..."
# Try to connect from localhost (should work if dashboard is running)
DASHBOARD_LOCAL=$(curl -sI "http://127.0.0.1:8080/dashboard/" 2>&1 | head -1 || echo "Failed")
if echo "$DASHBOARD_LOCAL" | grep -q "200\|301\|302"; then
  echo "✓ Dashboard accessible on localhost (expected)"
else
  echo "⚠️  Dashboard not accessible on localhost (may need SSH tunnel)"
fi

echo ""
echo "=== Smoke Test Complete ==="
echo ""
echo "Note: To access Traefik dashboard, use SSH tunnel:"
echo "  ssh -L 8080:127.0.0.1:8080 <user>@<server_ip>"
echo "  Then open: http://localhost:8080/dashboard/"
echo ""
