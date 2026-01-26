/**
 * BFF route for admin slow requests.
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
    const limit = searchParams.get("limit") || "50";

    const params = new URLSearchParams();
    params.set("limit", limit);
    const queryString = `?${params.toString()}`;

    const { data } = await backendFetch<unknown>(`/admin/perf/slow${queryString}`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch perf slow requests:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData =
      err.error || ({ code: "INTERNAL_ERROR", message: "Failed to fetch perf slow requests" } as const);
    return NextResponse.json({ error: errorData }, { status });
  }
}

