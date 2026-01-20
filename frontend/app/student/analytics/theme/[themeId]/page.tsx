"use client";

import { AccuracyTrendChart } from "@/components/student/analytics/AccuracyTrendChart";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getThemeAnalytics } from "@/lib/api/analyticsApi";
import type { ThemeAnalytics } from "@/lib/types/analytics";
import { ArrowLeft, BookOpen, CheckCircle2, Target } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function ThemeAnalyticsPage() {
  const params = useParams();
  const router = useRouter();
  const themeId = parseInt(params.themeId as string, 10);

  const [data, setData] = useState<ThemeAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const result = await getThemeAnalytics(themeId);
        setData(result);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load theme analytics");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [themeId]);

  if (loading) {
    return (
      <div className="container max-w-7xl py-8">
        <div className="mb-6">
          <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
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
            <div className="flex justify-center gap-4">
              <Button onClick={() => router.back()} variant="outline">
                Go Back
              </Button>
              <Button onClick={() => window.location.reload()}>Retry</Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (!data || data.attempted === 0) {
    return (
      <div className="container max-w-7xl py-8">
        <Button onClick={() => router.back()} variant="ghost" className="mb-6">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Analytics
        </Button>
        <Card className="p-12">
          <div className="text-center">
            <BookOpen className="mx-auto mb-4 h-16 w-16 text-muted-foreground" />
            <h2 className="mb-2 text-xl font-semibold">No Data for This Theme</h2>
            <p className="mb-6 text-muted-foreground">
              You haven&apos;t attempted any questions from this theme yet
            </p>
            <Button asChild>
              <Link href={`/student/practice/build?themes=${themeId}`}>
                Practice This Theme
              </Link>
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="container max-w-7xl py-8">
      <Button onClick={() => router.back()} variant="ghost" className="mb-6">
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Analytics
      </Button>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{data.theme_name}</h1>
          <p className="text-sm text-muted-foreground">
            Block: {data.block_name}
          </p>
        </div>
        <Button asChild>
          <Link href={`/student/practice/build?themes=${themeId}`}>
            Practice This Theme
          </Link>
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="mb-6 grid gap-6 md:grid-cols-3">
        <Card className="p-6">
          <div className="flex items-center gap-4">
            <div className="rounded-full bg-primary/10 p-3">
              <Target className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Accuracy</p>
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
              <p className="text-sm text-muted-foreground">Questions Attempted</p>
              <p className="text-2xl font-bold">{data.attempted}</p>
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
      </div>

      {/* Trend Chart */}
      <div className="mb-6">
        <AccuracyTrendChart
          data={data.trend}
          title="Accuracy Trend for This Theme"
        />
      </div>

      {/* Future: Common Mistakes */}
      {data.common_mistakes && data.common_mistakes.length > 0 && (
        <Card className="p-6">
          <h3 className="mb-4 text-lg font-semibold">Common Mistakes</h3>
          <p className="text-sm text-muted-foreground">
            This feature is coming soon!
          </p>
        </Card>
      )}
    </div>
  );
}
