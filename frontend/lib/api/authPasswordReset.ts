/**
 * Password reset API client
 * Uses BFF /api/v1 routes so auth cookies are sent (same-origin).
 */

import fetcher from "../fetcher";

const API_BASE = "/api/v1";

export interface PasswordResetRequestResponse {
  status: string;
  message: string;
}

export interface PasswordResetConfirmRequest {
  token: string;
  new_password: string;
}

export interface PasswordResetConfirmResponse {
  status: string;
  message: string;
}

/**
 * Request password reset (optional - for forgot-password page)
 */
export async function requestReset(email: string): Promise<PasswordResetRequestResponse> {
  return fetcher<PasswordResetRequestResponse>(`${API_BASE}/auth/password-reset/request`, {
    method: "POST",
    body: { email },
  });
}

/**
 * Confirm password reset with token
 */
export async function confirmReset(
  token: string,
  newPassword: string,
): Promise<PasswordResetConfirmResponse> {
  return fetcher<PasswordResetConfirmResponse>(`${API_BASE}/auth/password-reset/confirm`, {
    method: "POST",
    body: { token, new_password: newPassword },
  });
}
