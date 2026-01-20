/**
 * BFF route for import jobs list.
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

    const { data } = await backendFetch<unknown>(`/admin/import/jobs?limit=${limit}`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    if (error && typeof error === "object" && "status" in error && "error" in error) {
      const err = error as { status?: number; error?: { code: string; message: string } };
      return NextResponse.json({ error: err.error }, { status: err.status || 500 });
    }

    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Failed to fetch jobs" } },
      { status: 500 },
    );
  }
}
