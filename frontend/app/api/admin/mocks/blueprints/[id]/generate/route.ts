/**
 * BFF route for generating a mock instance.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    const body = await request.json();

    const { data } = await backendFetch<unknown>(
      `/admin/mocks/blueprints/${params.id}/generate`,
      {
        method: "POST",
        cookies: cookieHeader,
        body,
      },
    );

    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to generate mock:", error);
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to generate mock" };
    return NextResponse.json({ error: errorData }, { status });
  }
}
