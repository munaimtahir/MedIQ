#!/bin/bash
# Check formatting across the repository
# Usage: ./infra/scripts/format-check.sh

set -e

echo "🔍 Checking frontend formatting..."
cd frontend
npm run format:check
cd ..

echo "🔍 Checking backend formatting..."
cd backend
black --check .
ruff check .
cd ..

echo "✅ All formatting checks passed!"

