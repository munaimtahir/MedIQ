/**
 * BFF route for admin audit log.
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

    const entity_type = searchParams.get("entity_type");
    const entity_id = searchParams.get("entity_id");
    const action = searchParams.get("action");
    const limit = searchParams.get("limit");

    if (entity_type) params.set("entity_type", entity_type);
    if (entity_id) params.set("entity_id", entity_id);
    if (action) params.set("action", action);
    if (limit) params.set("limit", limit);

    const queryString = params.toString() ? `?${params.toString()}` : "";

    const { data } = await backendFetch<unknown>(`/admin/audit${queryString}`, {
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
        message: "Failed to fetch audit log",
      };

      return NextResponse.json(
        { error: errorData },
        {
          status,
          headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
        },
      );
    }

    console.error("[Audit Route] Unexpected error:", error);
    return NextResponse.json(
      {
        error: {
          code: "INTERNAL_ERROR",
          message: error instanceof Error ? error.message : "Failed to fetch audit log",
        },
      },
      { status: 500 },
    );
  }
}
