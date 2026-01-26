/**
 * BFF route for user learning preferences.
 * Proxies to backend GET/PATCH /users/me/preferences/learning with auth.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const { data } = await backendFetch<{
      revision_daily_target: number | null;
      spacing_multiplier: number;
      retention_target_override: number | null;
    }>("/users/me/preferences/learning", { method: "GET", cookies });
    return NextResponse.json(data, { status: 200 });
  } catch (e: unknown) {
    const err = e as { status?: number; error?: { code: string; message: string } };
    const status = err.status ?? 500;
    const body = err.error ?? { code: "INTERNAL_ERROR", message: "Failed to load preferences" };
    return NextResponse.json({ error: body }, { status });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const payload = (await request.json()) as {
      revision_daily_target?: number;
      spacing_multiplier?: number;
      retention_target_override?: number;
    };
    const { data } = await backendFetch<{
      revision_daily_target: number | null;
      spacing_multiplier: number;
      retention_target_override: number | null;
    }>("/users/me/preferences/learning", {
      method: "PATCH",
      cookies,
      body: payload,
    });
    return NextResponse.json(data, { status: 200 });
  } catch (e: unknown) {
    const err = e as { status?: number; error?: { code: string; message: string } };
    const status = err.status ?? 500;
    const body = err.error ?? { code: "INTERNAL_ERROR", message: "Failed to save preferences" };
    return NextResponse.json({ error: body }, { status });
  }
}
