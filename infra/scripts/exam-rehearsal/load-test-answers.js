// k6 Load Test: Answer Submissions (Steady State)
// Simulates students answering questions during exam
// Usage: k6 run --vus 300 --duration 30m load-test-answers.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const answerSubmitRate = new Rate('answer_submit_success');
const answerSubmitLatency = new Trend('answer_submit_latency');
const answerCount = new Counter('answers_submitted');

// Configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 },  // Ramp up
    { duration: '25m', target: 300 }, // Steady state
    { duration: '3m', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'],  // 95% of requests < 200ms
    http_req_failed: ['rate<0.01'],    // < 1% errors
    answer_submit_success: ['rate>0.99'], // > 99% success
  },
};

// Test data
const BASE_URL = __ENV.API_URL || 'https://api-staging.example.com';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';
const SESSION_IDS = __ENV.SESSION_IDS ? __ENV.SESSION_IDS.split(',') : [];

// Per-VU state
let sessionId = null;
let questionIds = [];
let currentQuestionIndex = 0;

export function setup() {
  // Get or create a session for this VU
  if (SESSION_IDS.length > 0) {
    sessionId = SESSION_IDS[__VU % SESSION_IDS.length];
  } else {
    // Create a new session
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${AUTH_TOKEN}`,
    };
    const payload = JSON.stringify({
      year: 1,
      blocks: ['A'],
      count: 20,
      mode: 'TUTOR',
    });
    const res = http.post(`${BASE_URL}/v1/sessions`, payload, { headers });
    if (res.status === 200 || res.status === 201) {
      const body = JSON.parse(res.body);
      sessionId = body.session_id;
      // Get session state to extract question IDs
      const stateRes = http.get(`${BASE_URL}/v1/sessions/${sessionId}`, { headers });
      if (stateRes.status === 200) {
        const state = JSON.parse(stateRes.body);
        questionIds = state.questions?.map(q => q.question_id) || [];
      }
    }
  }
  return { sessionId, questionIds };
}

export default function (data) {
  if (!data.sessionId || data.questionIds.length === 0) {
    sleep(1);
    return;
  }

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${AUTH_TOKEN}`,
    'X-Request-ID': `k6-answer-${__VU}-${__ITER}-${Date.now()}`,
  };

  // Select random question and answer
  const questionId = data.questionIds[Math.floor(Math.random() * data.questionIds.length)];
  const selectedIndex = Math.floor(Math.random() * 5); // 0-4

  const payload = JSON.stringify({
    question_id: questionId,
    selected_index: selectedIndex,
    marked_for_review: Math.random() < 0.1, // 10% marked for review
  });

  const startTime = Date.now();
  const res = http.post(
    `${BASE_URL}/v1/sessions/${data.sessionId}/answer`,
    payload,
    { headers }
  );
  const latency = Date.now() - startTime;

  const success = check(res, {
    'answer submitted': (r) => r.status === 200,
    'has answer data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.answer !== undefined;
      } catch {
        return false;
      }
    },
    'latency < 200ms': () => latency < 200,
  });

  answerSubmitRate.add(success);
  answerSubmitLatency.add(latency);
  answerCount.add(1);

  if (!success) {
    console.error(`Answer submit failed: ${res.status} - ${res.body}`);
  }

  // Simulate user thinking time: 5-30 seconds per question
  sleep(Math.random() * 25 + 5);
}
