/**
 * BFF route for downloading CSV templates.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(
  request: NextRequest,
  { params }: { params: { type: string } }
) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{ content: string; filename: string; content_type: string }>(
      `/admin/syllabus/import/templates/${params.type}`,
      {
        method: "GET",
        cookies,
      }
    );

    // Return CSV content
    return new NextResponse(data.content, {
      status: 200,
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": `attachment; filename="${data.filename}"`,
      },
    });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to download template" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
