import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Decode JWT without verification (for routing only).
 * Backend always verifies for actual authorization.
 */
function decodeJWT(token: string): { sub?: string; role?: string; exp?: number; type?: string } | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const payload = parts[1];
    // Handle base64url encoding (JWT standard)
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const decoded = Buffer.from(padded, "base64").toString("utf-8");
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public routes - no auth required
  if (
    pathname === "/login" ||
    pathname === "/signup" ||
    pathname === "/" ||
    pathname.startsWith("/api/auth") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/static")
  ) {
    return NextResponse.next();
  }

  // Get cookies
  const accessToken = request.cookies.get("access_token")?.value;
  const refreshToken = request.cookies.get("refresh_token")?.value;

  // Check if user has any auth token
  const hasAuth = !!(accessToken || refreshToken);

  // Student routes - require auth
  if (pathname.startsWith("/student")) {
    if (!hasAuth) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
    return NextResponse.next();
  }

  // Admin routes - require auth + ADMIN/REVIEWER role
  if (pathname.startsWith("/admin")) {
    if (!hasAuth) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }

    // Try to decode access token for role check
    if (accessToken) {
      const payload = decodeJWT(accessToken);
      const role = payload?.role;
      const tokenType = payload?.type;

      // Reject MFA pending tokens (not access tokens)
      if (tokenType === "mfa_pending") {
        return NextResponse.redirect(new URL("/login", request.url));
      }

      if (role && role !== "ADMIN" && role !== "REVIEWER") {
        // Not authorized - redirect to 403
        return NextResponse.redirect(new URL("/403", request.url));
      }
    }

    // If no access token but has refresh token, let through
    // Page-level auth will handle refresh and redirect if needed
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};

