"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { Play, Clock, AlertCircle } from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";
import { getMessageFromApiError, is401 } from "@/lib/apiError";

interface ThemeDueInfo {
  theme_id: number;
  theme_name: string;
  block_id: number;
  block_name: string;
  due_count_today: number;
  overdue_count: number;
  next_due_at: string | null;
}

interface RevisionTodayResponse {
  due_today_total: number;
  overdue_total: number;
  themes: ThemeDueInfo[];
  recommended_theme_ids: number[];
}

export default function RevisionPage() {
  const router = useRouter();
  const [data, setData] = useState<RevisionTodayResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/learning/revision/today", {
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
      setData(data);
    } catch (err) {
      if (is401(err)) {
        router.push("/login");
        return;
      }
      console.error("Failed to load revision data:", err);
      setError(new Error(getMessageFromApiError(err, "Failed to load revision data")));
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleStartRevision = async (themeId: number) => {
    try {
      // Call adaptive selection with revision mode and theme filter
      const response = await fetch("/api/v1/learning/adaptive/next", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "revision",
          theme_ids: [themeId],
          count: 20, // Default from user prefs or config
        }),
      });

      if (!response.ok) throw new Error("Failed to start revision session");

      const result = await response.json();
      // Navigate to session or show success
      if (result.question_ids && result.question_ids.length > 0) {
        // Create session and redirect
        window.location.href = `/student/sessions/new?question_ids=${result.question_ids.join(",")}`;
      }
    } catch (err) {
      console.error("Failed to start revision:", err);
      alert("Failed to start revision session. Please try again.");
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">Revision</h1>
        <SkeletonTable rows={5} cols={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">Revision</h1>
        <ErrorState
          title="Failed to load revision data"
          description={error?.message}
          onAction={loadData}
        />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="container mx-auto py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Revision</h1>
        <p className="text-muted-foreground mt-2">Today's due themes for spaced repetition</p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Due Today</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.due_today_total}</div>
            <p className="text-xs text-muted-foreground">Items due for review</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
            <AlertCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">{data.overdue_total}</div>
            <p className="text-xs text-muted-foreground">Past due items</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Themes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.themes.length}</div>
            <p className="text-xs text-muted-foreground">Themes with due items</p>
          </CardContent>
        </Card>
      </div>

      {/* Due Themes Table */}
      <Card>
        <CardHeader>
          <CardTitle>Due Themes</CardTitle>
          <CardDescription>Start a revision session for any theme below</CardDescription>
        </CardHeader>
        <CardContent>
          {data.themes.length === 0 ? (
            <EmptyState
              title="No themes due today"
              description="Great job! You're all caught up. Check back tomorrow for new revision items."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Theme</TableHead>
                  <TableHead>Block</TableHead>
                  <TableHead>Due Today</TableHead>
                  <TableHead>Overdue</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.themes.map((theme) => (
                  <TableRow key={theme.theme_id}>
                    <TableCell className="font-medium">{theme.theme_name}</TableCell>
                    <TableCell>{theme.block_name}</TableCell>
                    <TableCell>
                      <Badge variant="default">{theme.due_count_today}</Badge>
                    </TableCell>
                    <TableCell>
                      {theme.overdue_count > 0 ? (
                        <Badge variant="destructive">{theme.overdue_count}</Badge>
                      ) : (
                        <span className="text-muted-foreground">0</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        onClick={() => handleStartRevision(theme.theme_id)}
                        disabled={theme.due_count_today === 0}
                      >
                        <Play className="h-4 w-4 mr-1" />
                        Start Revision
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
