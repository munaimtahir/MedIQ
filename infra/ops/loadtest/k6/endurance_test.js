/**
 * k6 load test: Endurance test (long-duration stability)
 * 
 * Runs sustained load for extended period to test system stability,
 * memory leaks, connection pool exhaustion, etc.
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
const memoryLeakIndicator = new Trend('response_time_trend'); // Track if response times degrade over time

// Test configuration - sustained load for long duration
export const options = {
    stages: [
        { duration: '2m', target: parseInt(__ENV.VUS || '20') }, // Ramp up
        { duration: __ENV.DURATION || '30m', target: parseInt(__ENV.VUS || '20') }, // Sustained load (default 30 min)
        { duration: '2m', target: 0 }, // Ramp down
    ],
    thresholds: {
        'http_req_failed': ['rate<0.01'], // Less than 1% failures
        'http_req_duration': ['p(95)<2000'], // 95% under 2s (should remain stable)
        'session_create_success': ['rate>0.95'],
        'answer_submit_success': ['rate>0.95'],
        'session_submit_success': ['rate>0.95'],
    },
};

/**
 * Main VU function: Simulates user completing sessions repeatedly.
 */
export default function () {
    const baseUrl = getBaseUrl();
    const studentEmail = __ENV.STUDENT_USER || 'student-1@example.com';
    const studentPassword = __ENV.STUDENT_PASS || 'StudentPass123!';
    
    // Login (may need to refresh token periodically in real scenario)
    const token = login(baseUrl, studentEmail, studentPassword);
    if (!token) {
        console.error('Failed to login, aborting VU');
        return;
    }
    
    // Complete multiple sessions (endurance = repeated operations)
    const iterations = randomIntBetween(3, 5);
    for (let i = 0; i < iterations; i++) {
        // Create session
        const sessionData = createSession(baseUrl, token, {
            mode: 'TUTOR',
            year: 1,
            blocks: ['A'],
            count: 5,
        });
        
        if (!sessionData) {
            sessionCreateRate.add(0);
            continue;
        }
        
        sessionCreateRate.add(1);
        const sessionId = sessionData.session_id;
        
        // Get session state
        const state = getSessionState(baseUrl, token, sessionId);
        if (!state || !state.questions || state.questions.length === 0) {
            continue;
        }
        
        // Answer questions
        const questions = state.questions.slice(0, Math.min(3, state.questions.length));
        for (const question of questions) {
            thinkTime(1, 3);
            
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
            // Track response time trend (for memory leak detection)
            memoryLeakIndicator.add(submitResult.response_time || 0);
        } else {
            sessionSubmitRate.add(0);
        }
        
        // Pause between sessions
        sleep(randomIntBetween(5, 10));
    }
    
    // Longer pause before next VU iteration
    sleep(randomIntBetween(10, 20));
}

/**
 * Setup function.
 */
export function setup() {
    const baseUrl = getBaseUrl();
    const testRunId = __ENV.X_TEST_RUN_ID || `k6-endurance-${Date.now()}`;
    
    console.log(`Starting endurance test (long-duration stability)`);
    console.log(`Base URL: ${baseUrl}`);
    console.log(`Test Run ID: ${testRunId}`);
    console.log(`VUs: ${__ENV.VUS || '20'}`);
    console.log(`Duration: ${__ENV.DURATION || '30m'}`);
    
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
