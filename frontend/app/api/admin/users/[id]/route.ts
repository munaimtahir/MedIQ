/**
 * BFF route for admin user update.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    const { data } = await backendFetch<{
      id: string;
      name: string;
      email: string;
      role: string;
      is_active: boolean;
      created_at: string;
      last_login_at: string | null;
    }>(`/admin/users/${id}`, {
      method: "PUT",
      cookies,
      body,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to update user" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
