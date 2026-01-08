"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BarChart3, TrendingUp, Target, Clock, Info } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { InlineAlert } from "@/components/auth/InlineAlert";

interface AnalyticsData {
  total_sessions?: number;
  average_score?: number;
  questions_answered?: number;
  study_time_hours?: number;
}

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    loadAnalytics();
  }, []);

  async function loadAnalytics() {
    setLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual analytics endpoint when available
      // For now, check if endpoint exists
      const response = await fetch("/api/analytics/overview", {
        credentials: "include",
      });

      if (response.ok) {
        const result = await response.json();
        setData(result);
      } else if (response.status === 404) {
        // Endpoint not implemented yet - this is expected
        setData(null);
      } else {
        throw new Error("Failed to load analytics");
      }
    } catch (err) {
      // Endpoint doesn't exist yet - this is fine
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  const hasData = data && (
    data.total_sessions !== undefined ||
    data.average_score !== undefined ||
    data.questions_answered !== undefined ||
    data.study_time_hours !== undefined
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">Track your progress and performance</p>
      </div>

      {/* No Data State */}
      {!hasData && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Info className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">Analytics will appear here</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Once you start attempting questions and completing practice sessions, your
                performance metrics will be displayed here.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="by-block" disabled={!hasData}>
            By Block
          </TabsTrigger>
          <TabsTrigger value="by-theme" disabled={!hasData}>
            By Theme
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {hasData ? (
            <>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Total Sessions</CardTitle>
                    <BarChart3 className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {data.total_sessions ?? 0}
                    </div>
                    <p className="text-xs text-muted-foreground">Practice sessions completed</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Average Score</CardTitle>
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {data.average_score !== undefined
                        ? `${Math.round(data.average_score)}%`
                        : "N/A"}
                    </div>
                    <p className="text-xs text-muted-foreground">Across all sessions</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Questions Answered</CardTitle>
                    <Target className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {data.questions_answered ?? 0}
                    </div>
                    <p className="text-xs text-muted-foreground">Total practice questions</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Study Time</CardTitle>
                    <Clock className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {data.study_time_hours !== undefined
                        ? `${data.study_time_hours.toFixed(1)}h`
                        : "0h"}
                    </div>
                    <p className="text-xs text-muted-foreground">Hours this month</p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Performance Chart</CardTitle>
                  <CardDescription>Score trends over time</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex h-64 items-center justify-center text-muted-foreground">
                    <p>Chart visualization will appear here once more data is available</p>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center py-8">
                  <p className="text-sm text-muted-foreground">
                    Analytics data will appear here once you start practicing.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="by-block">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground">
                  Block-level analytics will be available once the analytics engine is enabled.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="by-theme">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground">
                  Theme-level analytics will be available once the analytics engine is enabled.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
