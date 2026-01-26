/**
 * BFF route for CSV import (multipart file upload).
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";

export async function POST(request: NextRequest, { params }: { params: Promise<{ type: string }> }) {
  try {
    const { type } = await params;
    const cookies = request.headers.get("cookie") || "";
    const { searchParams } = new URL(request.url);
    const dryRun = searchParams.get("dry_run") === "true";
    const autoCreate = searchParams.get("auto_create") === "true";

    // Parse multipart form data
    const formData = await request.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "No file provided" } },
        { status: 400 },
      );
    }

    // Forward to backend as multipart
    const backendFormData = new FormData();
    backendFormData.append("file", file);

    const queryParams = new URLSearchParams();
    queryParams.set("dry_run", dryRun.toString());
    if (autoCreate) {
      queryParams.set("auto_create", "true");
    }

    const url = `${BACKEND_URL}/v1/admin/syllabus/import/${type}?${queryParams.toString()}`;

    // Extract access token from cookies for Authorization header
    const accessTokenMatch = cookies.match(/access_token=([^;]+)/);
    const headers: HeadersInit = {};
    if (accessTokenMatch) {
      headers["Authorization"] = `Bearer ${accessTokenMatch[1]}`;
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: backendFormData,
    });

    const responseData = await response.json().catch(() => ({}));

    if (!response.ok) {
      const error = responseData.error || {
        code: "HTTP_ERROR",
        message: response.statusText,
      };
      return NextResponse.json({ error }, { status: response.status });
    }

    return NextResponse.json(responseData, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to import CSV" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
