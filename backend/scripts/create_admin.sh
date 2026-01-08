#!/bin/bash
# Script to create admin user via Docker
# Run from project root: bash backend/scripts/create_admin.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

docker compose -f "$PROJECT_ROOT/infra/docker/compose/docker-compose.dev.yml" exec -T backend python scripts/create_admin.py "$@"
