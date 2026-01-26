"use client";

import { useState, useEffect } from "react";
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
import { ErrorState } from "@/components/status/ErrorState";
import { RefreshCw, AlertTriangle, TrendingUp } from "lucide-react";
import { notify } from "@/lib/notify";

interface TagQualityDebt {
  total_debt_last_7d: number;
  by_reason: Record<string, number>;
  top_themes: Array<{ theme_id: number; theme_name: string; count: number }>;
  top_questions: Array<{ question_id: string; count: number }>;
}

export default function TagQualityPage() {
  const [data, setData] = useState<TagQualityDebt | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/tag-quality");
      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }
      const result = await response.json();
      setData(result);
    } catch (err) {
      const errObj = err instanceof Error ? err : new Error("Failed to load tag quality data");
      setError(errObj);
      notify.error("Failed to load tag quality", errObj.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading && !data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Tag Quality</h1>
            <p className="text-muted-foreground">Tag quality debt tracking and analysis</p>
          </div>
        </div>
        <SkeletonTable rows={5} cols={3} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Tag Quality</h1>
            <p className="text-muted-foreground">Tag quality debt tracking and analysis</p>
          </div>
        </div>
        <ErrorState
          variant="card"
          title="Failed to load tag quality data"
          description={error.message}
          actionLabel="Retry"
          onAction={fetchData}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Tag Quality</h1>
          <p className="text-muted-foreground">Tag quality debt tracking and analysis</p>
        </div>
        <Button variant="outline" onClick={fetchData} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Summary Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Summary (Last 7 Days)
          </CardTitle>
          <CardDescription>Total tag quality debt occurrences</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-4xl font-bold">{data?.total_debt_last_7d || 0}</div>
          <p className="text-sm text-muted-foreground mt-2">Total debt occurrences</p>
        </CardContent>
      </Card>

      {/* By Reason */}
      <Card>
        <CardHeader>
          <CardTitle>Debt by Reason</CardTitle>
          <CardDescription>Breakdown of debt occurrences by reason code</CardDescription>
        </CardHeader>
        <CardContent>
          {data && Object.keys(data.by_reason).length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Reason</TableHead>
                  <TableHead>Count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(data.by_reason)
                  .sort(([, a], [, b]) => b - a)
                  .map(([reason, count]) => (
                    <TableRow key={reason}>
                      <TableCell>
                        <Badge variant="outline">{reason}</Badge>
                      </TableCell>
                      <TableCell className="font-semibold">{count}</TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No debt data available</p>
          )}
        </CardContent>
      </Card>

      {/* Top Themes */}
      <Card>
        <CardHeader>
          <CardTitle>Top Themes with Debt</CardTitle>
          <CardDescription>Themes with the most tag quality debt</CardDescription>
        </CardHeader>
        <CardContent>
          {data && data.top_themes.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Theme</TableHead>
                  <TableHead>Count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.top_themes.map((theme) => (
                  <TableRow key={theme.theme_id}>
                    <TableCell>{theme.theme_name}</TableCell>
                    <TableCell className="font-semibold">{theme.count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No theme debt data available</p>
          )}
        </CardContent>
      </Card>

      {/* Top Questions */}
      <Card>
        <CardHeader>
          <CardTitle>Top Questions with Debt</CardTitle>
          <CardDescription>Questions with the most tag quality debt</CardDescription>
        </CardHeader>
        <CardContent>
          {data && data.top_questions.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Question ID</TableHead>
                  <TableHead>Count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.top_questions.map((question) => (
                  <TableRow key={question.question_id}>
                    <TableCell className="font-mono text-sm">{question.question_id}</TableCell>
                    <TableCell className="font-semibold">{question.count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No question debt data available</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
