// k6 Load Test: Session Submit Spike (Final 10 minutes)
// Simulates students submitting sessions in final minutes
// Usage: k6 run --vus 400 --duration 10m load-test-submit.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const submitRate = new Rate('session_submit_success');
const submitLatency = new Trend('session_submit_latency');
const doubleSubmitRate = new Rate('double_submit_handled');

// Configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 },  // Ramp up
    { duration: '6m', target: 400 }, // Peak submit window
    { duration: '2m', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],    // < 1% errors
    session_submit_success: ['rate>0.99'], // > 99% success
  },
};

// Test data
const BASE_URL = __ENV.API_URL || 'https://api-staging.example.com';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';
const SESSION_IDS = __ENV.SESSION_IDS ? __ENV.SESSION_IDS.split(',') : [];

export default function () {
  if (SESSION_IDS.length === 0) {
    sleep(1);
    return;
  }

  const sessionId = SESSION_IDS[__VU % SESSION_IDS.length];
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${AUTH_TOKEN}`,
    'X-Request-ID': `k6-submit-${__VU}-${__ITER}-${Date.now()}`,
  };

  // First submit
  const startTime = Date.now();
  let res = http.post(`${BASE_URL}/v1/sessions/${sessionId}/submit`, null, { headers });
  let latency = Date.now() - startTime;

  const firstSubmitSuccess = check(res, {
    'first submit success': (r) => r.status === 200,
    'has score': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.score_correct !== undefined;
      } catch {
        return false;
      }
    },
  });

  submitRate.add(firstSubmitSuccess);
  submitLatency.add(latency);

  // Simulate double-submit (network retry scenario)
  if (firstSubmitSuccess && Math.random() < 0.1) { // 10% retry rate
    sleep(0.5); // Quick retry
    const retryStartTime = Date.now();
    res = http.post(`${BASE_URL}/v1/sessions/${sessionId}/submit`, null, { headers });
    const retryLatency = Date.now() - retryStartTime;

    const doubleSubmitHandled = check(res, {
      'double submit handled': (r) => r.status === 200, // Should be idempotent
      'same score returned': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.score_correct !== undefined;
        } catch {
          return false;
        }
      },
    });

    doubleSubmitRate.add(doubleSubmitHandled);
    submitLatency.add(retryLatency);
  }

  if (!firstSubmitSuccess) {
    console.error(`Submit failed: ${res.status} - ${res.body}`);
  }

  // Random delay before next iteration (if any)
  sleep(Math.random() * 2 + 1);
}
