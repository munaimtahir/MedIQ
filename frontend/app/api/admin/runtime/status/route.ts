/**
 * BFF route for runtime control status.
 * Proxies GET /v1/admin/runtime/status to backend.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export interface RuntimeStatus {
  flags: {
    EXAM_MODE: { enabled: boolean; updated_at: string | null; updated_by: string | { id: string; email: string } | null; reason: string | null; source: string };
    FREEZE_UPDATES: { enabled: boolean; updated_at: string | null; updated_by: string | { id: string; email: string } | null; reason: string | null; source: string };
  };
  active_profile: { name: string; config: Record<string, string>; updated_at: string | null };
  module_overrides: Array<{ module_key: string; version_key: string; is_enabled: boolean; updated_at: string | null }>;
  resolved: {
    profile: string;
    modules: Record<string, string>;
    feature_toggles: Record<string, boolean>;
    freeze_updates: boolean;
    exam_mode: boolean;
    source: Record<string, unknown>;
  };
  last_changed: { action_type: string; created_at: string | null; actor_user_id: string | null } | null;
}

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { data } = await backendFetch<RuntimeStatus>("/admin/runtime/status", {
      method: "GET",
      cookies,
    });
    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status ?? 500;
    const errorData = err.error ?? { code: "INTERNAL_ERROR", message: "Failed to fetch runtime status" };
    return NextResponse.json({ error: errorData }, { status });
  }
}
