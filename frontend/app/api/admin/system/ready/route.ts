/**
 * BFF route for system readiness check.
 * Proxies to backend /ready endpoint.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      status: "ok" | "degraded" | "down";
      checks: Record<string, { status: "ok" | "degraded" | "down"; message?: string | null }>;
      request_id: string;
    }>("/ready", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to check system readiness" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
