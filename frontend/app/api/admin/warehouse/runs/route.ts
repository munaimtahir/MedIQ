/**
 * BFF route for warehouse export runs
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);

    const limit = searchParams.get("limit");
    const dataset = searchParams.get("dataset");
    const status = searchParams.get("status");

    const queryParams = new URLSearchParams();
    if (limit) queryParams.append("limit", limit);
    if (dataset) queryParams.append("dataset", dataset);
    if (status) queryParams.append("status", status);

    const url = `/admin/warehouse/runs${queryParams.toString() ? `?${queryParams.toString()}` : ""}`;

    const { data } = await backendFetch<
      Array<{
        run_id: string;
        dataset: string;
        run_type: string;
        status: string;
        rows_exported: number;
        files_written: number;
        manifest_path: string | null;
        last_error: string | null;
        created_at: string | null;
        started_at: string | null;
        finished_at: string | null;
        range_start: string | null;
        range_end: string | null;
      }>
    >(url, {
      method: "GET",
      cookies,
    });

    return NextResponse.json({ runs: data, total: data.length }, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch export runs" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
