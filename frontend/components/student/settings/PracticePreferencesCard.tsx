"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";

const STORAGE_KEY = "student_prefs_v1";

interface PracticePreferences {
  defaultMode: "tutor" | "exam";
  resumeUnfinished: boolean;
  showReviewImmediately: boolean;
  hideTimerInTutor: boolean;
}

const defaultPreferences: PracticePreferences = {
  defaultMode: "tutor",
  resumeUnfinished: false,
  showReviewImmediately: true,
  hideTimerInTutor: false,
};

export function PracticePreferencesCard() {
  const [preferences, setPreferences] = useState<PracticePreferences>(defaultPreferences);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load from localStorage
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setPreferences({ ...defaultPreferences, ...parsed });
      }
    } catch (error) {
      console.error("Failed to load preferences:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const updatePreference = <K extends keyof PracticePreferences>(
    key: K,
    value: PracticePreferences[K]
  ) => {
    const updated = { ...preferences, [key]: value };
    setPreferences(updated);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch (error) {
      console.error("Failed to save preferences:", error);
    }
  };

  if (loading) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Practice behavior</CardTitle>
        <CardDescription>Customize your practice experience</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          <Label>Default practice mode</Label>
          <RadioGroup
            value={preferences.defaultMode}
            onValueChange={(value) => updatePreference("defaultMode", value as "tutor" | "exam")}
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="tutor" id="mode-tutor" />
              <Label htmlFor="mode-tutor" className="cursor-pointer">
                Tutor
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="exam" id="mode-exam" />
              <Label htmlFor="mode-exam" className="cursor-pointer">
                Exam
              </Label>
            </div>
          </RadioGroup>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="resume-unfinished">Resume last unfinished session automatically</Label>
              <p className="text-sm text-muted-foreground">
                Automatically resume your last incomplete practice session when starting practice
              </p>
            </div>
            <Checkbox
              id="resume-unfinished"
              checked={preferences.resumeUnfinished}
              onCheckedChange={(checked) => updatePreference("resumeUnfinished", checked === true)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="show-review">Show review immediately after submit</Label>
              <p className="text-sm text-muted-foreground">
                Automatically show review screen after completing a practice session
              </p>
            </div>
            <Checkbox
              id="show-review"
              checked={preferences.showReviewImmediately}
              onCheckedChange={(checked) => updatePreference("showReviewImmediately", checked === true)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="hide-timer">Hide timer in tutor mode</Label>
              <p className="text-sm text-muted-foreground">
                Hide the timer when practicing in tutor mode
              </p>
            </div>
            <Checkbox
              id="hide-timer"
              checked={preferences.hideTimerInTutor}
              onCheckedChange={(checked) => updatePreference("hideTimerInTutor", checked === true)}
            />
          </div>
        </div>

        <p className="text-xs text-muted-foreground">
          These preferences apply on this device
        </p>
      </CardContent>
    </Card>
  );
}
