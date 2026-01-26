/**
 * BFF route for bookmarks list and create.
 * Proxies to backend GET/POST /bookmarks with auth.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = request.nextUrl;
    const qs = searchParams.toString();
    const path = qs ? `/bookmarks?${qs}` : "/bookmarks";
    const { data } = await backendFetch<unknown[]>(path, { method: "GET", cookies });
    return NextResponse.json(data, { status: 200 });
  } catch (e: unknown) {
    const err = e as { status?: number; error?: { code: string; message: string } };
    const status = err.status ?? 500;
    const body = err.error ?? { code: "INTERNAL_ERROR", message: "Failed to load bookmarks" };
    return NextResponse.json({ error: body }, { status });
  }
}

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const payload = (await request.json()) as { question_id: string; notes?: string | null };
    const { data, status } = await backendFetch<unknown>("/bookmarks", {
      method: "POST",
      cookies,
      body: payload,
    });
    return NextResponse.json(data, { status: status ?? 201 });
  } catch (e: unknown) {
    const err = e as { status?: number; error?: { code: string; message: string } };
    const status = err.status ?? 500;
    const body = err.error ?? { code: "INTERNAL_ERROR", message: "Failed to create bookmark" };
    return NextResponse.json({ error: body }, { status });
  }
}
