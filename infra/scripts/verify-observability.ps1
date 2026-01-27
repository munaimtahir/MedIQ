# Verification script for observability stack (Tasks 157-161)
# Tests: OpenTelemetry traces, Prometheus metrics, Grafana dashboards, structured logging

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Observability Stack Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$ComposeFile = "infra/docker/compose/docker-compose.dev.yml"
$BackendService = "backend"
$PrometheusService = "prometheus"
$GrafanaService = "grafana"
$TempoService = "tempo"
$OtelCollectorService = "otel-collector"

# Check if services are running
Write-Host "1. Checking services are running..." -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow
docker compose -f $ComposeFile ps | Select-String -Pattern "($BackendService|$PrometheusService|$GrafanaService|$TempoService|$OtelCollectorService)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Some services are not running" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Services are running" -ForegroundColor Green
Write-Host ""

# Test OpenTelemetry traces
Write-Host "2. Testing OpenTelemetry traces..." -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow
Write-Host "Making test request to generate trace..."
$RequestId = "test-trace-$(Get-Date -Format 'yyyyMMddHHmmss')"
try {
    Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -Headers @{"X-Request-ID"=$RequestId} -UseBasicParsing | Out-Null
    Start-Sleep -Seconds 2
    
    Write-Host "Checking Tempo for traces..."
    $TempoResponse = Invoke-RestMethod -Uri "http://localhost:3200/api/search?limit=5" -ErrorAction SilentlyContinue
    if ($TempoResponse.traces.Count -gt 0) {
        Write-Host "✓ Traces found in Tempo (count: $($TempoResponse.traces.Count))" -ForegroundColor Green
    } else {
        Write-Host "⚠ No traces found yet (may need more requests)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not verify traces: $_" -ForegroundColor Yellow
}
Write-Host ""

# Test Prometheus metrics
Write-Host "3. Testing Prometheus metrics..." -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow
Write-Host "Checking Prometheus targets..."
try {
    $PromTargets = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets"
    $UpTargets = $PromTargets.data.activeTargets | Where-Object { $_.health -eq "up" }
    $JobNames = $UpTargets | ForEach-Object { $_.labels.job }
    
    if ($JobNames -contains "backend") {
        Write-Host "✓ Backend target is UP" -ForegroundColor Green
    } else {
        Write-Host "✗ Backend target not found or DOWN" -ForegroundColor Red
    }
    
    if ($JobNames -contains "postgres") {
        Write-Host "✓ PostgreSQL exporter target is UP" -ForegroundColor Green
    } else {
        Write-Host "⚠ PostgreSQL exporter target not found" -ForegroundColor Yellow
    }
    
    if ($JobNames -contains "redis") {
        Write-Host "✓ Redis exporter target is UP" -ForegroundColor Green
    } else {
        Write-Host "⚠ Redis exporter target not found" -ForegroundColor Yellow
    }
    
    Write-Host "Querying backend metrics..."
    $MetricsResponse = Invoke-WebRequest -Uri "http://localhost:8000/metrics" -UseBasicParsing
    $MetricsCount = ($MetricsResponse.Content | Select-String -Pattern "http_requests_total").Matches.Count
    if ($MetricsCount -gt 0) {
        Write-Host "✓ Backend metrics endpoint accessible (found $MetricsCount metrics)" -ForegroundColor Green
    } else {
        Write-Host "✗ Backend metrics endpoint not accessible" -ForegroundColor Red
    }
} catch {
    Write-Host "⚠ Could not verify Prometheus: $_" -ForegroundColor Yellow
}
Write-Host ""

# Test Grafana
Write-Host "4. Testing Grafana..." -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow
try {
    $GrafanaHealth = Invoke-WebRequest -Uri "http://localhost:3001/api/health" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($GrafanaHealth.StatusCode -eq 200) {
        Write-Host "✓ Grafana is accessible" -ForegroundColor Green
        
        $Cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin"))
        $Headers = @{Authorization = "Basic $Cred"}
        
        $DataSources = Invoke-RestMethod -Uri "http://localhost:3001/api/datasources" -Headers $Headers
        Write-Host "  Datasources configured: $($DataSources.Count)" -ForegroundColor Cyan
        
        $Dashboards = Invoke-RestMethod -Uri "http://localhost:3001/api/search?type=dash-db" -Headers $Headers
        Write-Host "  Dashboards loaded: $($Dashboards.Count)" -ForegroundColor Cyan
        
        if ($Dashboards.Count -ge 3) {
            Write-Host "✓ Expected dashboards are loaded" -ForegroundColor Green
        } else {
            Write-Host "⚠ Expected 3+ dashboards, found $($Dashboards.Count)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✗ Grafana is not accessible (HTTP $($GrafanaHealth.StatusCode))" -ForegroundColor Red
    }
} catch {
    Write-Host "⚠ Could not verify Grafana: $_" -ForegroundColor Yellow
}
Write-Host ""

# Test structured logging
Write-Host "5. Testing structured logging..." -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow
Write-Host "Making test request and checking logs..."
$TestRequestId = "test-log-$(Get-Date -Format 'yyyyMMddHHmmss')"
try {
    Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -Headers @{"X-Request-ID"=$TestRequestId} -UseBasicParsing | Out-Null
    Start-Sleep -Seconds 1
    
    $Logs = docker compose -f $ComposeFile logs $BackendService --tail=20
    $LogLine = $Logs | Select-String -Pattern $TestRequestId | Select-Object -First 1
    
    if ($LogLine -match '"event":"request.start"') {
        Write-Host "✓ Request lifecycle logs found (request.start)" -ForegroundColor Green
    } else {
        Write-Host "⚠ Request lifecycle logs not found in recent output" -ForegroundColor Yellow
    }
    
    if ($LogLine -match '"request_id"') {
        Write-Host "✓ Request ID correlation in logs" -ForegroundColor Green
    } else {
        Write-Host "✗ Request ID not found in logs" -ForegroundColor Red
    }
    
    $JsonLog = $Logs | Select-String -Pattern '^\{"event"' | Select-Object -First 1
    if ($JsonLog) {
        Write-Host "✓ JSON structured logs detected" -ForegroundColor Green
    } else {
        Write-Host "⚠ JSON structured logs not detected in recent output" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not verify logging: $_" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Verification Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services:"
Write-Host "  - OpenTelemetry Collector: Check docker compose ps"
Write-Host "  - Tempo: http://localhost:3200"
Write-Host "  - Prometheus: http://localhost:9090"
Write-Host "  - Grafana: http://localhost:3001 (admin/admin)"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. View traces in Tempo UI: http://localhost:3200"
Write-Host "  2. View metrics in Prometheus: http://localhost:9090"
Write-Host "  3. View dashboards in Grafana: http://localhost:3001"
Write-Host "  4. Check logs: docker compose -f $ComposeFile logs -f $BackendService"
Write-Host ""
Write-Host "Verification complete!" -ForegroundColor Green
