/**
 * Notification utility functions.
 */

import { NotificationItem } from "./types";

/**
 * Check if a notification is unread.
 */
export function isUnread(notification: NotificationItem): boolean {
  return !notification.read_at;
}

/**
 * Format ISO timestamp to relative time string.
 * Simple implementation without heavy dependencies.
 */
export function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return "Just now";
  } else if (diffMinutes < 60) {
    return `${diffMinutes} ${diffMinutes === 1 ? "minute" : "minutes"} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} ${diffHours === 1 ? "hour" : "hours"} ago`;
  } else if (diffDays < 7) {
    return `${diffDays} ${diffDays === 1 ? "day" : "days"} ago`;
  } else {
    // For older dates, show formatted date
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
    });
  }
}

/**
 * Truncate text to a maximum number of characters.
 */
export function truncate(text: string, maxChars: number): string {
  if (text.length <= maxChars) {
    return text;
  }
  return text.slice(0, maxChars - 3) + "...";
}

/**
 * Get badge variant for notification type.
 */
export function getTypeBadgeVariant(
  type: NotificationType
): "default" | "secondary" | "outline" {
  switch (type) {
    case "announcement":
      return "default";
    case "system":
      return "secondary";
    case "reminder":
      return "outline";
    default:
      return "secondary";
  }
}
