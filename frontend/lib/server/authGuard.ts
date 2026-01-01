/**
 * Server-only authentication guard library for Next.js Server Components.
 * This file MUST be server-only - never imported in client components.
 */

import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { backendFetch } from "./backendClient";

/**
 * User type matching backend schema.
 */
export interface User {
  id: string;
  email: string;
  name: string;
  role: "STUDENT" | "ADMIN" | "REVIEWER";
  is_active: boolean;
  email_verified: boolean;
  onboarding_completed: boolean;
}

/**
 * Get access token from cookies.
 * Returns the access_token cookie value or null if not present.
 */
export async function getAccessTokenFromCookies(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get("access_token")?.value || null;
}

/**
 * Get refresh token from cookies.
 * Returns the refresh_token cookie value or null if not present.
 */
export async function getRefreshTokenFromCookies(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get("refresh_token")?.value || null;
}

/**
 * Get user from backend /v1/auth/me endpoint.
 * Returns user object on success, null on 401 (not authenticated).
 * Throws only on unexpected errors (network, 500, etc.).
 */
export async function getUser(): Promise<User | null> {
  const accessToken = await getAccessTokenFromCookies();
  const refreshToken = await getRefreshTokenFromCookies();

  // If no tokens at all, return null (not authenticated)
  if (!accessToken && !refreshToken) {
    return null;
  }

  try {
    // Build cookie string for forwarding to backend
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    // Call backend /v1/auth/me server-to-server
    const { data } = await backendFetch<{ user: User }>("/auth/me", {
      method: "GET",
      cookies: cookieHeader,
    });

    return data.user || null;
  } catch (error: any) {
    // If 401 (unauthorized), return null (not authenticated)
    if (error.status === 401) {
      return null;
    }

    // For other errors (network, 500, etc.), throw to let caller handle
    throw error;
  }
}

/**
 * Require user to be authenticated.
 * Redirects to /login if not authenticated.
 *
 * @param opts - Options object
 * @param opts.redirectTo - Optional redirect path after login (will be added as query param)
 * @param opts.requireOnboarding - If true, redirects to /onboarding if not completed (default: false)
 * @returns User object if authenticated (never returns null - redirects instead)
 */
export async function requireUser(opts?: {
  redirectTo?: string;
  requireOnboarding?: boolean;
}): Promise<User> {
  const user = await getUser();

  if (!user) {
    const redirectPath = opts?.redirectTo
      ? `/login?redirect=${encodeURIComponent(opts.redirectTo)}`
      : "/login";
    redirect(redirectPath);
  }

  // Check onboarding status if required
  if (opts?.requireOnboarding && !user.onboarding_completed) {
    redirect("/onboarding");
  }

  return user;
}

/**
 * Require user to be authenticated AND have completed onboarding.
 * Redirects to /login if not authenticated.
 * Redirects to /onboarding if onboarding not completed.
 *
 * @param opts - Options object
 * @param opts.redirectTo - Optional redirect path after login (will be added as query param)
 * @returns User object if authenticated and onboarded
 */
export async function requireOnboardedUser(opts?: { redirectTo?: string }): Promise<User> {
  return requireUser({ ...opts, requireOnboarding: true });
}

/**
 * Require user to have one of the specified roles.
 * Redirects to /login if not authenticated, or /403 if wrong role.
 *
 * @param roles - Array of allowed roles
 * @param opts - Options object
 * @param opts.forbiddenTo - Optional redirect path for forbidden access (default: /403)
 * @param opts.redirectTo - Optional redirect path after login (for unauthenticated users)
 * @returns User object if authenticated and authorized
 */
export async function requireRole(
  roles: Array<"ADMIN" | "REVIEWER" | "STUDENT">,
  opts?: { forbiddenTo?: string; redirectTo?: string },
): Promise<User> {
  const user = await requireUser({ redirectTo: opts?.redirectTo });

  // Check if user has required role
  if (!roles.includes(user.role)) {
    // Wrong role, redirect to forbidden page
    const forbiddenPath = opts?.forbiddenTo || "/403";
    redirect(forbiddenPath);
  }

  return user;
}

/**
 * Redirect if user is already authenticated.
 * Useful for /login and /signup pages to redirect logged-in users away.
 *
 * @param to - Redirect destination (e.g., "/student/dashboard" or "/admin")
 */
export async function redirectIfAuthed(to: string): Promise<void> {
  const user = await getUser();

  if (user) {
    // User is authenticated, redirect based on role
    if (to) {
      redirect(to);
    } else {
      // Default redirect based on role
      if (user.role === "STUDENT") {
        redirect("/student/dashboard");
      } else if (user.role === "ADMIN" || user.role === "REVIEWER") {
        redirect("/admin");
      } else {
        redirect("/");
      }
    }
  }
  // If not authenticated, do nothing (let page render)
}

