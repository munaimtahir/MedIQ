"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { NotificationItem } from "@/lib/notifications/types";
import { isUnread, formatRelativeTime, truncate, getTypeBadgeVariant } from "@/lib/notifications/utils";
import { ChevronDown, ChevronUp } from "lucide-react";

interface NotificationCardProps {
  notification: NotificationItem;
}

export function NotificationCard({ notification }: NotificationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const unread = isUnread(notification);

  const typeLabels = {
    announcement: "Announcement",
    system: "System",
    reminder: "Reminder",
  };

  return (
    <Card
      className={`transition-shadow hover:shadow-md cursor-pointer ${
        unread ? "border-l-4 border-l-primary" : ""
      }`}
      onClick={() => setIsExpanded(!isExpanded)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant={getTypeBadgeVariant(notification.type)} className="text-xs">
                {typeLabels[notification.type]}
              </Badge>
              {unread && (
                <span className="h-2 w-2 rounded-full bg-primary" aria-label="Unread" />
              )}
            </div>
            <h3 className={`text-base font-medium ${unread ? "font-semibold" : ""}`}>
              {notification.title}
            </h3>
            {!isExpanded && (
              <p className="text-sm text-muted-foreground line-clamp-2">
                {truncate(notification.body, 150)}
              </p>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {formatRelativeTime(notification.created_at)}
            </span>
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </div>
      </CardHeader>
      {isExpanded && (
        <CardContent className="pt-0">
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">
            {notification.body}
          </p>
        </CardContent>
      )}
    </Card>
  );
}
