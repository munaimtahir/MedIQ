import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id: themeId } = await params;
    const cookie = req.headers.get("cookie") || "";

    const res = await fetch(`${BACKEND_URL}/v1/analytics/theme/${themeId}`, {
      method: "GET",
      headers: {
        Cookie: cookie,
        "Content-Type": "application/json",
      },
    });

    if (!res.ok) {
      const errorText = await res.text();
      return NextResponse.json(
        { error: errorText || "Failed to fetch theme analytics" },
        { status: res.status },
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching theme analytics:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
