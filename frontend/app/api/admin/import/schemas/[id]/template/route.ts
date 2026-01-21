/**
 * BFF route for downloading schema template.
 */
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const cookieStore = await cookies();
    const cookieHeader = Array.from(cookieStore.getAll())
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");

    // Fetch template from backend
    const response = await fetch(
      `${process.env.BACKEND_URL}/v1/admin/import/schemas/${id}/template`,
      {
        method: "GET",
        headers: {
          Cookie: cookieHeader,
        },
      },
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: { code: "DOWNLOAD_FAILED", message: "Failed to download template" } },
        { status: response.status },
      );
    }

    const blob = await response.blob();
    const contentDisposition =
      response.headers.get("content-disposition") || `attachment; filename="template.csv"`;

    return new NextResponse(blob, {
      status: 200,
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": contentDisposition,
      },
    });
  } catch {
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Failed to download template" } },
      { status: 500 },
    );
  }
}
