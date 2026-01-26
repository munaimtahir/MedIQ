/**
 * BFF route for graph revision health.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      neo4j_available: boolean;
      graph_stats: {
        available: boolean;
        node_count: number;
        edge_count: number;
        error?: string;
      };
      cycle_check: {
        has_cycles: boolean;
        cycles: unknown[];
        cycle_count: number;
        error?: string;
      };
      last_sync: {
        id: string | null;
        status: string | null;
        finished_at: string | null;
        details: Record<string, unknown> | null;
      } | null;
    }>("/admin/graph-revision/health", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch graph health" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
