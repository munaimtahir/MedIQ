/**
 * BFF route for admin graph prerequisites query.
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
    const concept_id = searchParams.get("concept_id");
    const max_depth = searchParams.get("max_depth") || "5";
    const include_edges = searchParams.get("include_edges") || "true";

    if (!concept_id) {
      return NextResponse.json(
        { error: { code: "BAD_REQUEST", message: "concept_id is required" } },
        { status: 400 }
      );
    }

    const params = new URLSearchParams();
    params.set("concept_id", concept_id);
    params.set("max_depth", max_depth);
    params.set("include_edges", include_edges);
    const queryString = `?${params.toString()}`;

    const { data } = await backendFetch<unknown>(`/admin/graph/prerequisites${queryString}`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch graph prerequisites:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData =
      err.error ||
      ({ code: "INTERNAL_ERROR", message: "Failed to fetch graph prerequisites" } as const);
    return NextResponse.json({ error: errorData }, { status });
  }
}
