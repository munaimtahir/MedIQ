/**
 * k6 load test: Analytics endpoints
 * 
 * Simulates users querying analytics endpoints concurrently.
 * Tests analytics computation performance under load.
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
const analyticsOverviewRate = new Rate('analytics_overview_success');
const analyticsBlockRate = new Rate('analytics_block_success');
const analyticsThemeRate = new Rate('analytics_theme_success');
const analyticsOverviewDuration = new Trend('analytics_overview_duration');
const analyticsBlockDuration = new Trend('analytics_block_duration');
const analyticsThemeDuration = new Trend('analytics_theme_duration');

// Test configuration
export const options = {
    stages: [
        { duration: '30s', target: parseInt(__ENV.VUS || '10') }, // Ramp up
        { duration: __ENV.DURATION || '2m', target: parseInt(__ENV.VUS || '10') }, // Sustained load
        { duration: '30s', target: 0 }, // Ramp down
    ],
    thresholds: {
        'http_req_failed': ['rate<0.01'],
        'http_req_duration': ['p(95)<2000'],
        'analytics_overview_duration': ['p(95)<1500'],
        'analytics_block_duration': ['p(95)<1500'],
        'analytics_theme_duration': ['p(95)<1500'],
        'analytics_overview_success': ['rate>0.95'],
        'analytics_block_success': ['rate>0.95'],
        'analytics_theme_success': ['rate>0.95'],
    },
};

/**
 * Get analytics overview.
 */
function getAnalyticsOverview(baseUrl, token) {
    const url = `${baseUrl}/v1/analytics/overview`;
    const headers = getHeaders(token);
    
    const start = Date.now();
    const response = http.get(url, { headers: headers });
    const duration = Date.now() - start;
    analyticsOverviewDuration.add(duration);
    
    const success = check(response, {
        'analytics overview status is 200': (r) => r.status === 200,
        'analytics overview has data': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body !== null;
            } catch (e) {
                return false;
            }
        },
    });
    
    analyticsOverviewRate.add(success ? 1 : 0);
    return success;
}

/**
 * Get block-specific analytics.
 */
function getBlockAnalytics(baseUrl, token, blockId = 1) {
    const url = `${baseUrl}/v1/analytics/blocks/${blockId}`;
    const headers = getHeaders(token);
    
    const start = Date.now();
    const response = http.get(url, { headers: headers });
    const duration = Date.now() - start;
    analyticsBlockDuration.add(duration);
    
    const success = check(response, {
        'analytics block status is 200': (r) => r.status === 200,
    });
    
    analyticsBlockRate.add(success ? 1 : 0);
    return success;
}

/**
 * Get theme-specific analytics.
 */
function getThemeAnalytics(baseUrl, token, themeId = 1) {
    const url = `${baseUrl}/v1/analytics/themes/${themeId}`;
    const headers = getHeaders(token);
    
    const start = Date.now();
    const response = http.get(url, { headers: headers });
    const duration = Date.now() - start;
    analyticsThemeDuration.add(duration);
    
    const success = check(response, {
        'analytics theme status is 200': (r) => r.status === 200,
    });
    
    analyticsThemeRate.add(success ? 1 : 0);
    return success;
}

/**
 * Main VU function: Simulates user querying analytics.
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
    
    // Query different analytics endpoints
    const endpoints = [
        () => getAnalyticsOverview(baseUrl, token),
        () => getBlockAnalytics(baseUrl, token, 1),
        () => getThemeAnalytics(baseUrl, token, 1),
    ];
    
    // Randomly select endpoint to query
    const endpoint = endpoints[randomIntBetween(0, endpoints.length - 1)];
    endpoint();
    
    // Brief pause before next iteration
    sleep(randomIntBetween(2, 5));
}

/**
 * Setup function.
 */
export function setup() {
    const baseUrl = getBaseUrl();
    const testRunId = __ENV.X_TEST_RUN_ID || `k6-analytics-${Date.now()}`;
    
    console.log(`Starting analytics endpoints load test`);
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
