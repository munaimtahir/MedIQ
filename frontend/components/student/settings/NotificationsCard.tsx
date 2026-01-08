"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";

export function NotificationsCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Notifications</CardTitle>
        <CardDescription>Manage your notification preferences</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="practice-reminders" className="text-muted-foreground">
              Practice reminders
            </Label>
            <p className="text-sm text-muted-foreground">Email and in-app reminders for practice</p>
          </div>
          <Checkbox id="practice-reminders" disabled />
        </div>

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="syllabus-updates" className="text-muted-foreground">
              Announcements about syllabus updates
            </Label>
            <p className="text-sm text-muted-foreground">
              Get notified when syllabus content is updated
            </p>
          </div>
          <Checkbox id="syllabus-updates" disabled />
        </div>

        <p className="text-xs text-muted-foreground">Coming soon</p>
      </CardContent>
    </Card>
  );
}
