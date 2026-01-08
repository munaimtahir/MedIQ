/**
 * Notification types and interfaces.
 */

export type NotificationType = "announcement" | "system" | "reminder";

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  created_at: string; // ISO timestamp
  read_at?: string | null; // ISO timestamp or null
}

export interface NotificationsResponse {
  items: NotificationItem[];
}

export interface MarkAllReadResponse {
  updated: number;
}
