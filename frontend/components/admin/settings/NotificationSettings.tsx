"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { PlatformSettings } from "@/lib/admin/settings/hooks";

interface NotificationSettingsProps {
  settings: PlatformSettings;
  onChange: (settings: PlatformSettings) => void;
}

export function NotificationSettings({ settings, onChange }: NotificationSettingsProps) {
  const updateNotifications = (field: string, value: any) => {
    onChange({
      ...settings,
      notifications: {
        ...settings.notifications,
        [field]: value,
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Email */}
      <Card>
        <CardHeader>
          <CardTitle>Email Notifications</CardTitle>
          <CardDescription>Email notification preferences</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="password_reset_emails">Password Reset Emails</Label>
              <p className="text-sm text-muted-foreground">
                Send email when password is reset
              </p>
            </div>
            <Switch
              id="password_reset_emails"
              checked={settings.notifications.password_reset_emails_enabled}
              onCheckedChange={(checked) =>
                updateNotifications("password_reset_emails_enabled", checked)
              }
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="practice_reminders">
                Practice Reminders
                <Badge variant="secondary" className="ml-2">Coming soon</Badge>
              </Label>
              <p className="text-sm text-muted-foreground">
                Send reminders for practice sessions
              </p>
            </div>
            <Switch
              id="practice_reminders"
              checked={settings.notifications.practice_reminders_enabled}
              onCheckedChange={(checked) =>
                updateNotifications("practice_reminders_enabled", checked)
              }
              disabled={true}
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="admin_alerts">
                Admin Alerts
                <Badge variant="secondary" className="ml-2">Coming soon</Badge>
              </Label>
              <p className="text-sm text-muted-foreground">
                Send alerts to admins for system events
              </p>
            </div>
            <Switch
              id="admin_alerts"
              checked={settings.notifications.admin_alerts_enabled}
              onCheckedChange={(checked) =>
                updateNotifications("admin_alerts_enabled", checked)
              }
              disabled={true}
            />
          </div>
        </CardContent>
      </Card>

      {/* In-app */}
      <Card>
        <CardHeader>
          <CardTitle>In-app Notifications</CardTitle>
          <CardDescription>In-app notification preferences</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="inapp_announcements">In-app Announcements</Label>
              <p className="text-sm text-muted-foreground">
                Show announcements in the notifications center
              </p>
            </div>
            <Switch
              id="inapp_announcements"
              checked={settings.notifications.inapp_announcements_enabled}
              onCheckedChange={(checked) =>
                updateNotifications("inapp_announcements_enabled", checked)
              }
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
