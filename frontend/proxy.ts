/**
 * Next.js 16 Proxy file - Required by Next.js 16+
 *
 * Next.js 16.1.1 automatically runs this file for every request when it exists.
 * This is a PASSTHROUGH proxy - it does NOT perform authentication.
 *
 * IMPORTANT: Route protection is enforced via Server Component layout guards:
 * - `app/student/layout.tsx` calls `await requireUser()`
 * - `app/admin/layout.tsx` calls `await requireRole(["ADMIN", "REVIEWER"])`
 *
 * The proxy function below is a minimal passthrough that satisfies Next.js 16
 * requirements without duplicating auth logic. Auth is handled by layouts.
 *
 * Why not do auth in proxy?
 * - Layout guards run at component render time with full async/await support
 * - They can access cookies and make backend calls directly
 * - They provide proper redirects without edge runtime limitations
 * - Backend RBAC dependencies provide the enforcement layer
 */

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

/**
 * Passthrough proxy function - satisfies Next.js 16 requirement.
 * Does NOT perform authentication - that's handled by layout guards.
 */
export default function proxy(request: NextRequest): NextResponse {
  // Passthrough - no auth logic here
  // Layout guards handle authentication/authorization
  return NextResponse.next();
}

/**
 * Proxy configuration - which routes to apply proxy to.
 * Currently empty (passthrough for all), as auth is in layouts.
 */
export const config = {
  matcher: [],
};

// Re-export auth guard functions for backward compatibility
export * from "@/lib/server/authGuard";

