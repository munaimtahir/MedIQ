/**
 * BFF route for fetching themes.
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);
    const blockId = searchParams.get("block_id");
    
    const queryString = blockId ? `?block_id=${blockId}` : "";

    const { data } = await backendFetch<
      Array<{
        id: number;
        name: string;
        block_id: string;
      }>
    >(`/themes${queryString}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch themes" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
