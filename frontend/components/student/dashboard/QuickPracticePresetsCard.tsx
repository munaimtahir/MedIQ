"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Zap, Clock, FileText, Shuffle } from "lucide-react";
import { useRouter } from "next/navigation";

export function QuickPracticePresetsCard() {
  const router = useRouter();

  const presets = [
    {
      label: "10 MCQs (Tutor)",
      icon: Zap,
      href: "/student/practice/build?preset=tutor&count=10",
      description: "Quick practice with explanations",
    },
    {
      label: "20 MCQs (Tutor)",
      icon: Zap,
      href: "/student/practice/build?preset=tutor&count=20",
      description: "Standard practice session",
    },
    {
      label: "20 MCQs (Exam)",
      icon: Clock,
      href: "/student/practice/build?preset=exam&count=20",
      description: "Timed exam mode",
    },
    {
      label: "Random Mixed",
      icon: Shuffle,
      href: "/student/practice/build?preset=random",
      description: "Mixed topics and difficulty",
    },
    {
      label: "Past Paper Style",
      icon: FileText,
      href: "/student/practice/build?preset=pastpaper",
      description: "Coming soon",
      disabled: true,
    },
  ];

  return (
    <Card className="col-span-full md:col-span-1">
      <CardHeader>
        <CardTitle>Quick Practice</CardTitle>
        <CardDescription>Start practicing with presets</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {presets.map((preset) => {
          const Icon = preset.icon;
          return (
            <Button
              key={preset.label}
              variant="outline"
              className="w-full justify-start"
              onClick={() => !preset.disabled && router.push(preset.href)}
              disabled={preset.disabled}
            >
              <Icon className="mr-2 h-4 w-4" />
              <div className="flex-1 text-left">
                <div className="font-medium">{preset.label}</div>
                <div className="text-xs text-muted-foreground">{preset.description}</div>
              </div>
            </Button>
          );
        })}
      </CardContent>
    </Card>
  );
}
