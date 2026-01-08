/**
 * BFF route for admin syllabus themes (create).
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    const { data } = await backendFetch<unknown>("/admin/syllabus/themes", {
      method: "POST",
      cookies,
      body,
    });

    return NextResponse.json(data, { status: 201 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to create theme" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
