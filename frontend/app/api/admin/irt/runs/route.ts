/**
 * BFF route for IRT runs (list and create).
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);

    const params = new URLSearchParams();
    const status = searchParams.get("status");
    const modelType = searchParams.get("model_type");
    const limit = searchParams.get("limit");

    if (status) params.set("status", status);
    if (modelType) params.set("model_type", modelType);
    if (limit) params.set("limit", limit);

    const query = params.toString() ? `?${params.toString()}` : "";

    const { data } = await backendFetch<
      Array<{
        id: string;
        model_type: string;
        status: string;
        started_at: string | null;
        finished_at: string | null;
        metrics: Record<string, unknown> | null;
        error: string | null;
        created_at: string;
      }>
    >(`/admin/irt/runs${query}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch IRT runs" };

    return NextResponse.json({ error: errorData }, { status });
  }
}

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    const { data } = await backendFetch<{
      id: string;
      model_type: string;
      status: string;
      started_at: string | null;
      finished_at: string | null;
      metrics: Record<string, unknown> | null;
      error: string | null;
      created_at: string;
    }>("/admin/irt/runs", {
      method: "POST",
      body,
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to create IRT run" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
