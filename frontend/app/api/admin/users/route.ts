/**
 * BFF route for admin users (list and create).
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);

    const params = new URLSearchParams();
    const q = searchParams.get("q");
    const role = searchParams.get("role");
    const status = searchParams.get("status");
    const page = searchParams.get("page");
    const page_size = searchParams.get("page_size");

    if (q) params.set("q", q);
    if (role) params.set("role", role);
    if (status) params.set("status", status);
    if (page) params.set("page", page);
    if (page_size) params.set("page_size", page_size);

    const queryString = params.toString() ? `?${params.toString()}` : "";

    const { data } = await backendFetch<{
      items: Array<{
        id: string;
        name: string;
        email: string;
        role: string;
        is_active: boolean;
        created_at: string;
        last_login_at: string | null;
      }>;
      page: number;
      page_size: number;
      total: number;
    }>(`/admin/users${queryString}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch users" };

    return NextResponse.json({ error: errorData }, { status });
  }
}

export async function POST(request: NextRequest) {
  try {
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
    }>("/admin/users", {
      method: "POST",
      cookies,
      body,
    });

    return NextResponse.json(data, { status: 201 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to create user" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
