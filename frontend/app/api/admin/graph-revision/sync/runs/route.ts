/**
 * BFF route for graph revision sync runs.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit");

    const query = limit ? `?limit=${limit}` : "";

    const { data } = await backendFetch<
      Array<{
        id: string;
        status: string;
        started_at: string | null;
        finished_at: string | null;
        details_json: Record<string, unknown> | null;
        created_at: string;
      }>
    >(`/admin/graph-revision/sync/runs${query}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch sync runs" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
