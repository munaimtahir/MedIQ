/**
 * BFF route for admin question by ID (get and update).
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { id } = await params;

    const { data } = await backendFetch<unknown>(`/admin/questions/${id}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch question" };

    return NextResponse.json({ error: errorData }, { status });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { id } = await params;
    const body = await request.json();

    const { data } = await backendFetch<unknown>(`/admin/questions/${id}`, {
      method: "PUT",
      cookies,
      body,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to update question" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
