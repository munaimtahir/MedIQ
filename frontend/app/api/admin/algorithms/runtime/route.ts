/**
 * BFF route for algorithm runtime configuration.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      config: {
        active_profile: string;
        overrides: Record<string, string>;
        safe_mode: { freeze_updates: boolean; prefer_cache: boolean };
      };
      active_since: string;
      last_switch_events: Array<{
        id: string;
        previous_config: {
          active_profile: string;
          config_json: {
            profile: string;
            overrides: Record<string, string>;
            safe_mode: { freeze_updates: boolean; prefer_cache: boolean };
          };
          active_since: string;
        };
        new_config: {
          active_profile: string;
          config_json: {
            profile: string;
            overrides: Record<string, string>;
            safe_mode: { freeze_updates: boolean; prefer_cache: boolean };
          };
          active_since: string;
        };
        reason: string | null;
        created_at: string;
        created_by: string;
      }>;
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
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch runtime config" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
