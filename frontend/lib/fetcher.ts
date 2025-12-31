/**
 * Global fetch wrapper with automatic token refresh on 401.
 */

import { authClient } from "./authClient";

export interface FetcherError {
  code: string;
  message: string;
  status?: number;
  request_id?: string;
}

async function fetcher<T>(
  url: string,
  options: RequestInit = {},
  retryOn401 = true,
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  // Handle 401 with automatic refresh
  if (response.status === 401 && retryOn401) {
    // Try to refresh token
    const refreshResult = await authClient.refresh();

    if (refreshResult.error) {
      // Refresh failed - redirect to login
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw {
        code: "UNAUTHORIZED",
        message: "Session expired. Please login again.",
        status: 401,
      } as FetcherError;
    }

    // Retry original request once
    return fetcher<T>(url, options, false);
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error: FetcherError = {
      code: data.error?.code || "HTTP_ERROR",
      message: data.error?.message || response.statusText,
      status: response.status,
      request_id: data.error?.request_id || response.headers.get("X-Request-ID") || undefined,
    };
    throw error;
  }

  return data as T;
}

export default fetcher;

