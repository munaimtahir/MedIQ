/**
 * Common utilities for k6 load testing scripts.
 */

import { check, sleep } from 'k6';
import http from 'k6/http';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

/**
 * Generate a unique test run ID for correlation in logs/metrics.
 */
export function generateTestRunId() {
    return `k6-${Date.now()}-${Math.random().toString(36).substring(7)}`;
}

/**
 * Get base URL from environment variable.
 */
export function getBaseUrl() {
    return __ENV.BASE_URL || 'http://localhost:8000';
}

/**
 * Get test run ID from environment or generate new one.
 */
export function getTestRunId() {
    return __ENV.X_TEST_RUN_ID || generateTestRunId();
}

/**
 * Create common headers including test run ID.
 */
export function getHeaders(token = null) {
    const headers = {
        'Content-Type': 'application/json',
        'X-Test-Run-ID': getTestRunId(),
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

/**
 * Login and return access token.
 */
export function login(baseUrl, email, password) {
    const url = `${baseUrl}/v1/auth/login`;
    const payload = JSON.stringify({
        email: email,
        password: password,
    });
    const headers = getHeaders();
    
    const response = http.post(url, payload, { headers: headers });
    
    const checkResult = check(response, {
        'login status is 200': (r) => r.status === 200,
        'login has tokens': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.tokens && body.tokens.access_token;
            } catch (e) {
                return false;
            }
        },
    });
    
    if (!checkResult) {
        console.error(`Login failed: ${response.status} - ${response.body}`);
        return null;
    }
    
    try {
        const body = JSON.parse(response.body);
        return body.tokens.access_token;
    } catch (e) {
        console.error(`Failed to parse login response: ${e}`);
        return null;
    }
}

/**
 * Create a test session.
 */
export function createSession(baseUrl, token, options = {}) {
    const url = `${baseUrl}/v1/sessions`;
    const payload = JSON.stringify({
        mode: options.mode || 'TUTOR',
        year: options.year || 1,
        blocks: options.blocks || ['A'],
        themes: options.themes || null,
        count: options.count || 10,
        duration_seconds: options.duration_seconds || 3600,
        difficulty: options.difficulty || null,
        cognitive: options.cognitive || null,
    });
    const headers = getHeaders(token);
    
    const response = http.post(url, payload, { headers: headers });
    
    const checkResult = check(response, {
        'create session status is 200': (r) => r.status === 200,
        'create session has session_id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.session_id !== undefined;
            } catch (e) {
                return false;
            }
        },
    });
    
    if (!checkResult) {
        console.error(`Create session failed: ${response.status} - ${response.body}`);
        return null;
    }
    
    try {
        const body = JSON.parse(response.body);
        return {
            session_id: body.session_id,
            total_questions: body.total_questions || 0,
        };
    } catch (e) {
        console.error(`Failed to parse create session response: ${e}`);
        return null;
    }
}

/**
 * Get session state.
 */
export function getSessionState(baseUrl, token, sessionId) {
    const url = `${baseUrl}/v1/sessions/${sessionId}`;
    const headers = getHeaders(token);
    
    const response = http.get(url, { headers: headers });
    
    const checkResult = check(response, {
        'get session status is 200': (r) => r.status === 200,
        'get session has questions': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.questions && Array.isArray(body.questions);
            } catch (e) {
                return false;
            }
        },
    });
    
    if (!checkResult) {
        console.error(`Get session failed: ${response.status} - ${response.body}`);
        return null;
    }
    
    try {
        return JSON.parse(response.body);
    } catch (e) {
        console.error(`Failed to parse get session response: ${e}`);
        return null;
    }
}

/**
 * Submit an answer for a question.
 */
export function submitAnswer(baseUrl, token, sessionId, questionId, selectedIndex = null, markedForReview = false) {
    const url = `${baseUrl}/v1/sessions/${sessionId}/answer`;
    const payload = JSON.stringify({
        question_id: questionId,
        selected_index: selectedIndex,
        marked_for_review: markedForReview,
    });
    const headers = getHeaders(token);
    
    const response = http.post(url, payload, { headers: headers });
    
    const checkResult = check(response, {
        'submit answer status is 200': (r) => r.status === 200,
        'submit answer has answer': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.answer !== undefined;
            } catch (e) {
                return false;
            }
        },
    });
    
    if (!checkResult) {
        console.error(`Submit answer failed: ${response.status} - ${response.body}`);
        return null;
    }
    
    try {
        return JSON.parse(response.body);
    } catch (e) {
        console.error(`Failed to parse submit answer response: ${e}`);
        return null;
    }
}

/**
 * Submit a session (finalize).
 */
export function submitSession(baseUrl, token, sessionId) {
    const url = `${baseUrl}/v1/sessions/${sessionId}/submit`;
    const headers = getHeaders(token);
    
    const response = http.post(url, null, { headers: headers });
    
    const checkResult = check(response, {
        'submit session status is 200': (r) => r.status === 200,
        'submit session has score': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.session && body.session.score_correct !== undefined;
            } catch (e) {
                return false;
            }
        },
    });
    
    if (!checkResult) {
        console.error(`Submit session failed: ${response.status} - ${response.body}`);
        return null;
    }
    
    try {
        return JSON.parse(response.body);
    } catch (e) {
        console.error(`Failed to parse submit session response: ${e}`);
        return null;
    }
}

/**
 * Realistic think time (simulate user reading question).
 */
export function thinkTime(minSeconds = 2, maxSeconds = 8) {
    sleep(randomIntBetween(minSeconds, maxSeconds));
}

/**
 * Random option index (0-4 for MCQ).
 */
export function randomOptionIndex() {
    return randomIntBetween(0, 4);
}
