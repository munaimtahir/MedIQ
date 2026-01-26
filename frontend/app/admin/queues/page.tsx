"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { CheckCircle, XCircle, Clock, Loader } from "lucide-react";

interface QueueStats {
  global_totals: {
    due_today: number;
    overdue: number;
    due_tomorrow: number;
  };
  breakdown_by_theme: Array<{
    theme_id: number;
    theme_name: string;
    due_today: number;
    overdue: number;
  }>;
  breakdown_by_block: Array<{
    block_id: number;
    block_name: string;
    due_today: number;
    overdue: number;
  }>;
  last_regen_job: {
    id: string;
    status: string;
    started_at: string | null;
    finished_at: string | null;
    stats: Record<string, any>;
    error: string | null;
  } | null;
  trend: Array<{
    date: string;
    due_today: number;
    overdue: number;
    due_tomorrow: number;
    users_with_due: number;
  }>;
}

export default function QueuesPage() {
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/admin/queues/stats");
      if (!response.ok) throw new Error("Failed to load queue stats");
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error("Failed to load queue stats:", err);
      setError(err instanceof Error ? err : new Error("Failed to load queue stats"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      QUEUED: "secondary",
      RUNNING: "default",
      SUCCEEDED: "default",
      FAILED: "destructive",
    };
    const icons: Record<string, any> = {
      QUEUED: Clock,
      RUNNING: Loader,
      SUCCEEDED: CheckCircle,
      FAILED: XCircle,
    };
    const Icon = icons[status] || Clock;
    return (
      <Badge variant={variants[status] || "secondary"}>
        <Icon className="mr-1 h-3 w-3" />
        {status}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">Queue Statistics</h1>
        <SkeletonTable rows={5} cols={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">Queue Statistics</h1>
        <ErrorState
          title="Failed to load queue statistics"
          description={error?.message}
          onAction={loadStats}
        />
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <div className="container mx-auto py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Queue Statistics</h1>
        <p className="text-muted-foreground mt-2">Revision queue statistics and job monitoring</p>
      </div>

      {/* Global Totals */}
      <div className="grid gap-4 md:grid-cols-3 mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Due Today</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.global_totals.due_today}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">{stats.global_totals.overdue}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Due Tomorrow</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.global_totals.due_tomorrow}</div>
          </CardContent>
        </Card>
      </div>

      {/* Last Job Run */}
      {stats.last_regen_job && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Last Regeneration Job</CardTitle>
            <CardDescription>Most recent revision queue regeneration</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Status:</span>
                {getStatusBadge(stats.last_regen_job.status)}
              </div>
              {stats.last_regen_job.stats && (
                <div className="text-sm">
                  <span className="font-medium">Processed Users:</span>{" "}
                  {stats.last_regen_job.stats.processed_users || 0}
                </div>
              )}
              {stats.last_regen_job.error && (
                <div className="text-sm text-destructive">
                  <span className="font-medium">Error:</span> {stats.last_regen_job.error}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Top Themes */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Top Themes by Due Items</CardTitle>
          <CardDescription>Top 20 themes with most due items</CardDescription>
        </CardHeader>
        <CardContent>
          {stats.breakdown_by_theme.length === 0 ? (
            <EmptyState title="No themes with due items" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Theme</TableHead>
                  <TableHead>Due Today</TableHead>
                  <TableHead>Overdue</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stats.breakdown_by_theme.map((theme) => (
                  <TableRow key={theme.theme_id}>
                    <TableCell className="font-medium">{theme.theme_name}</TableCell>
                    <TableCell>{theme.due_today}</TableCell>
                    <TableCell>{theme.overdue}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Breakdown by Block */}
      <Card>
        <CardHeader>
          <CardTitle>Breakdown by Block</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Block</TableHead>
                <TableHead>Due Today</TableHead>
                <TableHead>Overdue</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stats.breakdown_by_block.map((block) => (
                <TableRow key={block.block_id}>
                  <TableCell className="font-medium">{block.block_name}</TableCell>
                  <TableCell>{block.due_today}</TableCell>
                  <TableCell>{block.overdue}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
