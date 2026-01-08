/**
 * BFF route for admin syllabus blocks (create).
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

    const { data } = await backendFetch<unknown>("/admin/syllabus/blocks", {
      method: "POST",
      cookies: cookieHeader,
      body,
    });

    return NextResponse.json(data, { status: 201 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string; details?: unknown } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to create block" };
    
    // Extract validation error details if present
    if (status === 422 && err.error?.details) {
      errorData.message = err.error.message || "Invalid request data";
      errorData.details = err.error.details;
    }

    return NextResponse.json({ error: errorData }, { status });
  }
}
