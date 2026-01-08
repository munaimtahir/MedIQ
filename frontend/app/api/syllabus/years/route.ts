import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
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
  } catch (error: any) {
    const status = error.status || 500;
    const backendError = error.error || {
      code: "INTERNAL_ERROR",
      message: "An error occurred",
    };

    return NextResponse.json(
      {
        error: {
          code: backendError.code,
          message: backendError.message,
          request_id: error.request_id || backendError.request_id,
        },
      },
      {
        status,
        headers: error.request_id ? { "X-Request-ID": error.request_id } : undefined,
      },
    );
  }
}
