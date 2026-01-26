/**
 * BFF route for email outbox list.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const searchParams = request.nextUrl.searchParams;

    const { data } = await backendFetch<{
      items: unknown[];
      page: number;
      page_size: number;
      total: number;
    }>("/admin/email/outbox", {
      method: "GET",
      cookies,
      queryParams: Object.fromEntries(searchParams.entries()),
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch email outbox" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
