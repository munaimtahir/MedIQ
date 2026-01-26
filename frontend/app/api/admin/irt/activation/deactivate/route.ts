/**
 * BFF route for IRT deactivation (kill-switch).
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    const { data } = await backendFetch<{
      message: string;
      state: {
        active: boolean;
        scope: string;
        model: string;
      };
    }>("/admin/irt/activation/deactivate", {
      method: "POST",
      cookies,
      body,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to deactivate IRT" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
