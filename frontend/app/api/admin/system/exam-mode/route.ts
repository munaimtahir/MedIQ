/**
 * BFF route for exam mode (get and toggle).
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      enabled: boolean;
      updated_at: string | null;
      updated_by: { id: string; email: string } | null;
      reason: string | null;
      source: string;
    }>("/admin/system/exam-mode", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch exam mode" };

    return NextResponse.json({ error: errorData }, { status });
  }
}

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    const { data } = await backendFetch<{
      enabled: boolean;
      updated_at: string | null;
      updated_by: { id: string; email: string } | null;
      reason: string | null;
      source: string;
    }>("/admin/system/exam-mode", {
      method: "POST",
      cookies,
      body,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to toggle exam mode" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
