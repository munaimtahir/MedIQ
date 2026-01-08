/**
 * BFF route for admin dashboard summary.
 * Proxies to backend dashboard summary endpoint.
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

    const { data } = await backendFetch<{
      syllabus: { years: number; blocks: number; themes: number };
      content: { published: number | null; in_review: number | null; draft: number | null };
      imports: { last_import_at: string | null; failed_rows: number | null };
    }>("/admin/dashboard/summary", {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch dashboard summary" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
