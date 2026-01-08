/**
 * BFF route for system info.
 * Proxies to backend system info endpoint.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      environment: string;
      api_version: string;
      backend_version: string;
      db_connected: boolean;
      redis_connected: boolean | null;
    }>("/admin/system/info", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch system info" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
