/**
 * Cookie utilities for Next.js API routes.
 * Centralized cookie handling with production security enforcement.
 */

import { NextResponse } from "next/server";

/**
 * Determine if we're in production.
 * Production requires Secure=true cookies (HTTPS only).
 */
function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

/**
 * Get cookie options for access or refresh token.
 * Enforces Secure=true in production, Secure=false in dev.
 */
export function getCookieOptions(kind: "access" | "refresh"): {
  httpOnly: boolean;
  secure: boolean;
  sameSite: "lax" | "strict" | "none";
  path: string;
  maxAge: number;
  domain?: string;
} {
  const isProd = isProduction();

  // Enforce Secure=true in production (foolproof)
  // If COOKIE_SECURE is set to false in prod, ignore it and force true
  let secure: boolean;
  if (isProd) {
    secure = true; // ALWAYS true in production
    if (process.env.COOKIE_SECURE === "false") {
      // Log warning (without secrets) if someone tries to disable secure in prod
      console.warn(
        "[Cookie Security] COOKIE_SECURE=false ignored in production. Cookies are always Secure=true in production.",
      );
    }
  } else {
    // In dev, default to false (works with http://localhost)
    secure = process.env.COOKIE_SECURE === "true";
  }

  const sameSite = (process.env.COOKIE_SAMESITE as "lax" | "strict" | "none") || "lax";
  const domain = process.env.COOKIE_DOMAIN?.trim() || undefined; // Only set if non-empty

  // Get maxAge from env
  const accessMaxAge = parseInt(process.env.ACCESS_COOKIE_MAXAGE_SECONDS || "900", 10);
  const refreshMaxAge = parseInt(process.env.REFRESH_COOKIE_MAXAGE_SECONDS || "1209600", 10);

  return {
    httpOnly: true, // Always httpOnly
    secure,
    sameSite,
    path: "/",
    maxAge: kind === "access" ? accessMaxAge : refreshMaxAge,
    ...(domain && { domain }), // Only include domain if set
  };
}

/**
 * Set authentication cookies on a NextResponse.
 * Uses Next.js Response cookies API.
 */
export function setAuthCookies(
  response: NextResponse,
  tokens: { accessToken: string; refreshToken: string },
): NextResponse {
  const accessOptions = getCookieOptions("access");
  const refreshOptions = getCookieOptions("refresh");

  // Use Next.js Response cookies API
  response.cookies.set("access_token", tokens.accessToken, {
    httpOnly: accessOptions.httpOnly,
    secure: accessOptions.secure,
    sameSite: accessOptions.sameSite,
    path: accessOptions.path,
    maxAge: accessOptions.maxAge,
    ...(accessOptions.domain && { domain: accessOptions.domain }),
  });

  response.cookies.set("refresh_token", tokens.refreshToken, {
    httpOnly: refreshOptions.httpOnly,
    secure: refreshOptions.secure,
    sameSite: refreshOptions.sameSite,
    path: refreshOptions.path,
    maxAge: refreshOptions.maxAge,
    ...(refreshOptions.domain && { domain: refreshOptions.domain }),
  });

  return response;
}

/**
 * Clear authentication cookies on a NextResponse.
 * Sets Max-Age=0 to expire cookies immediately.
 */
export function clearAuthCookies(response: NextResponse): NextResponse {
  const accessOptions = getCookieOptions("access");
  const refreshOptions = getCookieOptions("refresh");

  // Clear by setting Max-Age=0
  response.cookies.set("access_token", "", {
    httpOnly: accessOptions.httpOnly,
    secure: accessOptions.secure,
    sameSite: accessOptions.sameSite,
    path: accessOptions.path,
    maxAge: 0,
    ...(accessOptions.domain && { domain: accessOptions.domain }),
  });

  response.cookies.set("refresh_token", "", {
    httpOnly: refreshOptions.httpOnly,
    secure: refreshOptions.secure,
    sameSite: refreshOptions.sameSite,
    path: refreshOptions.path,
    maxAge: 0,
    ...(refreshOptions.domain && { domain: refreshOptions.domain }),
  });

  return response;
}

