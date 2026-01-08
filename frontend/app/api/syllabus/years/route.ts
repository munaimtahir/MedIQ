import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET() {
  try {
    const cookieStore = await cookies();
    
    // Build cookie string for forwarding
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");
    
    const { data, headers } = await backendFetch<unknown[]>("/syllabus/years", {
      method: "GET",
      cookies: cookieHeader,
    });

    return NextResponse.json(data, {
      status: 200,
      headers: {
        "X-Request-ID": headers.get("X-Request-ID") || "",
      },
    });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string; request_id?: string }; request_id?: string };
    const status = err.status || 500;
    const backendError = err.error || {
      code: "INTERNAL_ERROR",
      message: "An error occurred",
    };

    return NextResponse.json(
      {
        error: {
          code: backendError.code,
          message: backendError.message,
          request_id: err.request_id || backendError.request_id,
        },
      },
      {
        status,
        headers: err.request_id ? { "X-Request-ID": err.request_id } : undefined,
      },
    );
  }
}
