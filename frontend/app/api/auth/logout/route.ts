import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";
import { clearAuthCookies } from "@/lib/server/cookies";

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const refreshToken = cookieStore.get("refresh_token")?.value;

    // Call backend logout if refresh token exists
    if (refreshToken) {
      try {
        await backendFetch("/auth/logout", {
          method: "POST",
          body: { refresh_token: refreshToken },
        });
      } catch (error) {
        // Continue to clear cookies even if backend call fails
        console.error("Backend logout failed:", error);
      }
    }

    // Clear cookies
    const response = NextResponse.json({ status: "ok" }, { status: 200 });

    // Clear auth cookies using centralized helper
    clearAuthCookies(response);

    return response;
  } catch (error: any) {
    // Always clear cookies on logout attempt
    const response = NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Logout failed" } },
      { status: 500 },
    );

    // Clear auth cookies using centralized helper
    clearAuthCookies(response);

    return response;
  }
}

