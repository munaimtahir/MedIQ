/**
 * BFF route for running incremental export
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    // Backend expects query params, not body
    const { reason, confirmation_phrase } = body;
    const queryParams = new URLSearchParams();
    queryParams.append("reason", reason);
    queryParams.append("confirmation_phrase", confirmation_phrase);

    const { data } = await backendFetch<{ run_ids: string[]; status: string }>(
      `/admin/warehouse/export/incremental?${queryParams.toString()}`,
      {
        method: "POST",
        cookies,
      }
    );

    // Backend returns { run_ids: string[], status: string }
    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to run incremental export" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
