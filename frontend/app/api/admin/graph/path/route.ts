/**
 * BFF route for admin graph path query.
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
    const from = searchParams.get("from");
    const to = searchParams.get("to");
    const max_paths = searchParams.get("max_paths") || "3";
    const max_depth = searchParams.get("max_depth") || "8";

    if (!from || !to) {
      return NextResponse.json(
        { error: { code: "BAD_REQUEST", message: "from and to are required" } },
        { status: 400 }
      );
    }

    const params = new URLSearchParams();
    params.set("from", from);
    params.set("to", to);
    params.set("max_paths", max_paths);
    params.set("max_depth", max_depth);
    const queryString = `?${params.toString()}`;

    const { data } = await backendFetch<unknown>(`/admin/graph/path${queryString}`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch graph path:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData =
      err.error || ({ code: "INTERNAL_ERROR", message: "Failed to fetch graph path" } as const);
    return NextResponse.json({ error: errorData }, { status });
  }
}
