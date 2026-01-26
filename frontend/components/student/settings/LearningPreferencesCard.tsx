"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, Save } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { getMessageFromApiError, is401 } from "@/lib/apiError";

interface LearningPrefs {
  revision_daily_target: number | null;
  spacing_multiplier: number;
  retention_target_override: number | null;
}

export function LearningPreferencesCard() {
  const router = useRouter();
  const [prefs, setPrefs] = useState<LearningPrefs | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form state
  const [revisionDailyTarget, setRevisionDailyTarget] = useState<string>("");
  const [spacingMultiplier, setSpacingMultiplier] = useState<string>("1.0");
  const [retentionTarget, setRetentionTarget] = useState<string>("");

  const loadPrefs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/users/me/preferences/learning", {
        credentials: "include",
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { error?: { message?: string } };
        const err = { status: response.status, error: body };
        if (response.status === 401) {
          router.push("/login");
          return;
        }
        throw err;
      }
      const data = await response.json();
      setPrefs(data);
      setRevisionDailyTarget(data.revision_daily_target?.toString() || "");
      setSpacingMultiplier(data.spacing_multiplier?.toString() || "1.0");
      setRetentionTarget(data.retention_target_override?.toString() || "");
    } catch (err) {
      if (is401(err)) {
        router.push("/login");
        return;
      }
      console.error("Failed to load learning preferences:", err);
      setError(getMessageFromApiError(err, "Failed to load preferences"));
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    loadPrefs();
  }, [loadPrefs]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const payload: Partial<LearningPrefs> = {};

      if (revisionDailyTarget) {
        const target = parseInt(revisionDailyTarget, 10);
        if (isNaN(target) || target < 1) {
          throw new Error("Daily target must be a positive integer");
        }
        payload.revision_daily_target = target;
      }

      if (spacingMultiplier) {
        const multiplier = parseFloat(spacingMultiplier);
        if (isNaN(multiplier) || multiplier < 0.5 || multiplier > 2.0) {
          throw new Error("Spacing multiplier must be between 0.5 and 2.0");
        }
        payload.spacing_multiplier = multiplier;
      }

      if (retentionTarget) {
        const retention = parseFloat(retentionTarget);
        if (isNaN(retention) || retention < 0.7 || retention > 0.95) {
          throw new Error("Retention target must be between 0.7 and 0.95");
        }
        payload.retention_target_override = retention;
      }

      const response = await fetch("/api/v1/users/me/preferences/learning", {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = (await response.json().catch(() => ({}))) as {
          detail?: string;
          error?: { message?: string };
        };
        const err = { status: response.status, error: errorData };
        if (response.status === 401) {
          router.push("/login");
          return;
        }
        throw err;
      }

      const data = await response.json();
      setPrefs(data);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      if (is401(err)) {
        router.push("/login");
        return;
      }
      console.error("Failed to save learning preferences:", err);
      setError(getMessageFromApiError(err, "Failed to save preferences"));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Learning Preferences</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Learning Preferences</CardTitle>
        <CardDescription>
          Customize your spaced repetition and revision settings
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert>
            <AlertDescription>Preferences saved successfully!</AlertDescription>
          </Alert>
        )}

        <div className="space-y-4">
          {/* Revision Daily Target */}
          <div className="space-y-2">
            <Label htmlFor="revision-daily-target">Daily Revision Target</Label>
            <Input
              id="revision-daily-target"
              type="number"
              min="1"
              placeholder="Default (auto)"
              value={revisionDailyTarget}
              onChange={(e) => setRevisionDailyTarget(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Target number of revision items per day (leave empty for auto)
            </p>
          </div>

          {/* Spacing Multiplier */}
          <div className="space-y-2">
            <Label htmlFor="spacing-multiplier">Spacing Multiplier</Label>
            <Input
              id="spacing-multiplier"
              type="number"
              min="0.5"
              max="2.0"
              step="0.1"
              value={spacingMultiplier}
              onChange={(e) => setSpacingMultiplier(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Adjust review frequency: 0.8 = more frequent, 1.2 = less frequent (default: 1.0)
            </p>
          </div>

          {/* Retention Target Override */}
          <div className="space-y-2">
            <Label htmlFor="retention-target">Retention Target Override</Label>
            <Input
              id="retention-target"
              type="number"
              min="0.7"
              max="0.95"
              step="0.01"
              placeholder="Default (0.90)"
              value={retentionTarget}
              onChange={(e) => setRetentionTarget(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Target retention probability (0.7-0.95). Leave empty to use system default (0.90)
            </p>
          </div>

          <Button onClick={handleSave} disabled={saving}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving..." : "Save Preferences"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
