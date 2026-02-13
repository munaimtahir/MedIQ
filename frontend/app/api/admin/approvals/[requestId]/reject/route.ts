/**
 * BFF route for admin approvals reject.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ requestId: string }> }
) {
  try {
    const { requestId } = await context.params;
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const { data } = await backendFetch<unknown>(
      `/admin/runtime/approvals/${requestId}/reject`,
      {
        method: "POST",
        cookies: cookieHeader,
      }
    );

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to reject request:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData =
      err.error || ({ code: "INTERNAL_ERROR", message: "Failed to reject request" } as const);
    return NextResponse.json({ error: errorData }, { status });
  }
}
