/**
 * BFF route for warehouse runtime status
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      requested_mode: string;
      warehouse_freeze: boolean;
      last_export_runs: Array<{
        run_id: string;
        dataset: string;
        run_type: string;
        status: string;
        rows_exported: number;
        files_written: number;
        created_at: string | null;
      }>;
    }>("/admin/warehouse/runtime", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch warehouse runtime" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
