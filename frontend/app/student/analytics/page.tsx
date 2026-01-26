"use client";

import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getOverview } from "@/lib/api/analyticsApi";
import type { AnalyticsOverview } from "@/lib/types/analytics";
import { BarChart3, BookOpen, CheckCircle2, Target } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

// Lazy load heavy chart components
const AccuracyTrendChart = dynamic(
  () => import("@/components/student/analytics/AccuracyTrendChart").then((mod) => ({ 
    default: mod.AccuracyTrendChart 
  })),
  { 
    loading: () => <Skeleton className="h-[200px] w-full rounded-lg" />,
    ssr: false,
  }
);

const BlockAccuracyChart = dynamic(
  () => import("@/components/student/analytics/BlockAccuracyChart").then((mod) => ({ 
    default: mod.BlockAccuracyChart 
  })),
  { 
    loading: () => <Skeleton className="h-[300px] w-full rounded-lg" />,
    ssr: false,
  }
);

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const result = await getOverview();
        setData(result);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load analytics");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="container max-w-7xl py-8">
        <div className="mb-6">
          <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-6">
              <div className="h-24 animate-pulse rounded bg-muted" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container max-w-7xl py-8">
        <Card className="p-6">
          <div className="text-center">
            <p className="mb-4 text-destructive">{error}</p>
            <Button onClick={() => window.location.reload()}>Retry</Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!data || data.sessions_completed === 0) {
    return (
      <div className="container max-w-7xl py-8">
        <h1 className="mb-6 text-3xl font-bold">Analytics</h1>
        <Card className="p-12">
          <div className="text-center">
            <BarChart3 className="mx-auto mb-4 h-16 w-16 text-muted-foreground" />
            <h2 className="mb-2 text-xl font-semibold">No Analytics Yet</h2>
            <p className="mb-6 text-muted-foreground">
              Complete your first practice session to see your performance analytics
            </p>
            <Button asChild>
              <Link href="/student/practice/build">Start Practicing</Link>
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="container max-w-7xl py-8">
      <h1 className="mb-6 text-3xl font-bold">Analytics</h1>

      {/* Stats Cards */}
      <div className="mb-6 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card className="p-6">
          <div className="flex items-center gap-4">
            <div className="rounded-full bg-primary/10 p-3">
              <Target className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Overall Accuracy</p>
              <p className="text-2xl font-bold">{data.accuracy_pct.toFixed(1)}%</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-4">
            <div className="rounded-full bg-primary/10 p-3">
              <BookOpen className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Questions Seen</p>
              <p className="text-2xl font-bold">{data.questions_seen}</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-4">
            <div className="rounded-full bg-primary/10 p-3">
              <CheckCircle2 className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Correct Answers</p>
              <p className="text-2xl font-bold">{data.correct}</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-4">
            <div className="rounded-full bg-primary/10 p-3">
              <BarChart3 className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Sessions Completed</p>
              <p className="text-2xl font-bold">{data.sessions_completed}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Charts */}
      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <AccuracyTrendChart data={data.trend} title="Accuracy Over Time" />
        <BlockAccuracyChart data={data.by_block} />
      </div>

      {/* Weakest Themes */}
      {data.weakest_themes.length > 0 && (
        <Card className="mb-6 p-6">
          <h3 className="mb-4 text-lg font-semibold">Areas for Improvement</h3>
          <div className="space-y-3">
            {data.weakest_themes.slice(0, 5).map((theme) => (
              <div
                key={theme.theme_id}
                className="flex items-center justify-between rounded-lg border p-4"
              >
                <div className="flex-1">
                  <p className="font-medium">{theme.theme_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {theme.correct} / {theme.attempted} correct
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-2xl font-bold">{theme.accuracy_pct.toFixed(1)}%</p>
                  </div>
                  <Button asChild variant="outline" size="sm">
                    <Link href={`/student/practice/build?themes=${theme.theme_id}`}>Practice</Link>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Last Session */}
      {data.last_session && (
        <Card className="p-6">
          <h3 className="mb-4 text-lg font-semibold">Last Session</h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Score</p>
              <p className="text-2xl font-bold">{data.last_session.score_pct.toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Completed</p>
              <p className="font-medium">
                {new Date(data.last_session.submitted_at).toLocaleDateString()}
              </p>
            </div>
            <Button asChild variant="outline">
              <Link href={`/student/session/${data.last_session.session_id}/review`}>
                View Review
              </Link>
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
