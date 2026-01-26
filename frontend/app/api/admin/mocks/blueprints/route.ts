/**
 * BFF route for admin mocks blueprints (list and create).
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const { searchParams } = new URL(request.url);
    const params = new URLSearchParams();
    
    const year = searchParams.get("year");
    const status = searchParams.get("status");
    const page = searchParams.get("page");
    const page_size = searchParams.get("page_size");
    
    if (year) params.set("year", year);
    if (status) params.set("status", status);
    if (page) params.set("page", page);
    if (page_size) params.set("page_size", page_size);

    const queryString = params.toString() ? `?${params.toString()}` : "";

    const { data } = await backendFetch<unknown>(
      `/admin/mocks/blueprints${queryString}`,
      {
        method: "GET",
        cookies: cookieHeader,
      },
    );

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch blueprints:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch blueprints" };
    return NextResponse.json({ error: errorData }, { status });
  }
}

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const body = await request.json();

    const { data } = await backendFetch<unknown>(
      "/admin/mocks/blueprints",
      {
        method: "POST",
        cookies: cookieHeader,
        body,
      },
    );

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    console.error("Failed to create blueprint:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to create blueprint" };
    return NextResponse.json({ error: errorData }, { status });
  }
}
