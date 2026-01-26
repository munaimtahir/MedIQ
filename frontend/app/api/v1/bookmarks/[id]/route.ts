/**
 * BFF route for single bookmark get/update/delete.
 * Proxies to backend GET/PATCH/DELETE /bookmarks/:id with auth.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

function getCookies(request: NextRequest) {
  return request.headers.get("cookie") || "";
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const { data } = await backendFetch<unknown>(`/bookmarks/${id}`, {
      method: "GET",
      cookies: getCookies(request),
    });
    return NextResponse.json(data, { status: 200 });
  } catch (e: unknown) {
    const err = e as { status?: number; error?: { code: string; message: string } };
    return NextResponse.json(
      { error: err.error ?? { code: "INTERNAL_ERROR", message: "Failed to load bookmark" } },
      { status: err.status ?? 500 },
    );
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const payload = (await request.json()) as { notes?: string | null };
    const { data } = await backendFetch<unknown>(`/bookmarks/${id}`, {
      method: "PATCH",
      cookies: getCookies(request),
      body: payload,
    });
    return NextResponse.json(data, { status: 200 });
  } catch (e: unknown) {
    const err = e as { status?: number; error?: { code: string; message: string } };
    return NextResponse.json(
      { error: err.error ?? { code: "INTERNAL_ERROR", message: "Failed to update bookmark" } },
      { status: err.status ?? 500 },
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    await backendFetch<unknown>(`/bookmarks/${id}`, {
      method: "DELETE",
      cookies: getCookies(request),
    });
    return new NextResponse(null, { status: 204 });
  } catch (e: unknown) {
    const err = e as { status?: number; error?: { code: string; message: string } };
    return NextResponse.json(
      { error: err.error ?? { code: "INTERNAL_ERROR", message: "Failed to delete bookmark" } },
      { status: err.status ?? 500 },
    );
  }
}
