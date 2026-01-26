/**
 * BFF route for graph revision activation.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    const { data } = await backendFetch<{
      message: string;
      eligible: boolean;
      reasons: string[];
    }>("/admin/graph-revision/activate", {
      method: "POST",
      body,
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to activate graph revision" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
