"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { adminPerfApi, type PerfSlowRow, type PerfSummary } from "@/lib/api/adminPerf";
import { useUserStore } from "@/store/userStore";

export default function AdminPerformancePage() {
  const user = useUserStore((s) => s.user);
  const isAdmin = user?.role === "ADMIN";

  const [summary, setSummary] = useState<PerfSummary | null>(null);
  const [slow, setSlow] = useState<PerfSlowRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, slowRows] = await Promise.all([adminPerfApi.summary("24h"), adminPerfApi.slow(50)]);
      setSummary(s);
      setSlow(slowRows);
    } catch (e) {
      const err = e as Error;
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(() => load(), 45_000);
    return () => clearInterval(t);
  }, [load]);

  const hasData = useMemo(() => (summary?.requests || 0) > 0, [summary?.requests]);

  if (!isAdmin) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-2">Performance</h1>
        <p className="text-muted-foreground">Admin access required.</p>
      </div>
    );
  }

  if (loading && !summary) {
    return (
      <div className="container mx-auto py-8 space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Performance</h1>
          <p className="text-muted-foreground">Latency and DB pressure (last 24h)</p>
        </div>
        <SkeletonTable rows={6} cols={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">Performance</h1>
        <ErrorState
          title="Failed to load performance data"
          description={error.message || "An error occurred"}
          onAction={load}
        />
      </div>
    );
  }

  if (!summary || !hasData) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-2">Performance</h1>
        <p className="text-muted-foreground mb-6">Latency and DB pressure (last 24h)</p>
        <EmptyState title="No data yet" description="No perf samples have been recorded yet." />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Performance</h1>
        <p className="text-muted-foreground">Latency and DB pressure (window: {summary.window})</p>
      </div>

      {/* Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">p50</CardTitle>
            <CardDescription>Median latency</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(summary.p50_ms)}ms</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">p95</CardTitle>
            <CardDescription>Tail latency</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(summary.p95_ms)}ms</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">p99</CardTitle>
            <CardDescription>Worst-case-ish</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(summary.p99_ms)}ms</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Slow</CardTitle>
            <CardDescription>&gt; 500ms</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.slow_count}</div>
          </CardContent>
        </Card>
      </div>

      {/* DB pressure */}
      <Card>
        <CardHeader>
          <CardTitle>DB pressure</CardTitle>
          <CardDescription>Derived from sampled requests</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <div className="text-sm text-muted-foreground">p95 DB time</div>
            <div className="text-xl font-semibold">{Math.round(summary.db.p95_db_ms)}ms</div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">avg queries/request</div>
            <div className="text-xl font-semibold">{summary.db.avg_queries.toFixed(1)}</div>
          </div>
        </CardContent>
      </Card>

      {/* Top routes */}
      <Card>
        <CardHeader>
          <CardTitle>Top routes by p95</CardTitle>
          <CardDescription>Highest tail latency routes in the window</CardDescription>
        </CardHeader>
        <CardContent>
          {summary.top_routes.length === 0 ? (
            <EmptyState title="No route data" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Path</TableHead>
                  <TableHead>Count</TableHead>
                  <TableHead>p95</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.top_routes.map((r) => (
                  <TableRow key={r.path}>
                    <TableCell className="font-mono text-xs">{r.path}</TableCell>
                    <TableCell>{r.count}</TableCell>
                    <TableCell>{Math.round(r.p95_ms)}ms</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Slow requests */}
      <Card>
        <CardHeader>
          <CardTitle>Slow requests</CardTitle>
          <CardDescription>Last 50 requests &gt; 500ms</CardDescription>
        </CardHeader>
        <CardContent>
          {slow.length === 0 ? (
            <EmptyState title="No slow requests yet" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Route</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Total</TableHead>
                  <TableHead>DB</TableHead>
                  <TableHead>Queries</TableHead>
                  <TableHead>Req ID</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {slow.map((r) => (
                  <TableRow key={`${r.request_at}-${r.request_id ?? ""}`}>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(r.request_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {r.method} {r.path}
                    </TableCell>
                    <TableCell>
                      <Badge variant={r.status_code >= 500 ? "destructive" : "secondary"}>
                        {r.status_code}
                      </Badge>
                    </TableCell>
                    <TableCell>{r.total_ms}ms</TableCell>
                    <TableCell>{r.db_total_ms}ms</TableCell>
                    <TableCell>{r.db_query_count}</TableCell>
                    <TableCell className="font-mono text-xs">{r.request_id || "-"}</TableCell>
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

