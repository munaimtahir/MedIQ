#!/bin/bash
# Verification script for observability stack (Tasks 157-161)
# Tests: OpenTelemetry traces, Prometheus metrics, Grafana dashboards, structured logging

set -e

echo "=========================================="
echo "Observability Stack Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

COMPOSE_FILE="infra/docker/compose/docker-compose.dev.yml"
BACKEND_SERVICE="backend"
PROMETHEUS_SERVICE="prometheus"
GRAFANA_SERVICE="grafana"
TEMPO_SERVICE="tempo"
OTEL_COLLECTOR_SERVICE="otel-collector"

# Check if services are running
echo "1. Checking services are running..."
echo "-----------------------------------"
docker compose -f "$COMPOSE_FILE" ps | grep -E "($BACKEND_SERVICE|$PROMETHEUS_SERVICE|$GRAFANA_SERVICE|$TEMPO_SERVICE|$OTEL_COLLECTOR_SERVICE)" || {
    echo -e "${RED}ERROR: Some services are not running${NC}"
    exit 1
}
echo -e "${GREEN}✓ Services are running${NC}"
echo ""

# Test OpenTelemetry traces
echo "2. Testing OpenTelemetry traces..."
echo "-----------------------------------"
echo "Making test request to generate trace..."
REQUEST_ID="test-trace-$(date +%s)"
curl -s -X GET "http://localhost:8000/health" \
    -H "X-Request-ID: $REQUEST_ID" > /dev/null

sleep 2  # Wait for trace to be exported

echo "Checking Tempo for traces..."
TEMPO_TRACES=$(curl -s "http://localhost:3200/api/search?limit=5" | jq -r '.traces | length' 2>/dev/null || echo "0")
if [ "$TEMPO_TRACES" -gt "0" ]; then
    echo -e "${GREEN}✓ Traces found in Tempo (count: $TEMPO_TRACES)${NC}"
else
    echo -e "${YELLOW}⚠ No traces found yet (may need more requests)${NC}"
fi
echo ""

# Test Prometheus metrics
echo "3. Testing Prometheus metrics..."
echo "-----------------------------------"
echo "Checking Prometheus targets..."
PROM_TARGETS=$(curl -s "http://localhost:9090/api/v1/targets" | jq -r '.data.activeTargets[] | select(.health=="up") | .labels.job' 2>/dev/null || echo "")
if echo "$PROM_TARGETS" | grep -q "backend"; then
    echo -e "${GREEN}✓ Backend target is UP${NC}"
else
    echo -e "${RED}✗ Backend target not found or DOWN${NC}"
fi

if echo "$PROM_TARGETS" | grep -q "postgres"; then
    echo -e "${GREEN}✓ PostgreSQL exporter target is UP${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL exporter target not found${NC}"
fi

if echo "$PROM_TARGETS" | grep -q "redis"; then
    echo -e "${GREEN}✓ Redis exporter target is UP${NC}"
else
    echo -e "${YELLOW}⚠ Redis exporter target not found${NC}"
fi

echo "Querying backend metrics..."
BACKEND_METRICS=$(curl -s "http://localhost:8000/metrics" | grep -c "http_requests_total" || echo "0")
if [ "$BACKEND_METRICS" -gt "0" ]; then
    echo -e "${GREEN}✓ Backend metrics endpoint accessible (found $BACKEND_METRICS metrics)${NC}"
else
    echo -e "${RED}✗ Backend metrics endpoint not accessible${NC}"
fi
echo ""

# Test Grafana
echo "4. Testing Grafana..."
echo "-----------------------------------"
GRAFANA_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3001/api/health" || echo "000")
if [ "$GRAFANA_HEALTH" = "200" ]; then
    echo -e "${GREEN}✓ Grafana is accessible${NC}"
    
    # Check datasources
    DS_COUNT=$(curl -s -u admin:admin "http://localhost:3001/api/datasources" | jq -r 'length' 2>/dev/null || echo "0")
    echo "  Datasources configured: $DS_COUNT"
    
    # Check dashboards
    DASHBOARD_COUNT=$(curl -s -u admin:admin "http://localhost:3001/api/search?type=dash-db" | jq -r 'length' 2>/dev/null || echo "0")
    echo "  Dashboards loaded: $DASHBOARD_COUNT"
    
    if [ "$DASHBOARD_COUNT" -ge "3" ]; then
        echo -e "${GREEN}✓ Expected dashboards are loaded${NC}"
    else
        echo -e "${YELLOW}⚠ Expected 3+ dashboards, found $DASHBOARD_COUNT${NC}"
    fi
else
    echo -e "${RED}✗ Grafana is not accessible (HTTP $GRAFANA_HEALTH)${NC}"
fi
echo ""

# Test structured logging
echo "5. Testing structured logging..."
echo "-----------------------------------"
echo "Making test request and checking logs..."
TEST_REQUEST_ID="test-log-$(date +%s)"
curl -s -X GET "http://localhost:8000/health" \
    -H "X-Request-ID: $TEST_REQUEST_ID" > /dev/null

sleep 1

LOG_LINE=$(docker compose -f "$COMPOSE_FILE" logs "$BACKEND_SERVICE" --tail=10 | grep "$TEST_REQUEST_ID" | head -1 || echo "")
if echo "$LOG_LINE" | grep -q '"event":"request.start"'; then
    echo -e "${GREEN}✓ Request lifecycle logs found (request.start)${NC}"
else
    echo -e "${YELLOW}⚠ Request lifecycle logs not found in recent output${NC}"
fi

if echo "$LOG_LINE" | grep -q '"request_id"'; then
    echo -e "${GREEN}✓ Request ID correlation in logs${NC}"
else
    echo -e "${RED}✗ Request ID not found in logs${NC}"
fi

# Check for JSON format
JSON_LOG=$(docker compose -f "$COMPOSE_FILE" logs "$BACKEND_SERVICE" --tail=5 | grep -E '^\{"event"' | head -1 || echo "")
if [ -n "$JSON_LOG" ]; then
    echo -e "${GREEN}✓ JSON structured logs detected${NC}"
else
    echo -e "${YELLOW}⚠ JSON structured logs not detected in recent output${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo ""
echo "Services:"
echo "  - OpenTelemetry Collector: Check docker compose ps"
echo "  - Tempo: http://localhost:3200"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3001 (admin/admin)"
echo ""
echo "Next steps:"
echo "  1. View traces in Tempo UI: http://localhost:3200"
echo "  2. View metrics in Prometheus: http://localhost:9090"
echo "  3. View dashboards in Grafana: http://localhost:3001"
echo "  4. Check logs: docker compose -f $COMPOSE_FILE logs -f $BACKEND_SERVICE"
echo ""
echo -e "${GREEN}Verification complete!${NC}"
