/**
 * Helpers for API error handling.
 * BFF returns { error: { code, message } }; fetcher throws { status, error }.
 */

export type ApiErrorPayload = { status?: number; error?: unknown };

/**
 * Extract user-facing message from BFF/fetcher error.
 * Handles { status, error } where error is { error: { message } } or { detail }.
 */
export function getMessageFromApiError(err: unknown, fallback: string): string {
  if (err instanceof Error) return err.message;
  const o = err as ApiErrorPayload;
  const e = o?.error as { error?: { message?: string }; message?: string; detail?: string } | undefined;
  return (
    e?.error?.message ??
    e?.message ??
    (typeof e?.detail === "string" ? e.detail : null) ??
    fallback
  );
}

/**
 * Whether the error is an HTTP 401 (unauthorized).
 */
export function is401(err: unknown): boolean {
  const o = err as ApiErrorPayload;
  return o?.status === 401;
}
