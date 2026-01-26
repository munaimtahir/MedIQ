"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useNotifications, useMarkRead, useMarkAllRead } from "@/lib/hooks/useNotifications";
import { NotificationItem } from "@/lib/api/notificationsApi";
import { formatDistanceToNow } from "date-fns";
import { CheckCheck, Check, ExternalLink, AlertCircle, Info, AlertTriangle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { Skeleton } from "@/components/ui/skeleton";

const PAGE_SIZE = 25;

function NotificationListItem({ notification }: { notification: NotificationItem }) {
  const router = useRouter();
  const { trigger: markRead, isMutating } = useMarkRead();
  const { toast } = useToast();

  const handleMarkRead = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await markRead(notification.id);
      toast({
        title: "Marked as read",
        description: "Notification marked as read",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to mark notification as read",
        variant: "destructive",
      });
    }
  };

  const handleClick = () => {
    if (notification.action_url) {
      router.push(notification.action_url);
    }
  };

  const getSeverityIcon = () => {
    switch (notification.severity) {
      case "critical":
        return <AlertCircle className="h-4 w-4 text-destructive" />;
      case "warning":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default:
        return <Info className="h-4 w-4 text-blue-500" />;
    }
  };

  const getSeverityBadgeVariant = () => {
    switch (notification.severity) {
      case "critical":
        return "destructive";
      case "warning":
        return "default";
      default:
        return "secondary";
    }
  };

  return (
    <Card
      className={`cursor-pointer transition-colors hover:bg-muted/50 ${
        !notification.is_read ? "border-l-4 border-l-primary bg-muted/30" : ""
      }`}
      onClick={handleClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <h3 className={`font-semibold ${!notification.is_read ? "font-bold" : ""}`}>
                {notification.title}
              </h3>
              {getSeverityIcon()}
              <Badge variant={getSeverityBadgeVariant() as "default" | "secondary" | "destructive"}>
                {notification.severity}
              </Badge>
            </div>
            <p className="line-clamp-2 text-sm text-muted-foreground">{notification.body}</p>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>{formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}</span>
              {notification.action_url && (
                <span className="flex items-center gap-1">
                  <ExternalLink className="h-3 w-3" />
                  Open
                </span>
              )}
            </div>
          </div>
          {!notification.is_read && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleMarkRead}
              disabled={isMutating}
              className="shrink-0"
            >
              <Check className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function NotificationsSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="p-4">
            <Skeleton className="h-6 w-3/4 mb-2" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-2/3" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function NotificationsPage() {
  const [activeTab, setActiveTab] = useState<"all" | "unread">("all");
  const [page, setPage] = useState(1);
  const { toast } = useToast();

  const unreadOnly = activeTab === "unread";
  const { data, error, isLoading } = useNotifications({
    unread_only: unreadOnly,
    page,
    page_size: PAGE_SIZE,
  });

  const { trigger: markAllRead, isMutating: isMarkingAllRead } = useMarkAllRead();

  const handleMarkAllRead = async () => {
    try {
      const result = await markAllRead();
      toast({
        title: "Marked all as read",
        description: `${result.updated || 0} notification(s) marked as read`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to mark all notifications as read",
        variant: "destructive",
      });
    }
  };

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const hasUnread = data?.items.some((item) => !item.is_read) || false;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Notifications</h1>
          <p className="text-muted-foreground">Important updates, announcements, and reminders</p>
        </div>
        {hasUnread && (
          <Button
            variant="outline"
            disabled={isMarkingAllRead}
            onClick={handleMarkAllRead}
            className="gap-2"
          >
            <CheckCheck className="h-4 w-4" />
            Mark all as read
          </Button>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => {
        setActiveTab(v as "all" | "unread");
        setPage(1);
      }}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="unread">Unread</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="space-y-4">
          {isLoading ? (
            <NotificationsSkeleton />
          ) : error ? (
            <Card>
              <CardContent className="p-8 text-center">
                <p className="text-muted-foreground">Failed to load notifications</p>
                <Button
                  variant="outline"
                  onClick={() => window.location.reload()}
                  className="mt-4"
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          ) : !data || data.items.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <p className="text-muted-foreground">
                  {unreadOnly ? "No unread notifications" : "No notifications"}
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="space-y-4">
                {data.items.map((notification) => (
                  <NotificationListItem key={notification.id} notification={notification} />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between">
                  <Button
                    variant="outline"
                    disabled={page === 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
