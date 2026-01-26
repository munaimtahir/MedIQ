/**
 * BFF route for student graph suggestions query.
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
    const target_concept_id = searchParams.get("target_concept_id");
    const limit = searchParams.get("limit") || "10";

    if (!target_concept_id) {
      return NextResponse.json(
        { error: { code: "BAD_REQUEST", message: "target_concept_id is required" } },
        { status: 400 }
      );
    }

    const params = new URLSearchParams();
    params.set("target_concept_id", target_concept_id);
    params.set("limit", limit);
    const queryString = `?${params.toString()}`;

    const { data } = await backendFetch<unknown>(`/student/graph/suggestions${queryString}`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch student graph suggestions:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData =
      err.error ||
      ({ code: "INTERNAL_ERROR", message: "Failed to fetch student graph suggestions" } as const);
    return NextResponse.json({ error: errorData }, { status });
  }
}
