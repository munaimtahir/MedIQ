"use client";

import { memo, useMemo, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { WeakTheme } from "@/lib/dashboard/types";
import { AlertTriangle, Play } from "lucide-react";
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

interface WeakThemesCardProps {
  weakThemes: WeakTheme[];
  loading?: boolean;
  error?: Error | null;
}

const getReasonLabel = (reason: WeakTheme["reason"]): string => {
  switch (reason) {
    case "low_accuracy":
      return "Low accuracy";
    case "needs_attention":
      return "Needs attention";
    case "not_practiced":
      return "Not practiced";
    default:
      return "Needs attention";
  }
};

const getReasonVariant = (
  reason: WeakTheme["reason"],
): "default" | "destructive" | "secondary" => {
  switch (reason) {
    case "low_accuracy":
      return "destructive";
    case "needs_attention":
      return "default";
    case "not_practiced":
      return "secondary";
    default:
      return "default";
  }
};

export const WeakThemesCard = memo(function WeakThemesCard({ 
  weakThemes, 
  loading, 
  error 
}: WeakThemesCardProps) {
  const router = useRouter();
  
  // Memoize top 6 weak themes
  const topWeakThemes = useMemo(() => weakThemes.slice(0, 6), [weakThemes]);

  if (loading) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <Skeleton className="h-5 w-32" />
          <Skeleton className="mt-2 h-4 w-48" />
        </CardHeader>
        <CardContent className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <CardTitle>Weak Themes</CardTitle>
          <CardDescription>Themes that need attention</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Unable to load weak themes. Start practicing to see your weak areas.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (weakThemes.length === 0) {
    return (
      <Card className="col-span-full md:col-span-1">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Weak Themes
          </CardTitle>
          <CardDescription>Themes that need attention</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            Not enough data yet. Complete practice sessions to identify weak themes.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/student/practice/build")}
          >
            <Play className="mr-2 h-4 w-4" />
            Start Practice
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="col-span-full md:col-span-1">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-yellow-500" />
          Weak Themes
        </CardTitle>
        <CardDescription>Top themes that need attention</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {topWeakThemes.map((theme) => (
          <div
            key={theme.themeId}
            className="flex items-center justify-between rounded-lg border p-3"
          >
            <div className="flex-1">
              <p className="text-sm font-medium">{theme.themeTitle}</p>
              <div className="mt-1 flex items-center gap-2">
                <Badge variant={getReasonVariant(theme.reason)} className="text-xs">
                  {getReasonLabel(theme.reason)}
                </Badge>
                <span className="text-xs text-muted-foreground">Block {theme.blockCode}</span>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                router.push(`/student/blocks/${theme.blockId}/themes/${theme.themeId}`)
              }
            >
              <Play className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
});
