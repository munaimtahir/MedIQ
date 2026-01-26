/**
 * BFF route for listing mock instances.
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
    
    const blueprint_id = searchParams.get("blueprint_id");
    const limit = searchParams.get("limit"); // legacy
    const page = searchParams.get("page");
    const page_size = searchParams.get("page_size");
    
    if (blueprint_id) params.set("blueprint_id", blueprint_id);
    if (page) params.set("page", page);
    if (page_size) params.set("page_size", page_size);
    if (limit && !page_size) params.set("page_size", limit);

    const queryString = params.toString() ? `?${params.toString()}` : "";

    const { data } = await backendFetch<unknown>(
      `/admin/mocks/instances${queryString}`,
      {
        method: "GET",
        cookies: cookieHeader,
      },
    );

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch instances:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch instances" };
    return NextResponse.json({ error: errorData }, { status });
  }
}
