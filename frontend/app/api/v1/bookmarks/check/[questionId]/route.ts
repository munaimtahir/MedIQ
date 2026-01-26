/**
 * BFF route for bookmark check.
 * Proxies to backend GET /bookmarks/check/:questionId with auth.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ questionId: string }> },
) {
  try {
    const { questionId } = await params;
    const cookies = request.headers.get("cookie") || "";
    const { data } = await backendFetch<{ is_bookmarked: boolean; bookmark_id: string | null }>(
      `/bookmarks/check/${questionId}`,
      { method: "GET", cookies },
    );
    return NextResponse.json(data, { status: 200 });
  } catch (e: unknown) {
    const err = e as { status?: number; error?: { code: string; message: string } };
    return NextResponse.json(
      { error: err.error ?? { code: "INTERNAL_ERROR", message: "Failed to check bookmark" } },
      { status: err.status ?? 500 },
    );
  }
}
