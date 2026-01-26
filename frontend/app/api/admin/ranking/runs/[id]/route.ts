/**
 * BFF route for a single ranking run
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const cookies = _request.headers.get("cookie") || "";
    const { id } = await params;

    const { data } = await backendFetch<unknown>(`/admin/ranking/runs/${id}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch ranking run" };
    return NextResponse.json({ error: errorData }, { status });
  }
}
