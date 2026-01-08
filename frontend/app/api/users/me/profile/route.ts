/**
 * BFF route for user profile (GET and PUT).
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET() {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const { data, status, headers } = await backendFetch<unknown>("/users/me/profile", {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data, {
      status,
      headers: {
        "X-Request-ID": headers.get("X-Request-ID") || "",
      },
    });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || {
      code: "INTERNAL_ERROR",
      message: "An error occurred",
    };
    return NextResponse.json(
      {
        error: {
          code: errorData.code,
          message: errorData.message,
          request_id: err.status ? undefined : (error as { request_id?: string }).request_id,
        },
      },
      {
        status,
        headers: (error as { request_id?: string }).request_id
          ? { "X-Request-ID": (error as { request_id?: string }).request_id }
          : undefined,
      },
    );
  }
}

export async function PUT(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");
    const body = await request.json();

    const { data, status, headers } = await backendFetch<unknown>("/users/me/profile", {
      method: "PUT",
      cookies: cookieHeader,
      body: JSON.stringify(body),
      headers: {
        "Content-Type": "application/json",
      },
    });

    return NextResponse.json(data, {
      status,
      headers: {
        "X-Request-ID": headers.get("X-Request-ID") || "",
      },
    });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || {
      code: "INTERNAL_ERROR",
      message: "Failed to update profile",
    };

    return NextResponse.json(
      {
        error: {
          code: errorData.code,
          message: errorData.message,
          request_id: (error as { request_id?: string }).request_id,
        },
      },
      {
        status,
        headers: (error as { request_id?: string }).request_id
          ? { "X-Request-ID": (error as { request_id?: string }).request_id }
          : undefined,
      },
    );
  }
}
