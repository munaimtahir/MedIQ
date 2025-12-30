# Format all code in the repository
# Usage: .\infra\scripts\format-all.ps1

$ErrorActionPreference = "Stop"

Write-Host "🎨 Formatting frontend..." -ForegroundColor Cyan
Push-Location frontend
npm run format
Pop-Location

Write-Host "🎨 Formatting backend..." -ForegroundColor Cyan
Push-Location backend
black .
Pop-Location

Write-Host "✅ Formatting complete!" -ForegroundColor Green

