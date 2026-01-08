/**
 * BFF route for admin questions (list and create).
 * Proxies the request to the backend with proper authentication.
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
    const skip = searchParams.get("skip");
    const limit = searchParams.get("limit");
    const published = searchParams.get("published");
    
    if (skip) params.set("skip", skip);
    if (limit) params.set("limit", limit);
    if (published) params.set("published", published);
    
    const queryString = params.toString() ? `?${params.toString()}` : "";

    const { data } = await backendFetch<unknown>(`/admin/questions${queryString}`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    // Handle different error types
    if (error && typeof error === "object" && "status" in error && "error" in error) {
      const err = error as { status?: number; error?: { code: string; message: string; details?: unknown }; request_id?: string };
      const status = err.status || 500;
      const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch questions" };
      
      return NextResponse.json(
        { error: errorData },
        {
          status,
          headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
        }
      );
    }

    // Handle unexpected errors
    console.error("[Questions Route] Unexpected error:", error);
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: error instanceof Error ? error.message : "Failed to fetch questions" } },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");
    const body = await request.json();

    const { data } = await backendFetch<unknown>("/admin/questions", {
      method: "POST",
      cookies: cookieHeader,
      body,
    });

    return NextResponse.json(data, { status: 201 });
  } catch (error: unknown) {
    // Handle different error types
    if (error && typeof error === "object" && "status" in error && "error" in error) {
      const err = error as { status?: number; error?: { code: string; message: string; details?: unknown }; request_id?: string };
      const status = err.status || 500;
      const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to create question" };
      
      return NextResponse.json(
        { error: errorData },
        {
          status,
          headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
        }
      );
    }

    // Handle unexpected errors
    console.error("[Questions Route] Unexpected error:", error);
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: error instanceof Error ? error.message : "Failed to create question" } },
      { status: 500 }
    );
  }
}
