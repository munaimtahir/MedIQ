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

    // Build query params for CMS endpoints (supports all filter params)
    const params = new URLSearchParams();

    // CMS filters
    const status = searchParams.get("status");
    const year_id = searchParams.get("year_id");
    const block_id = searchParams.get("block_id");
    const theme_id = searchParams.get("theme_id");
    const difficulty = searchParams.get("difficulty");
    const cognitive_level = searchParams.get("cognitive_level");
    const source_book = searchParams.get("source_book");
    const q = searchParams.get("q");
    const page = searchParams.get("page");
    const page_size = searchParams.get("page_size");
    const sort = searchParams.get("sort");
    const order = searchParams.get("order");

    if (status) params.set("status", status);
    if (year_id) params.set("year_id", year_id);
    if (block_id) params.set("block_id", block_id);
    if (theme_id) params.set("theme_id", theme_id);
    if (difficulty) params.set("difficulty", difficulty);
    if (cognitive_level) params.set("cognitive_level", cognitive_level);
    if (source_book) params.set("source_book", source_book);
    if (q) params.set("q", q);
    if (page) params.set("page", page);
    if (page_size) params.set("page_size", page_size);
    if (sort) params.set("sort", sort);
    if (order) params.set("order", order);

    const queryString = params.toString() ? `?${params.toString()}` : "";

    const { data } = await backendFetch<unknown>(`/admin/questions${queryString}`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    // Handle different error types
    if (error && typeof error === "object" && "status" in error && "error" in error) {
      const err = error as {
        status?: number;
        error?: { code: string; message: string; details?: unknown };
        request_id?: string;
      };
      const status = err.status || 500;
      const errorData = err.error || {
        code: "INTERNAL_ERROR",
        message: "Failed to fetch questions",
      };

      return NextResponse.json(
        { error: errorData },
        {
          status,
          headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
        },
      );
    }

    // Handle unexpected errors
    console.error("[Questions Route] Unexpected error:", error);
    return NextResponse.json(
      {
        error: {
          code: "INTERNAL_ERROR",
          message: error instanceof Error ? error.message : "Failed to fetch questions",
        },
      },
      { status: 500 },
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
      const err = error as {
        status?: number;
        error?: { code: string; message: string; details?: unknown };
        request_id?: string;
      };
      const status = err.status || 500;
      const errorData = err.error || {
        code: "INTERNAL_ERROR",
        message: "Failed to create question",
      };

      return NextResponse.json(
        { error: errorData },
        {
          status,
          headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
        },
      );
    }

    // Handle unexpected errors
    console.error("[Questions Route] Unexpected error:", error);
    return NextResponse.json(
      {
        error: {
          code: "INTERNAL_ERROR",
          message: error instanceof Error ? error.message : "Failed to create question",
        },
      },
      { status: 500 },
    );
  }
}
