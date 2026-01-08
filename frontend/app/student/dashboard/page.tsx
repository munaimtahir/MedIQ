"use client";

import { useDashboardData } from "@/lib/dashboard/hooks";
import { NextBestActionCard } from "@/components/student/dashboard/NextBestActionCard";
import { StreakSummaryCard } from "@/components/student/dashboard/StreakSummaryCard";
import { BlockProgressCard } from "@/components/student/dashboard/BlockProgressCard";
import { WeakThemesCard } from "@/components/student/dashboard/WeakThemesCard";
import { QuickPracticePresetsCard } from "@/components/student/dashboard/QuickPracticePresetsCard";
import { RecentActivityCard } from "@/components/student/dashboard/RecentActivityCard";
import { BrowseSyllabusCard } from "@/components/student/dashboard/BrowseSyllabusCard";
import { AnnouncementsCard } from "@/components/student/dashboard/AnnouncementsCard";
import { DashboardSkeleton } from "@/components/student/dashboard/DashboardSkeleton";
import { useUserStore } from "@/store/userStore";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useRouter } from "next/navigation";

export default function StudentDashboard() {
  const { data, loading, error } = useDashboardData();
  const { user } = useUserStore();
  const router = useRouter();

  // Show skeleton while loading (but not if there's an error)
  if (loading && !error) {
    return <DashboardSkeleton />;
  }

  // Show error state
  if (error && !data) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome{user?.name ? ` ${user.name}` : ""}!
          </p>
        </div>
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Failed to Load Dashboard
            </CardTitle>
            <CardDescription>
              We encountered an error while loading your dashboard data.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {error.message || "An unexpected error occurred"}
            </p>
            <div className="flex gap-2">
              <Button
                onClick={() => router.refresh()}
                variant="default"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
              <Button
                onClick={() => router.push("/student/blocks")}
                variant="outline"
              >
                Go to Blocks
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show skeleton if we have an error but are still loading (shouldn't happen, but safety check)
  if (!data) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome{user?.name ? ` ${user.name}` : ""}!
        </p>
      </div>

      {/* Row 1: Next Best Action + Streak Summary */}
      <div className="grid gap-4 md:grid-cols-3">
        <NextBestActionCard
          nextAction={data.nextAction}
          loading={false}
          error={error}
        />
        <StreakSummaryCard metrics={data.metrics} loading={false} error={null} />
      </div>

      {/* Row 2: Block Progress + Weak Themes */}
      <div className="grid gap-4 md:grid-cols-2">
        <BlockProgressCard blocks={data.blocks} loading={false} error={null} />
        <WeakThemesCard weakThemes={data.weakThemes} loading={false} error={null} />
      </div>

      {/* Row 3: Quick Practice Presets + Recent Activity */}
      <div className="grid gap-4 md:grid-cols-2">
        <QuickPracticePresetsCard />
        <RecentActivityCard recentSessions={data.recentSessions} loading={false} error={null} />
      </div>

      {/* Row 4: Browse Syllabus + Announcements */}
      <div className="grid gap-4 md:grid-cols-2">
        <BrowseSyllabusCard
          blocks={data.blocks}
          themesByBlock={data.themesByBlock}
          loading={false}
          error={null}
        />
        <AnnouncementsCard announcements={data.announcements} loading={false} error={null} />
      </div>
    </div>
  );
}
