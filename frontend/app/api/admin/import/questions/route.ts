/**
 * BFF route for importing questions.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    // Get form data (file + options)
    const formData = await request.formData();

    // Forward to backend
    const response = await fetch(`${process.env.BACKEND_URL}/v1/admin/import/questions`, {
      method: "POST",
      headers: {
        Cookie: cookieHeader,
      },
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        {
          error: data.detail ||
            data.error || { code: "IMPORT_FAILED", message: "Failed to import questions" },
        },
        { status: response.status },
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    console.error("[Import Questions Route] Unexpected error:", error);
    return NextResponse.json(
      {
        error: {
          code: "INTERNAL_ERROR",
          message: error instanceof Error ? error.message : "Failed to import questions",
        },
      },
      { status: 500 },
    );
  }
}
