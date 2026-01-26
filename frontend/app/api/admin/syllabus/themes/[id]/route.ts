/**
 * BFF route for admin syllabus theme (update).
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    const { data } = await backendFetch<unknown>(`/admin/syllabus/themes/${id}`, {
      method: "PUT",
      cookies,
      body,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to update theme" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
