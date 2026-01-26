/**
 * BFF route for graph revision run metrics.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);
    const days = searchParams.get("days");

    const query = days ? `?days=${days}` : "";

    const { data } = await backendFetch<{
      runs: Array<{
        id: string;
        run_date: string;
        mode: string;
        metrics: Record<string, unknown> | null;
        status: string;
        created_at: string;
      }>;
    }>(`/admin/graph-revision/run-metrics${query}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch run metrics" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
