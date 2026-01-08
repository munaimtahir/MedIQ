/**
 * BFF route for fetching blocks.
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const year = searchParams.get("year");
    
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const path = `/syllabus/blocks${year ? `?year=${encodeURIComponent(year)}` : ""}`;
    const { data, status, headers } = await backendFetch<unknown[]>(path, {
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
    const err = error as { status?: number; error?: { code: string; message: string; request_id?: string }; request_id?: string };
    const status = err.status || 500;
    const backendError = err.error || {
      code: "INTERNAL_ERROR",
      message: "An error occurred",
    };
    return NextResponse.json(
      {
        error: {
          code: backendError.code,
          message: backendError.message,
          request_id: err.request_id || backendError.request_id,
        },
      },
      {
        status,
        headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
      },
    );
  }
}
