"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PlatformSettings } from "@/lib/admin/settings/hooks";
import { syllabusAPI, Year } from "@/lib/api";
import { useEffect, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";

interface GeneralSettingsProps {
  settings: PlatformSettings;
  onChange: (settings: PlatformSettings) => void;
}

export function GeneralSettings({ settings, onChange }: GeneralSettingsProps) {
  const [years, setYears] = useState<Year[]>([]);
  const [loadingYears, setLoadingYears] = useState(false);

  useEffect(() => {
    loadYears();
  }, []);

  async function loadYears() {
    setLoadingYears(true);
    try {
      const data = await syllabusAPI.getYears();
      setYears(data);
    } catch (error) {
      console.error("Failed to load years:", error);
    } finally {
      setLoadingYears(false);
    }
  }

  const updateGeneral = (field: string, value: any) => {
    onChange({
      ...settings,
      general: {
        ...settings.general,
        [field]: value,
      },
    });
  };

  const updateAcademic = (field: string, value: any) => {
    onChange({
      ...settings,
      academic_defaults: {
        ...settings.academic_defaults,
        [field]: value,
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Platform Identity */}
      <Card>
        <CardHeader>
          <CardTitle>Platform Identity</CardTitle>
          <CardDescription>Basic platform information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="platform_name">Platform Name *</Label>
            <Input
              id="platform_name"
              value={settings.general.platform_name}
              onChange={(e) => updateGeneral("platform_name", e.target.value)}
              maxLength={80}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="platform_description">Platform Description</Label>
            <Textarea
              id="platform_description"
              value={settings.general.platform_description}
              onChange={(e) => updateGeneral("platform_description", e.target.value)}
              maxLength={500}
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="default_language">Default Language</Label>
            <Select
              value={settings.general.default_language}
              onValueChange={(v) => updateGeneral("default_language", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">English</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="timezone">Timezone</Label>
            <Select
              value={settings.general.timezone}
              onValueChange={(v) => updateGeneral("timezone", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Asia/Karachi">Asia/Karachi</SelectItem>
                <SelectItem value="UTC">UTC</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Academic Defaults */}
      <Card>
        <CardHeader>
          <CardTitle>Academic Defaults</CardTitle>
          <CardDescription>Default academic year and visibility settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="default_year">Default Year</Label>
            {loadingYears ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <Select
                value={settings.academic_defaults.default_year_id?.toString() || "none"}
                onValueChange={(v) =>
                  updateAcademic("default_year_id", v === "none" ? null : Number(v))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="None" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  {years.map((year) => (
                    <SelectItem key={year.id} value={year.id.toString()}>
                      {year.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="blocks_visibility">Blocks Visibility Mode</Label>
            <Select
              value={settings.academic_defaults.blocks_visibility_mode}
              onValueChange={(v) => updateAcademic("blocks_visibility_mode", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="user_selected">User Selected</SelectItem>
                <SelectItem value="all">All</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="default_landing">Default Landing Page</Label>
            <Select
              value={settings.general.default_landing}
              onValueChange={(v) => updateGeneral("default_landing", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dashboard">Dashboard</SelectItem>
                <SelectItem value="blocks">Blocks</SelectItem>
                <SelectItem value="analytics">Analytics</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
