/**
 * BFF route for getting themes for a block.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    
    // Validate block ID - must be a valid positive integer
    // Check for undefined, null, empty, or invalid values
    if (!id || id === "undefined" || id === "null" || id === "" || id.trim() === "") {
      return NextResponse.json(
        { error: { code: "INVALID_REQUEST", message: "Block ID is required" } },
        { status: 400 }
      );
    }

    // Try to parse as number
    const blockIdNum = Number(id);
    if (isNaN(blockIdNum) || !Number.isInteger(blockIdNum) || blockIdNum <= 0) {
      return NextResponse.json(
        { error: { code: "INVALID_REQUEST", message: `Block ID must be a positive integer, got: ${id}` } },
        { status: 400 }
      );
    }

    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const { data } = await backendFetch<unknown>(`/admin/syllabus/blocks/${blockIdNum}/themes`, {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    // Handle different error types
    if (error && typeof error === "object" && "status" in error && "error" in error) {
      const err = error as { status?: number; error?: { code: string; message: string; details?: unknown }; request_id?: string };
      const status = err.status || 500;
      const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch themes" };
      
      // Extract validation error details if present
      if (status === 422 && err.error?.details) {
        errorData.message = err.error.message || "Invalid request data";
        errorData.details = err.error.details;
      }

      return NextResponse.json(
        { error: errorData },
        {
          status,
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
