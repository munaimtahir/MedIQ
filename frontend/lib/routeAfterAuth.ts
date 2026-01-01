/**
 * Post-auth routing utilities for consistent navigation after login/signup.
 * Used by both email auth and OAuth flows.
 */

import { authClient, type User } from "@/lib/authClient";

export interface RouteAfterAuthOptions {
  redirectParam?: string | null;
}

/**
 * Determines the correct route after successful authentication.
 * Fetches user profile to check onboarding status and role.
 *
 * @returns The path to navigate to
 */
export async function getRouteAfterAuth(
  options?: RouteAfterAuthOptions
): Promise<string> {
  const { redirectParam } = options || {};

  try {
    // Fetch fresh user data to get onboarding status
    const result = await authClient.me();

    if (result.error || !result.data?.user) {
      // Fallback if we can't get user data
      return "/student/dashboard";
    }

    const user = result.data.user as User;

    // If there's a redirect param and user is onboarded, use it
    if (redirectParam && user.onboarding_completed) {
      return redirectParam;
    }

    // Check onboarding status first
    if (!user.onboarding_completed) {
      return "/onboarding";
    }

    // Route based on role
    if (user.role === "ADMIN" || user.role === "REVIEWER") {
      return "/admin";
    }

    return "/student/dashboard";
  } catch {
    // Fallback on error
    return "/student/dashboard";
  }
}

/**
 * Execute the post-auth routing flow.
 * Call this after successful login/signup.
 *
 * @param router - Next.js router instance
 * @param options - Routing options
 */
export async function routeAfterAuth(
  navigate: (path: string) => void,
  options?: RouteAfterAuthOptions
): Promise<void> {
  const path = await getRouteAfterAuth(options);
  navigate(path);
}
