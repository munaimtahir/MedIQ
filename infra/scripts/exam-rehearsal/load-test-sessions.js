// k6 Load Test: Session Creation Burst
// Simulates 300-500 concurrent students starting sessions within 5 minutes
// Usage: k6 run --vus 400 --duration 5m load-test-sessions.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const sessionCreateRate = new Rate('session_create_success');
const sessionCreateLatency = new Trend('session_create_latency');

// Configuration
export const options = {
  stages: [
    { duration: '1m', target: 100 },  // Ramp up to 100 users
    { duration: '2m', target: 400 },  // Ramp to 400 users (peak)
    { duration: '2m', target: 400 },  // Hold at 400 users
    { duration: '1m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],    // < 1% errors
    session_create_success: ['rate>0.99'], // > 99% success
  },
};

// Test data
const BASE_URL = __ENV.API_URL || 'https://api-staging.example.com';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';

// Test session creation filters
const sessionFilters = [
  { year: 1, blocks: ['A'], count: 20, duration_seconds: 1800 },
  { year: 2, blocks: ['B'], count: 25, duration_seconds: 1800 },
  { year: 3, blocks: ['C'], count: 30, duration_seconds: null },
];

export default function () {
  // Select random filter
  const filter = sessionFilters[Math.floor(Math.random() * sessionFilters.length)];
  
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${AUTH_TOKEN}`,
    'X-Request-ID': `k6-${__VU}-${__ITER}-${Date.now()}`,
  };

  const payload = JSON.stringify({
    year: filter.year,
    blocks: filter.blocks,
    count: filter.count,
    duration_seconds: filter.duration_seconds,
    mode: filter.duration_seconds ? 'EXAM' : 'TUTOR',
  });

  const startTime = Date.now();
  const res = http.post(`${BASE_URL}/v1/sessions`, payload, { headers });
  const latency = Date.now() - startTime;

  const success = check(res, {
    'session created': (r) => r.status === 200 || r.status === 201,
    'has session_id': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.session_id !== undefined;
      } catch {
        return false;
      }
    },
    'latency < 500ms': () => latency < 500,
  });

  sessionCreateRate.add(success);
  sessionCreateLatency.add(latency);

  if (!success) {
    console.error(`Session create failed: ${res.status} - ${res.body}`);
  }

  // Random delay between 0.5-2 seconds (simulate user behavior)
  sleep(Math.random() * 1.5 + 0.5);
}
