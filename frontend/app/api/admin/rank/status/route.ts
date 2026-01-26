/**
 * BFF route for rank status.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);
    const cohortKey = searchParams.get("cohort_key");

    const query = cohortKey ? `?cohort_key=${encodeURIComponent(cohortKey)}` : "";

    const { data } = await backendFetch<{
      mode: string;
      latest_run: {
        id: string | null;
        status: string | null;
        coverage: number | null;
        stability: number | null;
        created_at: string | null;
      } | null;
      eligible: boolean;
      reasons: string[];
    }>(`/admin/rank/status${query}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch rank status" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
