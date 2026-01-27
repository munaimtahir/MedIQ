/**
 * Browser-side auth client.
 * Calls Next.js BFF endpoints (never directly to backend).
 */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  name: string;
  email: string;
  password: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: "STUDENT" | "ADMIN" | "REVIEWER";
  onboarding_completed: boolean;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at?: string;
}

export interface AuthError {
  code: string;
  message: string;
  details?: unknown;
  request_id?: string;
}

export interface AuthResponse<T = unknown> {
  data?: T;
  error?: AuthError;
  mfa_required?: boolean;
  mfa_token?: string;
  method?: string;
}

async function authFetch<T>(endpoint: string, options: RequestInit = {}): Promise<AuthResponse<T>> {
  const response = await fetch(`/api/auth${endpoint}`, {
    ...options,
    credentials: "include", // Include cookies
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    return {
      error: data.error || {
        code: "HTTP_ERROR",
        message: response.statusText,
      },
    };
  }

  // Pass through MFA fields if present
  const result: AuthResponse<T> = { data };
  if (data.mfa_required !== undefined) {
    result.mfa_required = data.mfa_required;
  }
  if (data.mfa_token !== undefined) {
    result.mfa_token = data.mfa_token;
  }
  if (data.method !== undefined) {
    result.method = data.method;
  }

  return result;
}

export const authClient = {
  /**
   * Login with email and password.
   */
  async login(payload: LoginRequest): Promise<AuthResponse<{ user: User }>> {
    return authFetch<{ user: User }>("/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Sign up new user.
   */
  async signup(payload: SignupRequest): Promise<AuthResponse<{ user: User }>> {
    return authFetch<{ user: User }>("/signup", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Get current user.
   */
  async me(): Promise<AuthResponse<{ user: User }>> {
    return authFetch<{ user: User }>("/me", {
      method: "GET",
    });
  },

  /**
   * Refresh access token.
   */
  async refresh(): Promise<AuthResponse<{ status: string }>> {
    return authFetch<{ status: string }>("/refresh", {
      method: "POST",
    });
  },

  /**
   * Logout.
   */
  async logout(): Promise<AuthResponse<{ status: string }>> {
    return authFetch<{ status: string }>("/logout", {
      method: "POST",
    });
  },
};
