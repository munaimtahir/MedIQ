/**
 * BFF route for rank runs (list and create).
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);

    const params = new URLSearchParams();
    const cohortKey = searchParams.get("cohort_key");
    const status = searchParams.get("status");
    const limit = searchParams.get("limit");

    if (cohortKey) params.set("cohort_key", cohortKey);
    if (status) params.set("status", status);
    if (limit) params.set("limit", limit);

    const query = params.toString() ? `?${params.toString()}` : "";

    const { data } = await backendFetch<
      Array<{
        id: string;
        cohort_key: string;
        model_version: string;
        status: string;
        started_at: string | null;
        finished_at: string | null;
        metrics: Record<string, unknown> | null;
        error: string | null;
        created_at: string;
      }>
    >(`/admin/rank/runs${query}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch rank runs" };

    return NextResponse.json({ error: errorData }, { status });
  }
}

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    const { data } = await backendFetch<{
      id: string;
      cohort_key: string;
      model_version: string;
      status: string;
      started_at: string | null;
      finished_at: string | null;
      metrics: Record<string, unknown> | null;
      error: string | null;
      created_at: string;
    }>("/admin/rank/runs", {
      method: "POST",
      body,
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to create rank run" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
