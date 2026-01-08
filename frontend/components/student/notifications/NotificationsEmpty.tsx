"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Bell } from "lucide-react";
import Link from "next/link";

export function NotificationsEmpty() {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-col items-center justify-center text-center space-y-4 py-8">
          <Bell className="h-12 w-12 text-muted-foreground" />
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">No notifications yet</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              When you have important updates, announcements, or reminders, they'll appear here.
            </p>
          </div>
          <Button variant="outline" asChild>
            <Link href="/student/settings">Go to Settings</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
