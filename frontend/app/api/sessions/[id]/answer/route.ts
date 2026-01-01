/**
 * BFF route for submitting an answer in a session.
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { id } = await params;
    const body = await request.json();

    const { data } = await backendFetch<unknown>(`/sessions/${id}/answer`, {
      method: "POST",
      cookies,
      body,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to submit answer" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
