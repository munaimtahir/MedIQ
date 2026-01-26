/**
 * BFF route for admin perf summary.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const { searchParams } = new URL(request.url);
    const window = searchParams.get("window") || "24h";

    const params = new URLSearchParams();
    params.set("window", window);
    const queryString = `?${params.toString()}`;

    const { data } = await backendFetch<unknown>(`/admin/perf/summary${queryString}`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch perf summary:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData =
      err.error || ({ code: "INTERNAL_ERROR", message: "Failed to fetch perf summary" } as const);
    return NextResponse.json({ error: errorData }, { status });
  }
}

