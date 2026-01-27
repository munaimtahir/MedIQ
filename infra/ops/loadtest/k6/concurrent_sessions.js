/**
 * k6 load test: Concurrent sessions
 * 
 * Simulates multiple users creating sessions, answering questions, and submitting.
 * Tests system behavior under concurrent load.
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
const answerSubmitDuration = new Trend('answer_submit_duration');
const sessionSubmitDuration = new Trend('session_submit_duration');

// Test configuration from environment
export const options = {
    stages: [
        { duration: '30s', target: parseInt(__ENV.VUS || '10') }, // Ramp up
        { duration: __ENV.DURATION || '2m', target: parseInt(__ENV.VUS || '10') }, // Sustained load
        { duration: '30s', target: 0 }, // Ramp down
    ],
    thresholds: {
        'http_req_failed': ['rate<0.01'], // Less than 1% failures
        'http_req_duration': ['p(95)<2000'], // 95% of requests under 2s
        'session_create_duration': ['p(95)<1500'], // Session creation p95 < 1.5s
        'answer_submit_duration': ['p(95)<1000'], // Answer submission p95 < 1s
        'session_submit_duration': ['p(95)<1500'], // Session submit p95 < 1.5s
        'session_create_success': ['rate>0.95'], // 95% success rate
        'answer_submit_success': ['rate>0.95'],
        'session_submit_success': ['rate>0.95'],
    },
};

/**
 * Main VU function: Simulates a user completing a session.
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
    
    if (!sessionData) {
        console.error('Failed to create session, aborting VU');
        return;
    }
    
    sessionCreateRate.add(1);
    const sessionId = sessionData.session_id;
    const totalQuestions = sessionData.total_questions || 10;
    
    // Get session state to see questions
    const state = getSessionState(baseUrl, token, sessionId);
    if (!state || !state.questions || state.questions.length === 0) {
        console.error('Failed to get session state or no questions, aborting VU');
        return;
    }
    
    // Answer questions (answer 70-100% of them)
    const questionsToAnswer = Math.floor(totalQuestions * (0.7 + Math.random() * 0.3));
    const questions = state.questions.slice(0, Math.min(questionsToAnswer, state.questions.length));
    
    for (const question of questions) {
        // Think time (simulate reading question)
        thinkTime(2, 6);
        
        // Submit answer
        const answerStart = Date.now();
        const answerResult = submitAnswer(
            baseUrl,
            token,
            sessionId,
            question.question_id,
            randomOptionIndex(),
            Math.random() < 0.1 // 10% chance of marking for review
        );
        const answerSubmitTime = Date.now() - answerStart;
        answerSubmitDuration.add(answerSubmitTime);
        
        if (answerResult) {
            answerSubmitRate.add(1);
        } else {
            answerSubmitRate.add(0);
            console.error(`Failed to submit answer for question ${question.question_id}`);
        }
    }
    
    // Submit session
    const submitStart = Date.now();
    const submitResult = submitSession(baseUrl, token, sessionId);
    const sessionSubmitTime = Date.now() - submitStart;
    sessionSubmitDuration.add(sessionSubmitTime);
    
    if (submitResult) {
        sessionSubmitRate.add(1);
    } else {
        sessionSubmitRate.add(0);
        console.error(`Failed to submit session ${sessionId}`);
    }
    
    // Brief pause before next iteration
    sleep(randomIntBetween(1, 3));
}

/**
 * Setup function: Runs once before all VUs.
 */
export function setup() {
    const baseUrl = getBaseUrl();
    const testRunId = __ENV.X_TEST_RUN_ID || `k6-${Date.now()}`;
    
    console.log(`Starting concurrent sessions load test`);
    console.log(`Base URL: ${baseUrl}`);
    console.log(`Test Run ID: ${testRunId}`);
    console.log(`VUs: ${__ENV.VUS || '10'}`);
    console.log(`Duration: ${__ENV.DURATION || '2m'}`);
    
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
