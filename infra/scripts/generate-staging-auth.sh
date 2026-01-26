#!/bin/bash
# Generate Basic Auth credentials for staging
# Usage: ./generate-staging-auth.sh [USERNAME] [PASSWORD]

set -e

USERNAME=${1:-"staging_user"}
PASSWORD=${2:-""}

if [ -z "$PASSWORD" ]; then
  echo "Usage: $0 <USERNAME> <PASSWORD>"
  echo ""
  echo "Example:"
  echo "  $0 staging_user mySecurePassword123"
  echo ""
  echo "Or generate interactively:"
  read -p "Username: " USERNAME
  read -sp "Password: " PASSWORD
  echo ""
fi

# Check if htpasswd is available
if ! command -v htpasswd &> /dev/null; then
  echo "Error: htpasswd not found"
  echo ""
  echo "Install it:"
  echo "  Linux (Debian/Ubuntu): sudo apt-get install apache2-utils"
  echo "  Linux (RHEL/CentOS):   sudo yum install httpd-tools"
  echo "  macOS:                 brew install httpd"
  echo "  Windows:               Use Docker: docker run --rm httpd:alpine htpasswd -nbB $USERNAME $PASSWORD"
  exit 1
fi

# Generate bcrypt hash
HASH=$(htpasswd -nbB "$USERNAME" "$PASSWORD")

echo ""
echo "=== Basic Auth Credentials Generated ==="
echo ""
echo "Add this to your .env.staging or server environment:"
echo ""
echo "STAGING_BASIC_AUTH_USERS=\"$HASH\""
echo ""
echo "Note: If setting in shell, escape \$ signs:"
echo "  export STAGING_BASIC_AUTH_USERS=\"$HASH\""
echo ""
echo "Or in .env file (quotes are usually sufficient):"
echo "  STAGING_BASIC_AUTH_USERS=\"$HASH\""
echo ""
echo "After setting, restart Traefik:"
echo "  docker compose -f infra/docker/compose/docker-compose.prod.yml restart traefik"
echo ""
