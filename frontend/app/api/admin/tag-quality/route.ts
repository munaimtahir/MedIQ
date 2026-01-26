/**
 * BFF route for admin tag quality debt.
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

    const { data } = await backendFetch<unknown>("/admin/tag-quality", {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch tag quality:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData =
      err.error || ({ code: "INTERNAL_ERROR", message: "Failed to fetch tag quality" } as const);
    return NextResponse.json({ error: errorData }, { status });
  }
}
