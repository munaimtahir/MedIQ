"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useNotifications } from "@/lib/notifications/hooks";
import { NotificationsList } from "@/components/student/notifications/NotificationsList";
import { NotificationsSkeleton } from "@/components/student/notifications/NotificationsSkeleton";
import { NotificationsEmpty } from "@/components/student/notifications/NotificationsEmpty";
import { NotificationsError } from "@/components/student/notifications/NotificationsError";
import { isUnread } from "@/lib/notifications/utils";
import { CheckCheck } from "lucide-react";

export default function NotificationsPage() {
  const {
    items,
    loading,
    error,
    refetch,
    markAllRead,
    markAllReadSupported,
  } = useNotifications();

  const unreadCount = items.filter((item) => isUnread(item)).length;
  const hasUnread = unreadCount > 0;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Notifications</h1>
          <p className="text-muted-foreground">
            Important updates, announcements, and reminders
          </p>
        </div>
        <Button
          variant="outline"
          disabled={loading || !hasUnread || !markAllReadSupported}
          onClick={markAllRead}
          title={
            !markAllReadSupported
              ? "Coming soon"
              : !hasUnread
              ? "No unread notifications"
              : undefined
          }
        >
          <CheckCheck className="mr-2 h-4 w-4" />
          Mark all as read
        </Button>
      </div>

      {/* Body */}
      {loading ? (
        <NotificationsSkeleton />
      ) : error ? (
        <NotificationsError error={error} onRetry={refetch} />
      ) : items.length === 0 ? (
        <NotificationsEmpty />
      ) : (
        <NotificationsList items={items} />
      )}

      {/* Footer hint */}
      <Card className="bg-muted/50">
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground text-center">
            In the future, practice reminders and syllabus updates will appear here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
