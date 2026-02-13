/**
 * BFF route for admin mocks blueprint (get, update).
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params;
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const { data } = await backendFetch<unknown>(
      `/admin/mocks/blueprints/${id}`,
      {
        method: "GET",
        cookies: cookieHeader,
      },
    );

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch blueprint:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch blueprint" };
    return NextResponse.json({ error: errorData }, { status });
  }
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params;
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const body = await request.json();

    const { data } = await backendFetch<unknown>(
      `/admin/mocks/blueprints/${id}`,
      {
        method: "PUT",
        cookies: cookieHeader,
        body,
      },
    );

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to update blueprint:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to update blueprint" };
    return NextResponse.json({ error: errorData }, { status });
  }
}
