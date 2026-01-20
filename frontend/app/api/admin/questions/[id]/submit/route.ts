/**
 * BFF route for submitting question for review.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const { data } = await backendFetch<unknown>(`/admin/questions/${id}/submit`, {
      method: "POST",
      cookies: cookieHeader,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    if (error && typeof error === "object" && "status" in error && "error" in error) {
      const err = error as {
        status?: number;
        error?: { code: string; message: string; details?: unknown };
        request_id?: string;
      };
      const status = err.status || 500;
      const errorData = err.error || {
        code: "INTERNAL_ERROR",
        message: "Failed to submit question",
      };

      return NextResponse.json(
        { error: errorData },
        {
          status,
          headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
        },
      );
    }

    console.error("[Submit Question Route] Unexpected error:", error);
    return NextResponse.json(
      {
        error: {
          code: "INTERNAL_ERROR",
          message: error instanceof Error ? error.message : "Failed to submit question",
        },
      },
      { status: 500 },
    );
  }
}
