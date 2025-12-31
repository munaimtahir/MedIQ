import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";
import { setAuthCookies, clearAuthCookies } from "@/lib/server/cookies";

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const refreshToken = cookieStore.get("refresh_token")?.value;

    if (!refreshToken) {
      return NextResponse.json(
        { error: { code: "UNAUTHORIZED", message: "No refresh token" } },
        { status: 401 },
      );
    }

    // Call backend refresh
    const { data, headers } = await backendFetch<{
      tokens: { access_token: string; refresh_token: string; token_type: string };
    }>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    });

    // Set new cookies (rotation)
    const response = NextResponse.json(
      { status: "ok" },
      {
        status: 200,
        headers: {
          "X-Request-ID": headers.get("X-Request-ID") || "",
        },
      },
    );

    // Set auth cookies using centralized helper
    setAuthCookies(response, {
      accessToken: data.tokens.access_token,
      refreshToken: data.tokens.refresh_token,
    });

    return response;
  } catch (error: any) {
    const status = error.status || 500;
    const backendError = error.error || {
      code: "INTERNAL_ERROR",
      message: "An error occurred",
    };

    // Clear cookies on refresh failure
    const response = NextResponse.json(
      {
        error: {
          code: backendError.code,
          message: backendError.message,
          request_id: error.request_id || backendError.request_id,
        },
      },
      {
        status,
        headers: error.request_id ? { "X-Request-ID": error.request_id } : undefined,
      },
    );

    // Clear auth cookies using centralized helper
    clearAuthCookies(response);

    return response;
  }
}

