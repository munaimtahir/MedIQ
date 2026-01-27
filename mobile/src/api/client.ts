/**API client with retry, refresh, and error handling.*/

import { ErrorResponse } from "../types/api";

// Get API base URL from environment
const getApiBaseUrl = (): string => {
  // Expo environment variables
  if (typeof process !== 'undefined' && process.env?.EXPO_PUBLIC_API_BASE_URL) {
    return process.env.EXPO_PUBLIC_API_BASE_URL;
  }
  // Fallback
  return "http://localhost:8000";
};

const API_BASE_URL = getApiBaseUrl();
const API_VERSION = "/api/v1";

// Request correlation
function generateRequestId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Network error detection
function isNetworkError(error: unknown): boolean {
  if (error instanceof Error) {
    return (
      error.message.includes("Network") ||
      error.message.includes("fetch") ||
      error.message.includes("timeout")
    );
  }
  return false;
}

// Retry with exponential backoff
async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 2,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: unknown;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      if (attempt < maxRetries && isNetworkError(error)) {
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, delay));
        continue;
      }
      
      throw error;
    }
  }
  
  throw lastError;
}

// Fetch wrapper with error envelope decoding
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${API_VERSION}${endpoint}`;
  const requestId = generateRequestId();
  
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    "X-Request-ID": requestId,
    ...options.headers,
  };
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  // Parse JSON
  let data: T | ErrorResponse;
  try {
    data = await response.json();
  } catch (e) {
    throw new Error(`Invalid JSON response: ${response.status}`);
  }
  
  // Check for error envelope
  if (!response.ok) {
    const error = data as ErrorResponse;
    const apiError = new Error(error.message || "API Error");
    (apiError as any).status = response.status;
    (apiError as any).error_code = error.error_code;
    (apiError as any).error_response = error;
    throw apiError;
  }
  
  return data as T;
}

// API client with token injection and refresh
export class ApiClient {
  private accessToken: string | null = null;
  private refreshInProgress: Promise<string | null> | null = null;
  
  setAccessToken(token: string | null): void {
    this.accessToken = token;
  }
  
  getAccessToken(): string | null {
    return this.accessToken;
  }
  
  // Refresh token callback (set by tokenStore)
  private refreshTokenCallback: (() => Promise<string | null>) | null = null;
  
  setRefreshTokenCallback(callback: () => Promise<string | null>): void {
    this.refreshTokenCallback = callback;
  }
  
  // Request with automatic token injection and refresh
  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retryOn401: boolean = true
  ): Promise<T> {
    return retryWithBackoff(async () => {
      // Add Authorization header if token exists
      const headers: HeadersInit = {
        ...options.headers,
      };
      
      if (this.accessToken) {
        headers["Authorization"] = `Bearer ${this.accessToken}`;
      }
      
      try {
        return await apiFetch<T>(endpoint, {
          ...options,
          headers,
        });
      } catch (error: any) {
        // Handle 401 with refresh
        if (error.status === 401 && retryOn401 && this.refreshTokenCallback) {
          // Check error code - some require re-login
          const errorCode = error.error_code;
          if (
            errorCode === "REFRESH_EXPIRED" ||
            errorCode === "REFRESH_REVOKED" ||
            errorCode === "REFRESH_TOKEN_REUSE"
          ) {
            // Force re-login
            this.setAccessToken(null);
            throw error;
          }
          
          // Try refresh (with lock to prevent concurrent refreshes)
          if (!this.refreshInProgress) {
            this.refreshInProgress = this.refreshTokenCallback();
          }
          
          const newToken = await this.refreshInProgress;
          this.refreshInProgress = null;
          
          if (newToken) {
            this.setAccessToken(newToken);
            // Retry original request once
            return await apiFetch<T>(endpoint, {
              ...options,
              headers: {
                ...headers,
                Authorization: `Bearer ${newToken}`,
              },
            });
          } else {
            // Refresh failed - force logout
            this.setAccessToken(null);
            throw error;
          }
        }
        
        throw error;
      }
    });
  }
  
  // GET request
  async get<T>(endpoint: string, headers?: HeadersInit): Promise<T> {
    return this.request<T>(endpoint, { method: "GET", headers });
  }
  
  // POST request
  async post<T>(endpoint: string, body: unknown, headers?: HeadersInit): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  }
}

// Singleton instance
export const apiClient = new ApiClient();
