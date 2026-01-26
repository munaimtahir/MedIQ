/**
 * BFF route for graph revision sync.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      id: string;
      status: string;
      started_at: string | null;
      finished_at: string | null;
      details_json: Record<string, unknown> | null;
      created_at: string;
    }>("/admin/graph-revision/sync", {
      method: "POST",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to trigger sync" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
