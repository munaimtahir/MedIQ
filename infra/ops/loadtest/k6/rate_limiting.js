/**
 * k6 load test: API rate limiting behavior
 * 
 * Tests rate limiting by making rapid requests to endpoints
 * that should be rate-limited (login, session creation, etc.).
 */

import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import http from 'k6/http';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import {
    getBaseUrl,
    getHeaders,
    login,
} from './common.js';

// Custom metrics
const loginRate = new Rate('login_success');
const rateLimitedRate = new Rate('rate_limited');
const loginDuration = new Trend('login_duration');

// Test configuration - rapid requests to trigger rate limiting
export const options = {
    stages: [
        { duration: '10s', target: 5 },    // Start small
        { duration: '30s', target: 20 },   // Rapid increase
        { duration: '1m', target: 50 },    // High load
        { duration: '30s', target: 0 },    // Ramp down
    ],
    thresholds: {
        // Track rate limiting behavior
        'rate_limited': ['rate>0.05'], // Expect at least 5% rate limiting under high load
        'login_success': ['rate>0.50'], // At least 50% should succeed (others rate limited)
    },
};

/**
 * Attempt login (may be rate limited).
 */
function attemptLogin(baseUrl, email, password) {
    const url = `${baseUrl}/v1/auth/login`;
    const payload = JSON.stringify({
        email: email,
        password: password,
    });
    const headers = getHeaders();
    
    const start = Date.now();
    const response = http.post(url, payload, { headers: headers });
    const duration = Date.now() - start;
    loginDuration.add(duration);
    
    // Check if rate limited
    const isRateLimited = response.status === 429;
    rateLimitedRate.add(isRateLimited ? 1 : 0);
    
    // Check if login succeeded
    const success = response.status === 200;
    loginRate.add(success ? 1 : 0);
    
    if (success) {
        try {
            const body = JSON.parse(response.body);
            return body.tokens ? body.tokens.access_token : null;
        } catch (e) {
            return null;
        }
    }
    
    return null;
}

/**
 * Main VU function: Rapidly attempts logins to test rate limiting.
 */
export default function () {
    const baseUrl = getBaseUrl();
    const studentEmail = __ENV.STUDENT_USER || 'student-1@example.com';
    const studentPassword = __ENV.STUDENT_PASS || 'StudentPass123!';
    
    // Make multiple rapid login attempts
    const attempts = randomIntBetween(5, 10);
    for (let i = 0; i < attempts; i++) {
        attemptLogin(baseUrl, studentEmail, studentPassword);
        
        // Very short pause (rapid requests)
        sleep(0.1 + Math.random() * 0.2);
    }
    
    // Brief pause before next iteration
    sleep(randomIntBetween(1, 3));
}

/**
 * Setup function.
 */
export function setup() {
    const baseUrl = getBaseUrl();
    const testRunId = __ENV.X_TEST_RUN_ID || `k6-ratelimit-${Date.now()}`;
    
    console.log(`Starting rate limiting behavior test`);
    console.log(`Base URL: ${baseUrl}`);
    console.log(`Test Run ID: ${testRunId}`);
    console.log(`Max VUs: 50`);
    console.log(`This test makes rapid requests to trigger rate limiting`);
    
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
