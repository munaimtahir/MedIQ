# Check formatting across the repository
# Usage: .\infra\scripts\format-check.ps1

$ErrorActionPreference = "Stop"

Write-Host "🔍 Checking frontend formatting..." -ForegroundColor Cyan
Push-Location frontend
npm run format:check
Pop-Location

Write-Host "🔍 Checking backend formatting..." -ForegroundColor Cyan
Push-Location backend
black --check .
ruff check .
Pop-Location

Write-Host "✅ All formatting checks passed!" -ForegroundColor Green

