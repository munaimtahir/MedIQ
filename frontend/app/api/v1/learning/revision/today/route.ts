/**
 * BFF route for revision today.
 * Proxies to backend GET /learning/revision/today with auth.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { data } = await backendFetch<{
      due_today_total: number;
      overdue_total: number;
      themes: Array<{
        theme_id: number;
        theme_name: string;
        block_id: number;
        block_name: string;
        due_count_today: number;
        overdue_count: number;
        next_due_at: string | null;
      }>;
      recommended_theme_ids: number[];
    }>("/learning/revision/today", { method: "GET", cookies });
    return NextResponse.json(data, { status: 200 });
  } catch (e: unknown) {
    const err = e as { status?: number; error?: { code: string; message: string } };
    const status = err.status ?? 500;
    const body = err.error ?? { code: "INTERNAL_ERROR", message: "Failed to load revision data" };
    return NextResponse.json({ error: body }, { status });
  }
}
