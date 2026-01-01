/**
 * BFF route for onboarding options.
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      years: Array<{
        id: number;
        slug: string;
        display_name: string;
        blocks: Array<{ id: number; code: string; display_name: string }>;
        subjects: Array<{ id: number; code: string | null; display_name: string }>;
      }>;
    }>("/onboarding/options", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch options" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
