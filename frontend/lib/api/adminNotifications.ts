/**
 * Admin notifications API client
 */

import fetcher from "../fetcher";

const API_BASE = "/api/v1";

export interface BroadcastTarget {
  mode: "user_ids" | "year" | "block" | "cohort";
  user_ids?: string[];
  year?: number | null;
  block_ids?: number[];
  cohort_id?: string | null;
}

export interface NotificationData {
  type: "ANNOUNCEMENT" | "SYSTEM" | "SECURITY" | "COURSE" | "REMINDER";
  title: string;
  body: string;
  action_url?: string | null;
  severity: "info" | "warning" | "critical";
}

export interface BroadcastRequest {
  target: BroadcastTarget;
  notification: NotificationData;
  reason: string;
  confirmation_phrase: string;
}

export interface BroadcastResponse {
  created: number;
  target_summary: {
    resolved_users: number;
    mode: string;
    year?: number;
    blocks?: number[];
    cohort_id?: string;
  };
}

export interface BroadcastSummaryItem {
  id: string;
  title: string;
  type: string;
  severity: string;
  created_at: string;
  created_by: string | null;
  target_summary: {
    mode: string;
    user_count: number;
    year?: number;
    block_ids?: number[];
  };
}

export interface RecentBroadcastsResponse {
  items: BroadcastSummaryItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface BroadcastDetailItem {
  id: string;
  title: string;
  type: string;
  severity: string;
  body: string;
  action_url: string | null;
  created_at: string;
  created_by: string | null;
  target_summary: {
    mode: string;
    user_count: number;
    year?: number;
    block_ids?: number[];
    cohort_id?: string;
  };
  audit_metadata: {
    before: Record<string, unknown> | null;
    after: Record<string, unknown> | null;
    meta: Record<string, unknown> | null;
    reason?: string;
  };
}

export const adminNotificationsApi = {
  /**
   * Broadcast notification to multiple users
   */
  async broadcastNotification(payload: BroadcastRequest): Promise<BroadcastResponse> {
    return fetcher<BroadcastResponse>(`${API_BASE}/admin/notifications/broadcast`, {
      method: "POST",
      body: payload,
    });
  },

  /**
   * List recent notification broadcasts
   */
  async listRecentBroadcasts(params: {
    page?: number;
    page_size?: number;
  }): Promise<RecentBroadcastsResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.append("page", String(params.page));
    if (params.page_size) searchParams.append("page_size", String(params.page_size));

    const query = searchParams.toString();
    return fetcher<RecentBroadcastsResponse>(
      `${API_BASE}/admin/notifications/recent${query ? `?${query}` : ""}`,
      {
        method: "GET",
      },
    );
  },

  /**
   * Get full details of a specific broadcast
   */
  async getBroadcastDetail(broadcastId: string): Promise<BroadcastDetailItem> {
    return fetcher<BroadcastDetailItem>(
      `${API_BASE}/admin/notifications/recent/${broadcastId}`,
      {
        method: "GET",
      },
    );
  },
};
