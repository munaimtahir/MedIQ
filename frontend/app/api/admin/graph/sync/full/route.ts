/**
 * BFF route for admin graph full rebuild.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const body = await request.json();

    const { data } = await backendFetch<unknown>("/admin/graph/sync/full", {
      method: "POST",
      cookies: cookieHeader,
      body,
    });

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to run full rebuild:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData =
      err.error || ({ code: "INTERNAL_ERROR", message: "Failed to run full rebuild" } as const);
    return NextResponse.json({ error: errorData }, { status });
  }
}
