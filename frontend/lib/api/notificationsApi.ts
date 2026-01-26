/**
 * Notifications API client
 * Uses BFF /api/v1 routes so auth cookies are sent (same-origin).
 */

import fetcher from "../fetcher";

const API_BASE = "/api/v1";

export const notificationsApi = {
  listNotifications,
  unreadCount,
  markRead,
  markAllRead,
};

export interface NotificationItem {
  id: string;
  type: string; // SYSTEM|SECURITY|COURSE|REMINDER|ANNOUNCEMENT
  title: string;
  body: string;
  action_url: string | null;
  severity: string; // info|warning|critical
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface NotificationsListResponse {
  items: NotificationItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface MarkReadResponse {
  id: string;
  is_read: boolean;
}

export interface MarkAllReadResponse {
  updated: number;
}

/**
 * List notifications with pagination
 */
export async function listNotifications(params: {
  unread_only?: boolean;
  page?: number;
  page_size?: number;
}): Promise<NotificationsListResponse> {
  const searchParams = new URLSearchParams();
  if (params.unread_only !== undefined) {
    searchParams.append("unread_only", String(params.unread_only));
  }
  if (params.page !== undefined) {
    searchParams.append("page", String(params.page));
  }
  if (params.page_size !== undefined) {
    searchParams.append("page_size", String(params.page_size));
  }

  return fetcher<NotificationsListResponse>(`${API_BASE}/notifications?${searchParams.toString()}`, {
    method: "GET",
  });
}

/**
 * Get unread notification count
 */
export async function unreadCount(): Promise<UnreadCountResponse> {
  return fetcher<UnreadCountResponse>(`${API_BASE}/notifications/unread-count`, {
    method: "GET",
  });
}

/**
 * Mark a notification as read
 */
export async function markRead(notificationId: string): Promise<MarkReadResponse> {
  return fetcher<MarkReadResponse>(`${API_BASE}/notifications/${notificationId}/read`, {
    method: "POST",
  });
}

/**
 * Mark all notifications as read
 */
export async function markAllRead(): Promise<MarkAllReadResponse> {
  return fetcher<MarkAllReadResponse>(`${API_BASE}/notifications/read-all`, {
    method: "POST",
  });
}
