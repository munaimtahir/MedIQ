"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PlatformSettings } from "@/lib/admin/settings/hooks";

interface PracticeSettingsProps {
  settings: PlatformSettings;
  onChange: (settings: PlatformSettings) => void;
}

export function PracticeSettings({ settings, onChange }: PracticeSettingsProps) {
  const updatePractice = (field: string, value: any) => {
    onChange({
      ...settings,
      practice_defaults: {
        ...settings.practice_defaults,
        [field]: value,
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Practice Defaults */}
      <Card>
        <CardHeader>
          <CardTitle>Practice Defaults</CardTitle>
          <CardDescription>Default practice behavior settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="default_mode">Default Mode</Label>
            <Select
              value={settings.practice_defaults.default_mode}
              onValueChange={(v) => updatePractice("default_mode", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tutor">Tutor</SelectItem>
                <SelectItem value="exam">Exam</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="timer_default">Timer Default</Label>
            <Select
              value={settings.practice_defaults.timer_default}
              onValueChange={(v) => updatePractice("timer_default", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="untimed">Untimed</SelectItem>
                <SelectItem value="timed">Timed</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="review_policy">Review Policy</Label>
            <Select
              value={settings.practice_defaults.review_policy}
              onValueChange={(v) => updatePractice("review_policy", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="always">Always</SelectItem>
                <SelectItem value="after_submit">After Submit</SelectItem>
                <SelectItem value="never">Never</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Self-paced Rules */}
      <Card>
        <CardHeader>
          <CardTitle>Self-paced Learning (Defaults Only)</CardTitle>
          <CardDescription>
            These settings define defaults. Students can still choose any block/theme unless
            future restrictions are explicitly built (we are not building them).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="allow_mixed_blocks">Allow Mixed Blocks</Label>
              <p className="text-sm text-muted-foreground">
                Allow practice sessions with questions from multiple blocks
              </p>
            </div>
            <Switch
              id="allow_mixed_blocks"
              checked={settings.practice_defaults.allow_mixed_blocks}
              onCheckedChange={(checked) => updatePractice("allow_mixed_blocks", checked)}
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="allow_any_block_anytime">Allow Any Block Anytime</Label>
              <p className="text-sm text-muted-foreground">
                Students can practice any block regardless of progression
              </p>
            </div>
            <Switch
              id="allow_any_block_anytime"
              checked={settings.practice_defaults.allow_any_block_anytime}
              onCheckedChange={(checked) => updatePractice("allow_any_block_anytime", checked)}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
