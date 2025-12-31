import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access_token")?.value;

    if (!accessToken) {
      return NextResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Not authenticated" } },
        { status: 401 },
      );
    }

    // Call backend /auth/me
    // Build cookie string for forwarding
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");
    const { data, headers } = await backendFetch<{ user: unknown }>("/auth/me", {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(
      { user: data.user },
      {
        status: 200,
        headers: {
          "X-Request-ID": headers.get("X-Request-ID") || "",
        },
      },
    );
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

