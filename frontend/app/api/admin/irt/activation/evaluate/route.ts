/**
 * BFF route for IRT activation evaluation.
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    const { data } = await backendFetch<{
      decision: {
        eligible: boolean;
        policy_version: string;
        evaluated_at: string;
        recommended_scope: string;
        recommended_model: string;
      };
      eligible: boolean;
      gates: Array<{
        name: string;
        passed: boolean;
        value: number | null;
        threshold: number | null;
        notes: string;
      }>;
    }>("/admin/irt/activation/evaluate", {
      method: "POST",
      cookies,
      body,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to evaluate activation" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
