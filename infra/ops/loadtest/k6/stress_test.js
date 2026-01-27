/**
 * k6 load test: Stress test (find breaking points)
 * 
 * Gradually increases load until system breaks or reaches maximum capacity.
 * Tests system limits and failure modes.
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
const errorRate = new Rate('errors');

// Test configuration - gradually increase load
export const options = {
    stages: [
        { duration: '1m', target: 10 },   // Start with 10 VUs
        { duration: '2m', target: 20 },   // Increase to 20
        { duration: '2m', target: 50 },   // Increase to 50
        { duration: '2m', target: 100 },  // Increase to 100
        { duration: '2m', target: 150 },  // Increase to 150
        { duration: '2m', target: 200 },  // Increase to 200 (stress point)
        { duration: '1m', target: 0 },    // Ramp down
    ],
    thresholds: {
        // More lenient thresholds for stress test
        'http_req_failed': ['rate<0.10'], // Allow up to 10% failures under stress
        'http_req_duration': ['p(95)<5000'], // Allow up to 5s under stress
        'session_create_success': ['rate>0.80'], // 80% success rate acceptable under stress
        'answer_submit_success': ['rate>0.80'],
        'session_submit_success': ['rate>0.80'],
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
        errorRate.add(1);
        console.error('Failed to login, aborting VU');
        return;
    }
    
    // Create session
    const sessionData = createSession(baseUrl, token, {
        mode: 'TUTOR',
        year: 1,
        blocks: ['A'],
        count: 5, // Smaller sessions for stress test
    });
    
    if (!sessionData) {
        errorRate.add(1);
        sessionCreateRate.add(0);
        console.error('Failed to create session, aborting VU');
        return;
    }
    
    sessionCreateRate.add(1);
    const sessionId = sessionData.session_id;
    
    // Get session state
    const state = getSessionState(baseUrl, token, sessionId);
    if (!state || !state.questions || state.questions.length === 0) {
        errorRate.add(1);
        console.error('Failed to get session state, aborting VU');
        return;
    }
    
    // Answer questions quickly (stress test = minimal think time)
    const questions = state.questions.slice(0, Math.min(3, state.questions.length));
    for (const question of questions) {
        sleep(0.5); // Minimal think time
        
        const answerResult = submitAnswer(
            baseUrl,
            token,
            sessionId,
            question.question_id,
            randomOptionIndex(),
            false
        );
        
        if (answerResult) {
            answerSubmitRate.add(1);
        } else {
            answerSubmitRate.add(0);
            errorRate.add(1);
        }
    }
    
    // Submit session
    const submitResult = submitSession(baseUrl, token, sessionId);
    if (submitResult) {
        sessionSubmitRate.add(1);
    } else {
        sessionSubmitRate.add(0);
        errorRate.add(1);
    }
    
    // Brief pause
    sleep(randomIntBetween(1, 3));
}

/**
 * Setup function.
 */
export function setup() {
    const baseUrl = getBaseUrl();
    const testRunId = __ENV.X_TEST_RUN_ID || `k6-stress-${Date.now()}`;
    
    console.log(`Starting stress test (finding breaking points)`);
    console.log(`Base URL: ${baseUrl}`);
    console.log(`Test Run ID: ${testRunId}`);
    console.log(`Max VUs: 200`);
    
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
