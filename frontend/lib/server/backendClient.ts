/**
 * Server-to-server backend client for Next.js API routes.
 * This should NEVER be imported in client-side code.
 */

// Use localhost when running dev on host; Docker sets BACKEND_URL=http://backend:8000
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

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
 * Build error object from backend response (supports { error } and { detail }).
 */
function parseBackendError(
  responseData: Record<string, unknown>,
  status: number,
  statusText: string,
  requestId?: string,
): { code: string; message: string; request_id?: string } {
  const e = responseData?.error as { code?: string; message?: string } | undefined;
  if (e?.code && e?.message) {
    return { code: e.code, message: e.message, request_id: requestId };
  }
  const detail = responseData?.detail as string | undefined;
  const message = detail || statusText || "Request failed";
  return {
    code: status === 401 ? "UNAUTHORIZED" : "HTTP_ERROR",
    message,
    request_id: requestId,
  };
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
    queryParams?: Record<string, string | number | boolean | undefined>;
  } = {},
): Promise<{ data: T; status: number; headers: Headers }> {
  const { method = "GET", body, headers = {}, cookies, queryParams } = options;

  let url = `${BACKEND_URL}/v1${path}`;
  if (queryParams) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(queryParams)) {
      if (value !== undefined) {
        params.append(key, String(value));
      }
    }
    const queryString = params.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }
  const requestHeaders: HeadersInit = {
    "Content-Type": "application/json",
    ...headers,
  };

  if (cookies) {
    const accessTokenMatch = cookies.match(/access_token=([^;]+)/);
    if (accessTokenMatch) {
      requestHeaders["Authorization"] = `Bearer ${accessTokenMatch[1]}`;
    }
    requestHeaders["Cookie"] = cookies;
  }

  const response = await fetch(url, {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });

  const responseData = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  const requestId = response.headers.get("X-Request-ID") || undefined;

  if (!response.ok) {
    throw {
      status: response.status,
      error: parseBackendError(
        responseData,
        response.status,
        response.statusText,
        requestId,
      ),
      request_id: requestId,
    };
  }

  return {
    data: responseData as T,
    status: response.status,
    headers: response.headers,
  };
}
