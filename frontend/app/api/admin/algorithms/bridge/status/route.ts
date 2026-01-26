/**
 * BFF route for bridge status lookup.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);
    const userId = searchParams.get("user_id");

    const queryString = userId ? `?user_id=${userId}` : "";

    const { data } = await backendFetch<{
      user_id?: string;
      bridges?: Array<{
        id: string;
        from_profile: string;
        to_profile: string;
        status: string;
        started_at: string | null;
        finished_at: string | null;
        details: Record<string, unknown> | null;
      }>;
      summary?: {
        counts_by_status: Record<string, number>;
        total: number;
      };
    }>(`/admin/algorithms/bridge/status${queryString}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to load bridge status" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
