/**
 * BFF route for fetching themes.
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const blockId = searchParams.get("block_id");
    
    // Validate block_id - must be a valid positive integer
    if (!blockId || blockId === "undefined" || blockId === "null" || blockId === "") {
      return NextResponse.json(
        { error: { code: "INVALID_REQUEST", message: "block_id parameter is required" } },
        { status: 400 }
      );
    }

    // Try to parse as number
    const blockIdNum = Number(blockId);
    if (isNaN(blockIdNum) || !Number.isInteger(blockIdNum) || blockIdNum <= 0) {
      return NextResponse.json(
        { error: { code: "INVALID_REQUEST", message: `block_id must be a positive integer, got: ${blockId}` } },
        { status: 400 }
      );
    }
    
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const path = `/syllabus/themes?block_id=${blockIdNum}`;
    const { data, status, headers } = await backendFetch<unknown[]>(path, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data, {
      status,
      headers: {
        "X-Request-ID": headers.get("X-Request-ID") || "",
      },
    });
  } catch (error: unknown) {
    // Handle different error types
    if (error && typeof error === "object" && "status" in error && "error" in error) {
      const err = error as { status?: number; error?: { code: string; message: string; details?: unknown }; request_id?: string };
      const statusCode = err.status || 500;
      const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch themes" };
      
      return NextResponse.json(
        {
          error: {
            code: errorData.code,
            message: errorData.message,
            request_id: err.request_id || errorData.request_id,
          },
        },
        {
          status: statusCode,
          headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
        }
      );
    }

    // Handle unexpected errors
    console.error("[Themes Route] Unexpected error:", error);
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: error instanceof Error ? error.message : "Failed to fetch themes" } },
      { status: 500 }
    );
  }
}
