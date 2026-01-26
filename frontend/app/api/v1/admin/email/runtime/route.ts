/**
 * BFF route for email runtime configuration.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      requested_mode: string;
      effective_mode: string;
      freeze: boolean;
      provider: { type: string; configured: boolean };
      warnings: string[];
      blocking_reasons: string[];
    }>("/admin/email/runtime", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch email runtime config" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
