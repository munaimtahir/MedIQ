/**
 * BFF route for admin graph neighbors query.
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
    const depth = searchParams.get("depth") || "1";

    if (!concept_id) {
      return NextResponse.json(
        { error: { code: "BAD_REQUEST", message: "concept_id is required" } },
        { status: 400 }
      );
    }

    const params = new URLSearchParams();
    params.set("concept_id", concept_id);
    params.set("depth", depth);
    const queryString = `?${params.toString()}`;

    const { data } = await backendFetch<unknown>(`/admin/graph/neighbors${queryString}`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch graph neighbors:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData =
      err.error || ({ code: "INTERNAL_ERROR", message: "Failed to fetch graph neighbors" } as const);
    return NextResponse.json({ error: errorData }, { status });
  }
}
