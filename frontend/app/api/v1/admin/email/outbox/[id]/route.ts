/**
 * BFF route for getting email outbox item by ID.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { id } = await params;

    const { data } = await backendFetch<unknown>(`/admin/email/outbox/${id}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch email outbox item" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
