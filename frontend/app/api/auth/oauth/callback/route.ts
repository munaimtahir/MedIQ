/**
 * OAuth callback BFF route.
 * Receives an exchange code from the backend OAuth callback,
 * exchanges it for tokens, sets cookies, and redirects to the appropriate page.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";
import { setAuthCookies } from "@/lib/server/cookies";

const FRONTEND_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

interface OAuthExchangeResponse {
  user?: {
    id: string;
    name: string;
    email: string;
    role: string;
    onboarding_completed: boolean;
  };
  tokens?: {
    access_token: string;
    refresh_token: string;
    token_type: string;
  };
  mfa_required?: boolean;
  mfa_token?: string;
  method?: string;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get("code");

  // If no code, this is likely an error redirect - pass through to login page
  if (!code) {
    const error = searchParams.get("error");
    const provider = searchParams.get("provider");
    const linkRequired = searchParams.get("link_required");
    const linkToken = searchParams.get("link_token");
    const email = searchParams.get("email");

    // Build redirect URL with query params
    const params = new URLSearchParams();
    if (error) params.set("error", error);
    if (provider) params.set("provider", provider);
    if (linkRequired) params.set("link_required", linkRequired);
    if (linkToken) params.set("link_token", linkToken);
    if (email) params.set("email", email);

    const redirectUrl = params.toString() ? `/login?${params.toString()}` : "/login";
    return NextResponse.redirect(new URL(redirectUrl, FRONTEND_URL));
  }

  try {
    // Exchange the code for tokens via backend
    const { data } = await backendFetch<OAuthExchangeResponse>("/auth/oauth/exchange", {
      method: "POST",
      body: { code },
    });

    // Handle MFA required
    if (data.mfa_required) {
      const params = new URLSearchParams({
        mfa: "true",
        mfa_token: data.mfa_token || "",
        method: data.method || "totp",
      });
      return NextResponse.redirect(new URL(`/login?${params.toString()}`, FRONTEND_URL));
    }

    // If we have tokens, set cookies and redirect
    if (data.tokens) {
      // Determine redirect destination based on user data
      let redirectPath = "/student/dashboard";

      if (data.user) {
        if (!data.user.onboarding_completed) {
          redirectPath = "/onboarding";
        } else if (data.user.role === "ADMIN") {
          redirectPath = "/admin/dashboard";
        }
      }

      // Create redirect response
      const response = NextResponse.redirect(new URL(redirectPath, FRONTEND_URL));

      // Set auth cookies
      setAuthCookies(response, {
        accessToken: data.tokens.access_token,
        refreshToken: data.tokens.refresh_token,
      });

      return response;
    }

    // Fallback - no tokens, redirect to login
    return NextResponse.redirect(new URL("/login?error=OAUTH_NO_TOKENS", FRONTEND_URL));
  } catch (error: unknown) {
    console.error("[OAuth Callback] Exchange failed:", error);

    // Extract error code if available
    const errorObj = error as { error?: { code?: string } };
    const errorCode = errorObj?.error?.code || "OAUTH_EXCHANGE_FAILED";

    return NextResponse.redirect(new URL(`/login?error=${errorCode}`, FRONTEND_URL));
  }
}
