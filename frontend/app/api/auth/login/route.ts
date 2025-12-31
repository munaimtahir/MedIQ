import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";
import { setAuthCookies } from "@/lib/server/cookies";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password } = body;

    if (!email || !password) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "Email and password are required" } },
        { status: 400 },
      );
    }

    // Call backend login
    const { data, headers } = await backendFetch<{
      user: unknown;
      tokens?: { access_token: string; refresh_token: string; token_type: string };
      mfa_required?: boolean;
      mfa_token?: string;
      method?: string;
    }>("/auth/login", {
      method: "POST",
      body: { email, password },
    });

    // Handle MFA required
    if (data.mfa_required) {
      return NextResponse.json(
        {
          mfa_required: true,
          mfa_token: data.mfa_token,
          method: data.method,
        },
        { status: 200 },
      );
    }

    // Set cookies if tokens present
    if (data.tokens) {
      const response = NextResponse.json(
        { user: data.user },
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
    }

    return NextResponse.json({ user: data.user }, { status: 200 });
  } catch (error: any) {
    const status = error.status || 500;
    const backendError = error.error || {
      code: "INTERNAL_ERROR",
      message: "An error occurred",
    };

    return NextResponse.json(
      {
        error: {
          code: backendError.code,
          message: backendError.message,
          details: backendError.details,
          request_id: error.request_id || backendError.request_id,
        },
      },
      {
        status,
        headers: error.request_id ? { "X-Request-ID": error.request_id } : undefined,
      },
    );
  }
}

