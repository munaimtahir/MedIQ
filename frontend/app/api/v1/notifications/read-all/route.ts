/**
 * BFF route for marking all notifications as read.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      updated: number;
    }>("/notifications/read-all", {
      method: "POST",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to mark all as read" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
