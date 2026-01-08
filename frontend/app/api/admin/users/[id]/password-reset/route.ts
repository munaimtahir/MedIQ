/**
 * BFF route for triggering password reset.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      message: string;
      email_sent: boolean;
    }>(`/admin/users/${params.id}/password-reset`, {
      method: "POST",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to trigger password reset" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
