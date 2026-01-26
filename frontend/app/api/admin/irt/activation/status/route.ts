/**
 * BFF route for IRT activation status.
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      flags: {
        active: boolean;
        scope: string;
        model: string;
        shadow: boolean;
      };
      latest_decision: {
        eligible: boolean | null;
        run_id: string | null;
        created_at: string | null;
      };
      recent_events: Array<{
        event_type: string;
        created_at: string;
        created_by: string;
        reason: string | null;
      }>;
    }>("/admin/irt/activation/status", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch activation status" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
