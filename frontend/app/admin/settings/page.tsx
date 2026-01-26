"use client";

import { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAdminSettings, useSystemInfo, type PlatformSettings } from "@/lib/admin/settings/hooks";
import { GeneralSettings } from "@/components/admin/settings/GeneralSettings";
import { PracticeSettings } from "@/components/admin/settings/PracticeSettings";
import { SecuritySettings } from "@/components/admin/settings/SecuritySettings";
import { NotificationSettings } from "@/components/admin/settings/NotificationSettings";
import { SystemInfo, SystemControls } from "@/components/admin/settings/SystemInfo";
import { SettingsSkeleton } from "@/components/admin/settings/SettingsSkeleton";
import { InlineError } from "@/components/admin/settings/InlineError";
import { Save } from "lucide-react";

export default function AdminSettingsPage() {
  const { settings: serverSettings, loading, error, updateSettings } = useAdminSettings();
  const [draftSettings, setDraftSettings] = useState<PlatformSettings | null>(null);

  // Initialize draft when server settings load
  useEffect(() => {
    if (serverSettings) {
      setDraftSettings(serverSettings);
    }
  }, [serverSettings]);

  // Check if settings are dirty
  const isDirty = useMemo(() => {
    if (!serverSettings || !draftSettings) return false;
    return JSON.stringify(serverSettings) !== JSON.stringify(draftSettings);
  }, [serverSettings, draftSettings]);

  const handleSave = async () => {
    if (!draftSettings) return;
    try {
      await updateSettings(draftSettings);
      // Draft will be updated by the hook's refetch
    } catch {
      // Error already handled in hook
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Admin Settings</h1>
          <p className="text-muted-foreground">Platform-wide configuration and defaults</p>
        </div>
        <SettingsSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Admin Settings</h1>
          <p className="text-muted-foreground">Platform-wide configuration and defaults</p>
        </div>
        <InlineError message={error.message} />
      </div>
    );
  }

  if (!draftSettings) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Admin Settings</h1>
          <p className="text-muted-foreground">Platform-wide configuration and defaults</p>
        </div>
        <Button onClick={handleSave} disabled={!isDirty}>
          <Save className="mr-2 h-4 w-4" />
          Save Changes
        </Button>
      </div>

      {/* Settings Tabs */}
      <Tabs defaultValue="general" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="practice">Learning & Practice</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        <TabsContent value="general">
          <GeneralSettings settings={draftSettings} onChange={setDraftSettings} />
        </TabsContent>

        <TabsContent value="practice">
          <PracticeSettings settings={draftSettings} onChange={setDraftSettings} />
        </TabsContent>

        <TabsContent value="security">
          <SecuritySettings settings={draftSettings} onChange={setDraftSettings} />
        </TabsContent>

        <TabsContent value="notifications">
          <NotificationSettings settings={draftSettings} onChange={setDraftSettings} />
        </TabsContent>

        <TabsContent value="system">
          <SystemControls />
        </TabsContent>
      </Tabs>
    </div>
  );
}
