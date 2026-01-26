"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { ErrorState } from "@/components/status/ErrorState";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface MetricPoint {
  date: string;
  value: number;
  run_id: string;
  suite_name: string;
  suite_versions: Record<string, string>;
}

interface MetricTimeseries {
  metric: string;
  window: string;
  points: MetricPoint[];
}

export default function EvaluationMetricsPage() {
  const [data, setData] = useState<MetricTimeseries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [selectedMetric, setSelectedMetric] = useState("logloss");
  const [selectedWindow, setSelectedWindow] = useState("30d");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/v1/admin/evaluation/metrics/timeseries?metric=${selectedMetric}&window=${selectedWindow}`
      );
      if (!response.ok) throw new Error("Failed to load metrics timeseries");
      const data = await response.json();
      setData(data);
    } catch (err) {
      console.error("Failed to load metrics timeseries:", err);
      setError(err instanceof Error ? err : new Error("Failed to load metrics timeseries"));
    } finally {
      setLoading(false);
    }
  }, [selectedMetric, selectedWindow]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">Evaluation Metrics</h1>
        <SkeletonTable rows={5} cols={3} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">Evaluation Metrics</h1>
        <ErrorState
          title="Failed to load metrics"
          description={error?.message}
          onAction={loadData}
        />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  // Prepare chart data
  const chartData = data.points.map((p) => ({
    date: p.date,
    value: p.value,
    suite: p.suite_name,
  }));

  return (
    <div className="container mx-auto py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Evaluation Metrics</h1>
        <p className="text-muted-foreground mt-2">Shadow evaluation dashboard - metrics over time</p>
      </div>

      {/* Controls */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-4">
          <div className="w-48">
            <label className="text-sm font-medium mb-2 block">Metric</label>
            <Select value={selectedMetric} onValueChange={setSelectedMetric}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="logloss">Log Loss</SelectItem>
                <SelectItem value="brier">Brier Score</SelectItem>
                <SelectItem value="ece">ECE (Expected Calibration Error)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="w-48">
            <label className="text-sm font-medium mb-2 block">Time Window</label>
            <Select value={selectedWindow} onValueChange={setSelectedWindow}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="90d">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Chart */}
      <Card>
        <CardHeader>
          <CardTitle>{selectedMetric.toUpperCase()} Over Time</CardTitle>
          <CardDescription>Time-series of {selectedMetric} metric</CardDescription>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No data available</div>
          ) : (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#8884d8" name={selectedMetric} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
