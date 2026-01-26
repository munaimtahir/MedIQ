/**
 * BFF route for listing ranking runs
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit");
    const queryParams = new URLSearchParams();
    if (limit) queryParams.append("limit", limit);
    const url = `/admin/ranking/runs${queryParams.toString() ? `?${queryParams.toString()}` : ""}`;

    const { data } = await backendFetch<{ runs: unknown[] }>(url, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch ranking runs" };
    return NextResponse.json({ error: errorData }, { status });
  }
}
