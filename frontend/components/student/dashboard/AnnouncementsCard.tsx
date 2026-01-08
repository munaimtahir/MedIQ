"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Announcement } from "@/lib/dashboard/types";
import { Bell } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface AnnouncementsCardProps {
  announcements: Announcement[];
  loading?: boolean;
  error?: Error | null;
}

export function AnnouncementsCard({ announcements, loading, error }: AnnouncementsCardProps) {
  if (loading) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-48 mt-2" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <CardTitle>Announcements</CardTitle>
          <CardDescription>Platform updates and news</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Unable to load announcements.</p>
        </CardContent>
      </Card>
    );
  }

  if (announcements.length === 0) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Announcements
          </CardTitle>
          <CardDescription>Platform updates and news</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No updates at this time.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="col-span-full md:col-span-1">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Announcements
        </CardTitle>
        <CardDescription>Platform updates and news</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {announcements.map((announcement) => (
          <div key={announcement.id} className="rounded-lg border p-3">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="font-medium text-sm">{announcement.title}</p>
                {announcement.body && (
                  <p className="mt-1 text-xs text-muted-foreground">{announcement.body}</p>
                )}
                <p className="mt-1 text-xs text-muted-foreground">
                  {new Date(announcement.date).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
