"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface TagQualityDebt {
  total_debt_last_7d: number;
  by_reason: Record<string, number>;
  top_themes: Array<{
    theme_id: number;
    theme_name: string;
    count: number;
  }>;
  top_questions: Array<{
    question_id: string;
    count: number;
  }>;
}

export function TagQualityDebtCard() {
  const [data, setData] = useState<TagQualityDebt | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/admin/tag-quality");
      if (!response.ok) throw new Error("Failed to load tag quality debt");
      const data = await response.json();
      setData(data);
    } catch (err) {
      console.error("Failed to load tag quality debt:", err);
      setError(err instanceof Error ? err : new Error("Failed to load tag quality debt"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Tag Quality Debt</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Tag Quality Debt</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Failed to load data</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-warning" />
          Tag Quality Debt
        </CardTitle>
        <CardDescription>BKT Q-matrix hygiene (last 7 days)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <div className="text-2xl font-bold">{data.total_debt_last_7d}</div>
            <p className="text-xs text-muted-foreground">Total debt events</p>
          </div>

          {Object.keys(data.by_reason).length > 0 && (
            <div>
              <p className="text-sm font-medium mb-2">By Reason</p>
              <div className="space-y-1">
                {Object.entries(data.by_reason).map(([reason, count]) => (
                  <div key={reason} className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{reason}</span>
                    <Badge variant="secondary">{count}</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.top_themes.length > 0 && (
            <div>
              <p className="text-sm font-medium mb-2">Top Themes</p>
              <div className="space-y-1">
                {data.top_themes.slice(0, 5).map((theme) => (
                  <div key={theme.theme_id} className="flex justify-between text-sm">
                    <span className="text-muted-foreground truncate">{theme.theme_name}</span>
                    <Badge variant="outline">{theme.count}</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
