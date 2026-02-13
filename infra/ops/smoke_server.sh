#!/bin/sh
set -eu

FRONTEND_URL="${FRONTEND_URL:-https://example.com/}"
BACKEND_DOMAIN_HEALTH_URL="${BACKEND_DOMAIN_HEALTH_URL:-https://example.com/api/health}"
BACKEND_LOCAL_HEALTH_URL="${BACKEND_LOCAL_HEALTH_URL:-http://127.0.0.1:8000/health}"

check() {
  name="$1"
  url="$2"
  code="$(curl -k -sS -o /dev/null -w '%{http_code}' "$url" || true)"
  if [ "$code" -ge 200 ] && [ "$code" -lt 400 ]; then
    echo "[OK] $name -> $url ($code)"
  else
    echo "[FAIL] $name -> $url (status=$code)" >&2
    exit 1
  fi
}

check "frontend" "$FRONTEND_URL"
check "backend-domain-health" "$BACKEND_DOMAIN_HEALTH_URL"
check "backend-local-health" "$BACKEND_LOCAL_HEALTH_URL"

echo "Smoke checks passed."
