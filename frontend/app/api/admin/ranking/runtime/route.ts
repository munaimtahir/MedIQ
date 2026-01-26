/**
 * BFF route for ranking runtime status
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(_request: NextRequest) {
  try {
    const cookies = _request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      requested_mode: string;
      effective_mode: string;
      freeze: boolean;
      warnings: string[];
      readiness: { ready: boolean; checks: Record<string, unknown>; blocking_reasons: string[] } | null;
      recent_parity: {
        k: number;
        epsilon?: number;
        pass: boolean;
        max_abs_percentile_diff: number | null;
        rank_mismatch_count: number | null;
        last_checked_at: string | null;
      } | null;
    }>("/admin/ranking/runtime", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch ranking runtime" };
    return NextResponse.json({ error: errorData }, { status });
  }
}
