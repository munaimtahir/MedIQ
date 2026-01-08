/**
 * BFF route for fetching notifications.
 * Proxies to backend or returns mock data in dev mode.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";
import { mockNotifications } from "@/lib/notifications/mock";

const USE_MOCK = process.env.NEXT_PUBLIC_NOTIFICATIONS_MOCK === "1";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    try {
      // Try to fetch from backend
      const { data } = await backendFetch<{ items: unknown[] }>("/notifications/me", {
        method: "GET",
        cookies,
      });

      return NextResponse.json({ items: data.items || [] }, { status: 200 });
    } catch (backendError) {
      // Backend unavailable
      if (USE_MOCK) {
        // In dev mode, return mock data
        console.warn("Backend notifications unavailable, using mock data");
        return NextResponse.json({ items: mockNotifications }, { status: 200 });
      } else {
        // In production, return empty list (not an error)
        return NextResponse.json({ items: [] }, { status: 200 });
      }
    }
  } catch (error: unknown) {
    console.error("Error in notifications BFF:", error);
    // Always return empty list on error to keep UX calm
    return NextResponse.json({ items: [] }, { status: 200 });
  }
}
