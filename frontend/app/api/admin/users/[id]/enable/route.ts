/**
 * BFF route for enabling a user.
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
      id: string;
      name: string;
      email: string;
      role: string;
      is_active: boolean;
      created_at: string;
      last_login_at: string | null;
    }>(`/admin/users/${params.id}/enable`, {
      method: "POST",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to enable user" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
