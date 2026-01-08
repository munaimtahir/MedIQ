import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";
import { setAuthCookies } from "@/lib/server/cookies";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, email, password } = body;

    if (!name || !email || !password) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "Name, email, and password are required" } },
        { status: 400 },
      );
    }

    // Call backend signup
    const { data, headers } = await backendFetch<{
      user: unknown;
      message: string;
    }>("/auth/signup", {
      method: "POST",
      body: { name, email, password },
    });

    // Signup no longer returns tokens - user must verify email first
    const response = NextResponse.json(
      { user: data.user, message: data.message },
      {
        status: 201,
        headers: {
          "X-Request-ID": headers.get("X-Request-ID") || "",
        },
      },
    );

    return response;
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
