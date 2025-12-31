/**
 * Server-to-server backend client for Next.js API routes.
 * This should NEVER be imported in client-side code.
 */

const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";

export interface BackendError {
  error: {
    code: string;
    message: string;
    details?: unknown;
    request_id?: string;
  };
}

export interface BackendResponse<T> {
  data?: T;
  error?: BackendError["error"];
  request_id?: string;
}

/**
 * Fetch from backend API (server-to-server only).
 */
export async function backendFetch<T>(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    headers?: Record<string, string>;
    cookies?: string; // Forward cookies from Next.js request
  } = {},
): Promise<{ data: T; status: number; headers: Headers }> {
  const { method = "GET", body, headers = {}, cookies } = options;

  const url = `${BACKEND_URL}/v1${path}`;
  const requestHeaders: HeadersInit = {
    "Content-Type": "application/json",
    ...headers,
  };

  // Forward Authorization header if access_token cookie is present
  if (cookies) {
    // Extract access_token from cookie string
    const accessTokenMatch = cookies.match(/access_token=([^;]+)/);
    if (accessTokenMatch) {
      requestHeaders["Authorization"] = `Bearer ${accessTokenMatch[1]}`;
    }
  }

  const response = await fetch(url, {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });

  const responseData = await response.json().catch(() => ({}));

  // Extract request ID from response headers
  const requestId = response.headers.get("X-Request-ID") || undefined;

  if (!response.ok) {
    const error: BackendError = responseData;
    throw {
      status: response.status,
      error: error.error || {
        code: "HTTP_ERROR",
        message: response.statusText,
        request_id: requestId,
      },
      request_id: requestId,
    };
  }

  return {
    data: responseData as T,
    status: response.status,
    headers: response.headers,
  };
}

