/**
 * BFF route for fetching blocks.
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);
    const year = searchParams.get("year");
    
    const queryString = year ? `?year=${year}` : "";

    const { data } = await backendFetch<
      Array<{
        id: string;
        name: string;
        year: number;
        description?: string;
      }>
    >(`/blocks${queryString}`, {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch blocks" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
