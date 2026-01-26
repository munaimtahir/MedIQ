/**
 * BFF route for freezing updates (safe mode).
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    await backendFetch("/admin/algorithms/runtime/freeze_updates", {
      method: "POST",
      body,
      cookies,
    });

    // Fetch updated runtime config
    const { data } = await backendFetch<{
      config: {
        active_profile: string;
        overrides: Record<string, string>;
        safe_mode: { freeze_updates: boolean; prefer_cache: boolean };
      };
      active_since: string;
      last_switch_events: Array<unknown>;
      bridge_job_health: {
        counts_by_status: Record<string, number>;
        total: number;
      };
    }>("/admin/algorithms/runtime", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to freeze updates" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
