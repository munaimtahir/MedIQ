/**
 * BFF route for adaptive next (revision / practice question selection).
 * Proxies to backend POST /learning/adaptive/next with auth.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = (await request.json()) as {
      mode?: string;
      theme_ids?: number[];
      block_ids?: number[];
      count?: number;
    };
    const { data } = await backendFetch<{ question_ids: string[] }>("/learning/adaptive/next", {
      method: "POST",
      cookies,
      body,
    });
    return NextResponse.json(data, { status: 200 });
  } catch (e: unknown) {
    const err = e as { status?: number; error?: { code: string; message: string } };
    const status = err.status ?? 500;
    const body = err.error ?? { code: "INTERNAL_ERROR", message: "Failed to start revision session" };
    return NextResponse.json({ error: body }, { status });
  }
}
