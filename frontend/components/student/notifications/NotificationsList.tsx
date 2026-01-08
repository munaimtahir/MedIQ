"use client";

import { NotificationItem } from "@/lib/notifications/types";
import { NotificationCard } from "./NotificationCard";

interface NotificationsListProps {
  items: NotificationItem[];
}

export function NotificationsList({ items }: NotificationsListProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {items.map((notification) => (
        <NotificationCard key={notification.id} notification={notification} />
      ))}
    </div>
  );
}
