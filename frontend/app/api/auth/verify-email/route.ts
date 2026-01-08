/**
 * BFF route for email verification.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");
    const body = await request.json();

    const { data, status, headers } = await backendFetch<{
      status: string;
      message: string;
    }>("/auth/verify-email", {
      method: "POST",
      cookies: cookieHeader,
      body: body, // backendFetch handles JSON.stringify internally
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
      message: "Failed to verify email",
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
