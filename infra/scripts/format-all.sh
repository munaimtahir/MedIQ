#!/bin/bash
# Format all code in the repository
# Usage: ./infra/scripts/format-all.sh

set -e

echo "🎨 Formatting frontend..."
cd frontend
npm run format
cd ..

echo "🎨 Formatting backend..."
cd backend
black .
cd ..

echo "✅ Formatting complete!"

