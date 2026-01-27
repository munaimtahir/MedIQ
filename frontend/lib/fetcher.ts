/**
 * Generic fetcher for SWR and API calls
 */

interface FetcherOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

export interface FetcherError {
  status: number;
  code: string;
  message: string;
}

async function fetcher<T = unknown>(url: string, options?: FetcherOptions): Promise<T> {
  const response = await fetch(url, {
    method: options?.method || "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    body: options?.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    
    // Normalize error shape to { status, code, message }
    let code = "HTTP_ERROR";
    let message = "Request failed";
    
    // Try to extract from { error: { code, message } }
    if (errorData?.error?.code && errorData?.error?.message) {
      code = errorData.error.code;
      message = errorData.error.message;
    }
    // Try to extract from { detail }
    else if (errorData?.detail) {
      message = typeof errorData.detail === "string" ? errorData.detail : "Request failed";
      if (response.status === 401) {
        code = "UNAUTHORIZED";
      } else if (response.status === 404) {
        code = "NOT_FOUND";
      } else {
        code = "HTTP_ERROR";
      }
    }
    // Try to extract from { message }
    else if (errorData?.message) {
      message = errorData.message;
      code = response.status === 401 ? "UNAUTHORIZED" : "HTTP_ERROR";
    }
    // Fallback to status-based codes
    else {
      if (response.status === 401) {
        code = "UNAUTHORIZED";
        message = "Unauthorized";
      } else if (response.status === 403) {
        code = "FORBIDDEN";
        message = "Forbidden";
      } else if (response.status === 404) {
        code = "NOT_FOUND";
        message = "Not found";
      } else if (response.status === 429) {
        code = "RATE_LIMITED";
        message = "Rate limited";
      } else if (response.status >= 500) {
        code = "INTERNAL_ERROR";
        message = "Internal server error";
      }
    }
    
    const error: FetcherError = { status: response.status, code, message };
    throw error;
  }

  return response.json();
}

export default fetcher;
export { fetcher };
