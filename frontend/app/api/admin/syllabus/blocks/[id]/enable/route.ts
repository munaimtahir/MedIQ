/**
 * BFF route for enabling a block.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<unknown>(`/admin/syllabus/blocks/${params.id}/enable`, {
      method: "POST",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to enable block" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
