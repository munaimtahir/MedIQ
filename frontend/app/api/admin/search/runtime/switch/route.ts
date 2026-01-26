/**
 * API route for switching search runtime (proxies to backend)
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

    const { data } = await backendFetch<unknown>("/admin/search/runtime/switch", {
      method: "POST",
      cookies: cookieHeader,
      body,
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
        message: "Failed to switch search runtime",
      };

      return NextResponse.json(
        { error: errorData },
        {
          status,
          headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
        },
      );
    }

    console.error("[Search Runtime Switch Route] Unexpected error:", error);
    return NextResponse.json(
      {
        error: {
          code: "INTERNAL_ERROR",
          message: error instanceof Error ? error.message : "Failed to switch search runtime",
        },
      },
      { status: 500 },
    );
  }
}
