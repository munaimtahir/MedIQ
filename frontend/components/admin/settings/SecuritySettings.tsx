"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { PlatformSettings } from "@/lib/admin/settings/hooks";

interface SecuritySettingsProps {
  settings: PlatformSettings;
  onChange: (settings: PlatformSettings) => void;
}

export function SecuritySettings({ settings, onChange }: SecuritySettingsProps) {
  const updateSecurity = (field: string, value: any) => {
    onChange({
      ...settings,
      security: {
        ...settings.security,
        [field]: value,
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Token Defaults */}
      <Card>
        <CardHeader>
          <CardTitle>Token Defaults</CardTitle>
          <CardDescription>JWT token expiration settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="access_token_minutes">
              Access Token Minutes (5-240)
            </Label>
            <Input
              id="access_token_minutes"
              type="number"
              min={5}
              max={240}
              value={settings.security.access_token_minutes}
              onChange={(e) => {
                const value = Number(e.target.value);
                if (value >= 5 && value <= 240) {
                  updateSecurity("access_token_minutes", value);
                }
              }}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="refresh_token_days">Refresh Token Days (1-90)</Label>
            <Input
              id="refresh_token_days"
              type="number"
              min={1}
              max={90}
              value={settings.security.refresh_token_days}
              onChange={(e) => {
                const value = Number(e.target.value);
                if (value >= 1 && value <= 90) {
                  updateSecurity("refresh_token_days", value);
                }
              }}
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="force_logout_on_password_reset">
                Force Logout on Password Reset
              </Label>
              <p className="text-sm text-muted-foreground">
                Invalidate all sessions when password is reset
              </p>
            </div>
            <Switch
              id="force_logout_on_password_reset"
              checked={settings.security.force_logout_on_password_reset}
              onCheckedChange={(checked) =>
                updateSecurity("force_logout_on_password_reset", checked)
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Rate Limits */}
      <Card>
        <CardHeader>
          <CardTitle>Rate Limits</CardTitle>
          <CardDescription>API rate limiting configuration</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Configured in infrastructure
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
