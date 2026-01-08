"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DashboardMetrics } from "@/lib/dashboard/types";
import { Flame, Clock, FileQuestion, BarChart3 } from "lucide-react";
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

interface StreakSummaryCardProps {
  metrics: DashboardMetrics | null;
  loading?: boolean;
  error?: Error | null;
}

export function StreakSummaryCard({ 
  metrics, 
  loading, 
  error: _error // eslint-disable-line @typescript-eslint/no-unused-vars
}: StreakSummaryCardProps) {
  const router = useRouter();

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </CardContent>
      </Card>
    );
  }

  const displayMetrics = metrics || {
    streakDays: 0,
    minutesThisWeek: 0,
    questionsThisWeek: 0,
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity</CardTitle>
        <CardDescription>Your study progress</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Flame className="h-4 w-4 text-orange-500" />
              <span className="text-sm text-muted-foreground">Days active</span>
            </div>
            <span className="font-semibold">{displayMetrics.streakDays} days</span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-500" />
              <span className="text-sm text-muted-foreground">Time this week</span>
            </div>
            <span className="font-semibold">{displayMetrics.minutesThisWeek} min</span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileQuestion className="h-4 w-4 text-green-500" />
              <span className="text-sm text-muted-foreground">Questions this week</span>
            </div>
            <span className="font-semibold">{displayMetrics.questionsThisWeek}</span>
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="w-full"
          onClick={() => router.push("/student/analytics")}
        >
          <BarChart3 className="mr-2 h-4 w-4" />
          View analytics
        </Button>
      </CardContent>
    </Card>
  );
}
