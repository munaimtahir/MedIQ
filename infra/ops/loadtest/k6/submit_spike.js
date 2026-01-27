/**
 * k6 load test: Submit spike
 * 
 * Simulates a sudden spike in session submissions (e.g., exam deadline).
 * Tests system resilience under sudden load increase.
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
const sessionSubmitDuration = new Trend('session_submit_duration');
const sessionSubmitRate = new Rate('session_submit_success');
const spikeSubmitDuration = new Trend('spike_submit_duration');

// Test configuration from environment
export const options = {
    stages: [
        { duration: '1m', target: parseInt(__ENV.BASE_VUS || '5') }, // Baseline load
        { duration: '30s', target: parseInt(__ENV.SPIKE_VUS || '50') }, // Spike ramp up
        { duration: '1m', target: parseInt(__ENV.SPIKE_VUS || '50') }, // Sustained spike
        { duration: '30s', target: parseInt(__ENV.BASE_VUS || '5') }, // Spike ramp down
        { duration: '1m', target: parseInt(__ENV.BASE_VUS || '5') }, // Return to baseline
    ],
    thresholds: {
        'http_req_failed': ['rate<0.02'], // Less than 2% failures (spike tolerance)
        'http_req_duration': ['p(95)<3000'], // 95% of requests under 3s (spike tolerance)
        'session_submit_duration': ['p(95)<2000'], // Session submit p95 < 2s
        'spike_submit_duration': ['p(95)<2500'], // Spike submit p95 < 2.5s
        'session_submit_success': ['rate>0.90'], // 90% success rate (spike tolerance)
    },
};

/**
 * Main VU function: Creates session and submits immediately (spike scenario).
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
    const sessionData = createSession(baseUrl, token, {
        mode: 'TUTOR',
        year: 1,
        blocks: ['A'],
        count: 5, // Smaller session for spike test
    });
    
    if (!sessionData) {
        console.error('Failed to create session, aborting VU');
        return;
    }
    
    const sessionId = sessionData.session_id;
    
    // Get session state
    const state = getSessionState(baseUrl, token, sessionId);
    if (!state || !state.questions || state.questions.length === 0) {
        console.error('Failed to get session state or no questions, aborting VU');
        return;
    }
    
    // In spike scenario, users may have already answered some questions
    // Answer remaining questions quickly (minimal think time)
    const questions = state.questions;
    for (const question of questions) {
        // Minimal think time (spike = rushed submissions)
        sleep(0.5 + Math.random() * 1.0);
        
        // Submit answer
        submitAnswer(
            baseUrl,
            token,
            sessionId,
            question.question_id,
            randomOptionIndex(),
            false
        );
    }
    
    // Submit session (this is the spike - many concurrent submits)
    const submitStart = Date.now();
    const submitResult = submitSession(baseUrl, token, sessionId);
    const sessionSubmitTime = Date.now() - submitStart;
    sessionSubmitDuration.add(sessionSubmitTime);
    spikeSubmitDuration.add(sessionSubmitTime);
    
    if (submitResult) {
        sessionSubmitRate.add(1);
    } else {
        sessionSubmitRate.add(0);
        console.error(`Failed to submit session ${sessionId}`);
    }
    
    // No pause - spike scenario means immediate next iteration
    sleep(randomIntBetween(0.5, 2));
}

/**
 * Setup function: Runs once before all VUs.
 */
export function setup() {
    const baseUrl = getBaseUrl();
    const testRunId = __ENV.X_TEST_RUN_ID || `k6-spike-${Date.now()}`;
    
    console.log(`Starting submit spike load test`);
    console.log(`Base URL: ${baseUrl}`);
    console.log(`Test Run ID: ${testRunId}`);
    console.log(`Base VUs: ${__ENV.BASE_VUS || '5'}`);
    console.log(`Spike VUs: ${__ENV.SPIKE_VUS || '50'}`);
    
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
