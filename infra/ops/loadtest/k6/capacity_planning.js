/**
 * k6 load test: Capacity planning
 * 
 * Tests system capacity by gradually increasing load to determine
 * maximum concurrent users the system can handle.
 */

import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import http from 'k6/http';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import {
    getBaseUrl,
    getHeaders,
    login,
    createSession,
    getSessionState,
    submitAnswer,
    submitSession,
    thinkTime,
    randomOptionIndex,
} from './common.js';

// Custom metrics
const sessionCreateRate = new Rate('session_create_success');
const answerSubmitRate = new Rate('answer_submit_success');
const sessionSubmitRate = new Rate('session_submit_success');
const sessionCreateDuration = new Trend('session_create_duration');
const p95Latency = new Trend('p95_latency');

// Test configuration - gradual capacity increase
export const options = {
    stages: [
        { duration: '2m', target: 10 },    // Baseline: 10 users
        { duration: '3m', target: 25 },    // Step 1: 25 users
        { duration: '3m', target: 50 },    // Step 2: 50 users
        { duration: '3m', target: 75 },    // Step 3: 75 users
        { duration: '3m', target: 100 },   // Step 4: 100 users
        { duration: '3m', target: 150 },   // Step 5: 150 users
        { duration: '3m', target: 200 },   // Step 6: 200 users
        { duration: '3m', target: 250 },   // Step 7: 250 users (capacity limit)
        { duration: '2m', target: 0 },     // Ramp down
    ],
    thresholds: {
        // Track when system degrades
        'http_req_failed': ['rate<0.05'], // Allow up to 5% failures at capacity
        'http_req_duration': ['p(95)<3000'], // p95 should stay under 3s
        'session_create_duration': ['p(95)<2000'], // Session creation p95 < 2s
        'session_create_success': ['rate>0.90'], // 90% success rate at capacity
        'answer_submit_success': ['rate>0.90'],
        'session_submit_success': ['rate>0.90'],
    },
};

/**
 * Main VU function: Simulates user completing a session.
 */
export default function () {
    const baseUrl = getBaseUrl();
    const studentEmail = __ENV.STUDENT_USER || 'student-1@example.com';
    const studentPassword = __ENV.STUDENT_PASS || 'StudentPass123!';
    
    // Login
    const token = login(baseUrl, studentEmail, studentPassword);
    if (!token) {
        console.error('Failed to login, aborting VU');
        return;
    }
    
    // Create session
    const sessionStart = Date.now();
    const sessionData = createSession(baseUrl, token, {
        mode: 'TUTOR',
        year: 1,
        blocks: ['A'],
        count: 10,
    });
    const sessionCreateTime = Date.now() - sessionStart;
    sessionCreateDuration.add(sessionCreateTime);
    p95Latency.add(sessionCreateTime);
    
    if (!sessionData) {
        sessionCreateRate.add(0);
        console.error('Failed to create session, aborting VU');
        return;
    }
    
    sessionCreateRate.add(1);
    const sessionId = sessionData.session_id;
    
    // Get session state
    const state = getSessionState(baseUrl, token, sessionId);
    if (!state || !state.questions || state.questions.length === 0) {
        console.error('Failed to get session state, aborting VU');
        return;
    }
    
    // Answer questions
    const questionsToAnswer = Math.floor(state.questions.length * 0.8);
    const questions = state.questions.slice(0, Math.min(questionsToAnswer, state.questions.length));
    
    for (const question of questions) {
        thinkTime(2, 5);
        
        const answerResult = submitAnswer(
            baseUrl,
            token,
            sessionId,
            question.question_id,
            randomOptionIndex(),
            Math.random() < 0.1
        );
        
        if (answerResult) {
            answerSubmitRate.add(1);
        } else {
            answerSubmitRate.add(0);
        }
    }
    
    // Submit session
    const submitResult = submitSession(baseUrl, token, sessionId);
    if (submitResult) {
        sessionSubmitRate.add(1);
    } else {
        sessionSubmitRate.add(0);
    }
    
    // Pause before next iteration
    sleep(randomIntBetween(3, 8));
}

/**
 * Setup function.
 */
export function setup() {
    const baseUrl = getBaseUrl();
    const testRunId = __ENV.X_TEST_RUN_ID || `k6-capacity-${Date.now()}`;
    
    console.log(`Starting capacity planning test`);
    console.log(`Base URL: ${baseUrl}`);
    console.log(`Test Run ID: ${testRunId}`);
    console.log(`Max VUs: 250`);
    console.log(`This test will gradually increase load to find capacity limits`);
    
    // Verify backend is accessible
    const healthCheck = http.get(`${baseUrl}/v1/health`);
    check(healthCheck, {
        'health check passed': (r) => r.status === 200,
    });
    
    if (healthCheck.status !== 200) {
        console.error(`Backend health check failed: ${healthCheck.status}`);
        throw new Error('Backend not accessible');
    }
    
    return {
        baseUrl: baseUrl,
        testRunId: testRunId,
    };
}
