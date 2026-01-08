/**
 * BFF route for admin settings (get and update).
 * Proxies the request to the backend with proper authentication.
 */
import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backendClient";

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";

    const { data } = await backendFetch<{
      data: {
        general: {
          platform_name: string;
          platform_description: string;
          default_language: string;
          timezone: string;
          default_landing: string;
        };
        academic_defaults: {
          default_year_id: number | null;
          blocks_visibility_mode: string;
        };
        practice_defaults: {
          default_mode: string;
          timer_default: string;
          review_policy: string;
          allow_mixed_blocks: boolean;
          allow_any_block_anytime: boolean;
        };
        security: {
          access_token_minutes: number;
          refresh_token_days: number;
          force_logout_on_password_reset: boolean;
        };
        notifications: {
          password_reset_emails_enabled: boolean;
          practice_reminders_enabled: boolean;
          admin_alerts_enabled: boolean;
          inapp_announcements_enabled: boolean;
        };
        version: number;
      };
      updated_at: string | null;
      updated_by_user_id: number | null;
    }>("/admin/settings", {
      method: "GET",
      cookies,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to fetch settings" };

    return NextResponse.json({ error: errorData }, { status });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const cookies = request.headers.get("cookie") || "";
    const body = await request.json();

    const { data } = await backendFetch<{
      data: {
        general: any;
        academic_defaults: any;
        practice_defaults: any;
        security: any;
        notifications: any;
        version: number;
      };
      updated_at: string | null;
      updated_by_user_id: number | null;
    }>("/admin/settings", {
      method: "PUT",
      cookies,
      body,
    });

    return NextResponse.json(data, { status: 200 });
  } catch (error: unknown) {
    const err = error as { status?: number; error?: { code: string; message: string } };
    const status = err.status || 500;
    const errorData = err.error || { code: "INTERNAL_ERROR", message: "Failed to update settings" };

    return NextResponse.json({ error: errorData }, { status });
  }
}
