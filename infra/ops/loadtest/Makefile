.PHONY: help concurrent spike cms analytics stress endurance capacity ratelimit clean

help:
	@echo "k6 Load Testing Commands"
	@echo ""
	@echo "Basic Tests:"
	@echo "  make concurrent    - Run concurrent sessions test"
	@echo "  make spike         - Run submit spike test"
	@echo ""
	@echo "Advanced Tests:"
	@echo "  make cms           - Run CMS workflow load test"
	@echo "  make analytics     - Run analytics endpoints load test"
	@echo "  make stress        - Run stress test (find breaking points)"
	@echo "  make endurance     - Run endurance test (long-duration stability)"
	@echo "  make capacity      - Run capacity planning test"
	@echo "  make ratelimit     - Run rate limiting behavior test"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean         - Clean k6 results directory"
	@echo ""
	@echo "Environment variables:"
	@echo "  BASE_URL           - Backend URL (default: http://localhost:8000)"
	@echo "  STUDENT_USER       - Student email"
	@echo "  STUDENT_PASS       - Student password"
	@echo "  ADMIN_USER         - Admin email (for CMS tests)"
	@echo "  ADMIN_PASS         - Admin password (for CMS tests)"
	@echo "  VUS                - Virtual users (default: 10)"
	@echo "  DURATION           - Test duration (default: 2m)"
	@echo "  BASE_VUS           - Baseline VUs for spike (default: 5)"
	@echo "  SPIKE_VUS          - Spike VUs (default: 50)"
	@echo "  X_TEST_RUN_ID      - Test run ID for correlation"

concurrent:
	@echo "Running concurrent sessions load test..."
	@docker compose -f docker-compose.k6.yml run --rm \
		-e K6_SCRIPT=concurrent_sessions.js \
		k6

spike:
	@echo "Running submit spike load test..."
	@docker compose -f docker-compose.k6.yml run --rm \
		-e K6_SCRIPT=submit_spike.js \
		k6

cms:
	@echo "Running CMS workflow load test..."
	@docker compose -f docker-compose.k6.yml run --rm \
		-e K6_SCRIPT=cms_workflow.js \
		k6

analytics:
	@echo "Running analytics endpoints load test..."
	@docker compose -f docker-compose.k6.yml run --rm \
		-e K6_SCRIPT=analytics_endpoints.js \
		k6

stress:
	@echo "Running stress test (finding breaking points)..."
	@docker compose -f docker-compose.k6.yml run --rm \
		-e K6_SCRIPT=stress_test.js \
		k6

endurance:
	@echo "Running endurance test (long-duration stability)..."
	@docker compose -f docker-compose.k6.yml run --rm \
		-e K6_SCRIPT=endurance_test.js \
		-e DURATION=30m \
		k6

capacity:
	@echo "Running capacity planning test..."
	@docker compose -f docker-compose.k6.yml run --rm \
		-e K6_SCRIPT=capacity_planning.js \
		k6

ratelimit:
	@echo "Running rate limiting behavior test..."
	@docker compose -f docker-compose.k6.yml run --rm \
		-e K6_SCRIPT=rate_limiting.js \
		k6

clean:
	@echo "Cleaning k6 results..."
	@rm -rf k6-results/*.json
	@echo "Done."
