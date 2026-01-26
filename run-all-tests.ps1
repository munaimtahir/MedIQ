# Run all tests in Docker with no time limit and proper error checking
$ErrorActionPreference = "Stop"

$composeDir = "d:\PMC\New Exam Prep Site\infra\docker\compose"
$composeFile = "docker-compose.test.yml"

# Detect docker compose command (docker compose or docker-compose)
# Try docker compose first (newer Docker versions)
$useDockerCompose = $false
$null = docker compose version 2>&1
if ($LASTEXITCODE -eq 0 -or $?) {
    $useDockerCompose = $false
    Write-Host "Using: docker compose" -ForegroundColor Gray
} else {
    $null = docker-compose --version 2>&1
    if ($LASTEXITCODE -eq 0 -or $?) {
        $useDockerCompose = $true
        Write-Host "Using: docker-compose" -ForegroundColor Gray
    } else {
        Write-Host "Error: Neither 'docker compose' nor 'docker-compose' found!" -ForegroundColor Red
        Write-Host "Please install Docker Desktop or docker-compose" -ForegroundColor Red
        exit 1
    }
}

# Function to run docker compose commands
function Invoke-DockerCompose {
    param(
        [string[]]$Arguments
    )
    if ($useDockerCompose) {
        docker-compose $Arguments
    } else {
        docker compose $Arguments
    }
    return $LASTEXITCODE
}

# Set environment variables for backend tests
$env:TEST_DATABASE_NAME = "exam_platform_test"
$env:TEST_DATABASE_USER = "exam_user"
$env:TEST_DATABASE_PASSWORD = "test_password"
$env:CI = "true"

Write-Host "=== Running Backend Tests in Docker ===" -ForegroundColor Cyan
Set-Location $composeDir

# Clean up any existing containers first
Write-Host "Cleaning up any existing containers..." -ForegroundColor Yellow
Invoke-DockerCompose -Arguments @("-f", $composeFile, "--profile", "test", "down", "-v") 2>&1 | Out-Null

# Run backend tests
Write-Host "Starting backend tests..." -ForegroundColor Yellow
try {
    $backendExitCode = Invoke-DockerCompose -Arguments @("-f", $composeFile, "--profile", "test", "up", "--abort-on-container-exit", "--exit-code-from", "backend-test", "backend-test")
    if ($null -eq $backendExitCode) {
        $backendExitCode = $LASTEXITCODE
        if ($null -eq $backendExitCode) {
            $backendExitCode = if ($?) { 0 } else { 1 }
        }
    }
} catch {
    Write-Host "Error running backend tests: $_" -ForegroundColor Red
    $backendExitCode = 1
}

# Keep containers running for inspection (cleanup skipped)
Write-Host "`nBackend test containers are kept running for inspection." -ForegroundColor Yellow
Write-Host "To view logs: docker compose -f $composeFile --profile test logs backend-test" -ForegroundColor Cyan
Write-Host "To clean up: docker compose -f $composeFile --profile test down -v" -ForegroundColor Cyan

if ($backendExitCode -ne 0) {
    Write-Host "`nBackend tests failed with exit code $backendExitCode" -ForegroundColor Red
    Write-Host "Containers are still running. View logs with:" -ForegroundColor Yellow
    Write-Host "  docker compose -f $composeFile --profile test logs backend-test" -ForegroundColor Cyan
    Write-Host "  docker logs exam_platform_backend_test" -ForegroundColor Cyan
    Set-Location "d:\PMC\New Exam Prep Site"
    exit $backendExitCode
}

Write-Host "`n=== Running Frontend Tests in Docker ===" -ForegroundColor Cyan

# Clean up any existing containers first
Write-Host "Cleaning up any existing containers..." -ForegroundColor Yellow
Invoke-DockerCompose -Arguments @("-f", $composeFile, "--profile", "test", "down", "-v") 2>&1 | Out-Null

# Run frontend tests
Write-Host "Starting frontend tests..." -ForegroundColor Yellow
try {
    $frontendExitCode = Invoke-DockerCompose -Arguments @("-f", $composeFile, "--profile", "test", "up", "--abort-on-container-exit", "--exit-code-from", "frontend-test", "frontend-test")
    if ($null -eq $frontendExitCode) {
        $frontendExitCode = $LASTEXITCODE
        if ($null -eq $frontendExitCode) {
            $frontendExitCode = if ($?) { 0 } else { 1 }
        }
    }
} catch {
    Write-Host "Error running frontend tests: $_" -ForegroundColor Red
    $frontendExitCode = 1
}

# Keep containers running for inspection (cleanup skipped)
Write-Host "`nFrontend test containers are kept running for inspection." -ForegroundColor Yellow
Write-Host "To view logs: docker compose -f $composeFile --profile test logs frontend-test" -ForegroundColor Cyan
Write-Host "To clean up: docker compose -f $composeFile --profile test down -v" -ForegroundColor Cyan

if ($frontendExitCode -ne 0) {
    Write-Host "`nFrontend tests failed with exit code $frontendExitCode" -ForegroundColor Red
    Write-Host "Containers are still running. View logs with:" -ForegroundColor Yellow
    Write-Host "  docker compose -f $composeFile --profile test logs frontend-test" -ForegroundColor Cyan
    Write-Host "  docker logs exam_platform_frontend_test" -ForegroundColor Cyan
    Set-Location "d:\PMC\New Exam Prep Site"
    exit $frontendExitCode
}

Write-Host "`n=== All Tests Passed! ===" -ForegroundColor Green
Write-Host "`nContainers are kept running for inspection." -ForegroundColor Yellow
Write-Host "To clean up all test containers:" -ForegroundColor Cyan
Write-Host "  docker compose -f $composeFile --profile test down -v" -ForegroundColor Cyan
Set-Location "d:\PMC\New Exam Prep Site"
