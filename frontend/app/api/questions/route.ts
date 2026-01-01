/**
 * BFF route for fetching questions (student view).
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);
    
    const params = new URLSearchParams();
    const themeId = searchParams.get("theme_id");
    const blockId = searchParams.get("block_id");
    const limit = searchParams.get("limit");
    
    if (themeId) params.set("theme_id", themeId);
    if (blockId) params.set("block_id", blockId);
    if (limit) params.set("limit", limit);
    
    const queryString = params.toString() ? `?${params.toString()}` : "";

    const { data } = await backendFetch<unknown>(`/questions${queryString}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch questions" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
