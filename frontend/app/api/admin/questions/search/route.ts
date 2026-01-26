/**
 * API route for questions search (proxies to backend)
 */

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const { searchParams } = new URL(request.url);

    // Build query params
    const params = new URLSearchParams();
    searchParams.forEach((value, key) => {
      params.append(key, value);
    });

    const queryString = params.toString() ? `?${params.toString()}` : "";

    const { data } = await backendFetch<unknown>(`/admin/questions/search${queryString}`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    if (error && typeof error === "object" && "status" in error && "error" in error) {
      const err = error as {
        status?: number;
        error?: { code: string; message: string; details?: unknown };
        request_id?: string;
      };
      const status = err.status || 500;
      const errorData = err.error || {
        code: "INTERNAL_ERROR",
        message: "Search failed",
      };

      return NextResponse.json(
        { error: errorData },
        {
          status,
          headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
        },
      );
    }

    console.error("[Search Route] Unexpected error:", error);
    return NextResponse.json(
      {
        error: {
          code: "INTERNAL_ERROR",
          message: error instanceof Error ? error.message : "Search failed",
        },
      },
      { status: 500 },
    );
  }
}
