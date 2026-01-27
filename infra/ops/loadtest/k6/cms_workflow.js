/**
 * k6 load test: CMS workflow
 * 
 * Simulates admin users creating, updating, submitting, approving, and publishing questions.
 * Tests CMS system behavior under concurrent load.
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
const questionCreateRate = new Rate('question_create_success');
const questionUpdateRate = new Rate('question_update_success');
const questionSubmitRate = new Rate('question_submit_success');
const questionApproveRate = new Rate('question_approve_success');
const questionPublishRate = new Rate('question_publish_success');
const questionCreateDuration = new Trend('question_create_duration');
const questionUpdateDuration = new Trend('question_update_duration');
const questionPublishDuration = new Trend('question_publish_duration');

// Test configuration
export const options = {
    stages: [
        { duration: '30s', target: parseInt(__ENV.VUS || '5') }, // Ramp up
        { duration: __ENV.DURATION || '3m', target: parseInt(__ENV.VUS || '5') }, // Sustained load
        { duration: '30s', target: 0 }, // Ramp down
    ],
    thresholds: {
        'http_req_failed': ['rate<0.01'], // Less than 1% failures
        'http_req_duration': ['p(95)<2000'], // 95% of requests under 2s
        'question_create_duration': ['p(95)<1500'],
        'question_update_duration': ['p(95)<1000'],
        'question_publish_duration': ['p(95)<2000'],
        'question_create_success': ['rate>0.95'],
        'question_update_success': ['rate>0.95'],
        'question_submit_success': ['rate>0.95'],
        'question_approve_success': ['rate>0.95'],
        'question_publish_success': ['rate>0.95'],
    },
};

/**
 * Create a question (DRAFT).
 */
function createQuestion(baseUrl, token) {
    const url = `${baseUrl}/v1/admin/questions`;
    const payload = JSON.stringify({
        stem: `Load test question ${Date.now()}-${Math.random().toString(36).substring(7)}`,
        option_a: 'Option A',
        option_b: 'Option B',
        option_c: 'Option C',
        option_d: 'Option D',
        option_e: 'Option E',
        correct_index: randomIntBetween(0, 4),
        year_id: 1,
        block_id: 1,
        theme_id: 1,
        difficulty: 'MEDIUM',
        cognitive_level: 'UNDERSTAND',
    });
    const headers = getHeaders(token);
    
    const start = Date.now();
    const response = http.post(url, payload, { headers: headers });
    const duration = Date.now() - start;
    questionCreateDuration.add(duration);
    
    const success = check(response, {
        'create question status is 201': (r) => r.status === 201,
        'create question has id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.id !== undefined;
            } catch (e) {
                return false;
            }
        },
    });
    
    questionCreateRate.add(success ? 1 : 0);
    
    if (success) {
        try {
            return JSON.parse(response.body);
        } catch (e) {
            return null;
        }
    }
    return null;
}

/**
 * Update a question.
 */
function updateQuestion(baseUrl, token, questionId) {
    const url = `${baseUrl}/v1/admin/questions/${questionId}`;
    const payload = JSON.stringify({
        stem: `Updated question ${Date.now()}`,
    });
    const headers = getHeaders(token);
    
    const start = Date.now();
    const response = http.put(url, payload, { headers: headers });
    const duration = Date.now() - start;
    questionUpdateDuration.add(duration);
    
    const success = check(response, {
        'update question status is 200': (r) => r.status === 200,
    });
    
    questionUpdateRate.add(success ? 1 : 0);
    return success;
}

/**
 * Submit question for review.
 */
function submitQuestion(baseUrl, token, questionId) {
    const url = `${baseUrl}/v1/admin/questions/${questionId}/submit`;
    const headers = getHeaders(token);
    
    const response = http.post(url, null, { headers: headers });
    
    const success = check(response, {
        'submit question status is 200': (r) => r.status === 200,
    });
    
    questionSubmitRate.add(success ? 1 : 0);
    return success;
}

/**
 * Approve question.
 */
function approveQuestion(baseUrl, token, questionId) {
    const url = `${baseUrl}/v1/admin/questions/${questionId}/approve`;
    const headers = getHeaders(token);
    
    const response = http.post(url, null, { headers: headers });
    
    const success = check(response, {
        'approve question status is 200': (r) => r.status === 200,
    });
    
    questionApproveRate.add(success ? 1 : 0);
    return success;
}

/**
 * Publish question.
 */
function publishQuestion(baseUrl, token, questionId) {
    const url = `${baseUrl}/v1/admin/questions/${questionId}/publish`;
    const payload = JSON.stringify({
        source_book: 'Test Book',
        source_page: 'p. 1',
    });
    const headers = getHeaders(token);
    
    const start = Date.now();
    const response = http.post(url, payload, { headers: headers });
    const duration = Date.now() - start;
    questionPublishDuration.add(duration);
    
    const success = check(response, {
        'publish question status is 200': (r) => r.status === 200,
    });
    
    questionPublishRate.add(success ? 1 : 0);
    return success;
}

/**
 * Main VU function: Simulates admin completing CMS workflow.
 */
export default function () {
    const baseUrl = getBaseUrl();
    const adminEmail = __ENV.ADMIN_USER || 'admin-1@example.com';
    const adminPassword = __ENV.ADMIN_PASS || 'AdminPass123!';
    
    // Login as admin
    const token = login(baseUrl, adminEmail, adminPassword);
    if (!token) {
        console.error('Failed to login as admin, aborting VU');
        return;
    }
    
    // Step 1: Create question (DRAFT)
    const question = createQuestion(baseUrl, token);
    if (!question || !question.id) {
        console.error('Failed to create question, aborting VU');
        return;
    }
    
    sleep(randomIntBetween(1, 3));
    
    // Step 2: Update question
    updateQuestion(baseUrl, token, question.id);
    
    sleep(randomIntBetween(1, 2));
    
    // Step 3: Submit for review
    if (submitQuestion(baseUrl, token, question.id)) {
        sleep(randomIntBetween(1, 2));
        
        // Step 4: Approve (if submit succeeded)
        if (approveQuestion(baseUrl, token, question.id)) {
            sleep(randomIntBetween(1, 2));
            
            // Step 5: Publish (if approve succeeded)
            publishQuestion(baseUrl, token, question.id);
        }
    }
    
    // Brief pause before next iteration
    sleep(randomIntBetween(2, 5));
}

/**
 * Setup function.
 */
export function setup() {
    const baseUrl = getBaseUrl();
    const testRunId = __ENV.X_TEST_RUN_ID || `k6-cms-${Date.now()}`;
    
    console.log(`Starting CMS workflow load test`);
    console.log(`Base URL: ${baseUrl}`);
    console.log(`Test Run ID: ${testRunId}`);
    console.log(`VUs: ${__ENV.VUS || '5'}`);
    console.log(`Duration: ${__ENV.DURATION || '3m'}`);
    
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
