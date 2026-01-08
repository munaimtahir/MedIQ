/**
 * BFF route for marking all notifications as read.
 * Proxies to backend or returns 501 if not implemented.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function POST(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    try {
      const { data } = await backendFetch<{ updated: number }>("/notifications/me/mark-all-read", {
        method: "POST",
        cookies,
      });

      return NextResponse.json(data, { status: 200 });
    } catch (backendError) {
      // Backend not implemented
      const err = backendError as { status?: number };
      if (err.status === 404 || err.status === 501) {
        return NextResponse.json(
          { error: { message: "Coming soon" } },
          { status: 501 }
        );
      }

      // Other errors
      return NextResponse.json(
        { error: { message: "Failed to mark all as read" } },
        { status: 500 }
      );
    }
  } catch (error: unknown) {
    console.error("Error in mark-all-read BFF:", error);
    return NextResponse.json(
      { error: { message: "Failed to mark all as read" } },
      { status: 500 }
    );
  }
}
