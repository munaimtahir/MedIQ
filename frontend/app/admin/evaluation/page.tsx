"use client";

import { useCallback, useEffect, useState } from "react";
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
import { Play, Eye, Clock, CheckCircle, XCircle, Loader } from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";

interface EvalRun {
  id: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  status: string;
  suite_name: string;
  suite_versions: Record<string, string>;
  dataset_spec: Record<string, any>;
  config: Record<string, any>;
  git_sha: string | null;
  random_seed: number | null;
  notes: string | null;
  error: string | null;
}

interface EvalRunDetail extends EvalRun {
  metrics: Array<{
    id: string;
    metric_name: string;
    scope_type: string;
    scope_id: string | null;
    value: number;
    n: number;
    extra: Record<string, any> | null;
  }>;
  artifacts: Array<{
    id: string;
    type: string;
    path: string;
    created_at: string;
  }>;
}

export default function EvaluationPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [selectedRun, setSelectedRun] = useState<EvalRunDetail | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/admin/eval/runs?limit=50");
      if (!response.ok) throw new Error("Failed to load evaluation runs");
      const data = await response.json();
      setRuns(data);
    } catch (err) {
      console.error("Failed to load evaluation runs:", err);
      setError(err instanceof Error ? err : new Error("Failed to load evaluation runs"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const handleViewDetails = async (runId: string) => {
    try {
      const response = await fetch(`/api/v1/admin/eval/runs/${runId}`);
      if (!response.ok) throw new Error("Failed to load run details");
      const data = await response.json();
      setSelectedRun(data.run);
      setDetailModalOpen(true);
    } catch (err) {
      console.error("Failed to load run details:", err);
    }
  };

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
        <h1 className="text-3xl font-bold mb-6">Evaluation Harness</h1>
        <SkeletonTable rows={5} cols={6} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">Evaluation Harness</h1>
        <ErrorState
          title="Failed to load runs"
          description={error?.message}
          onAction={loadRuns}
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Evaluation Harness</h1>
          <p className="text-muted-foreground mt-2">
            Offline replay and metrics for learning algorithms
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Evaluation Runs</CardTitle>
          <CardDescription>List of evaluation runs with their status and metrics</CardDescription>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <EmptyState
              title="No evaluation runs"
              description="Create your first evaluation run using the CLI or API"
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Suite</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={run.id}>
                    <TableCell className="font-medium">{run.suite_name}</TableCell>
                    <TableCell>{getStatusBadge(run.status)}</TableCell>
                    <TableCell>
                      {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                    </TableCell>
                    <TableCell>
                      {run.started_at && run.finished_at
                        ? `${Math.round(
                            (new Date(run.finished_at).getTime() -
                              new Date(run.started_at).getTime()) /
                              1000
                          )}s`
                        : "-"}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewDetails(run.id)}
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {selectedRun && detailModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle>Run Details</CardTitle>
                  <CardDescription>{selectedRun.suite_name}</CardDescription>
                </div>
                <Button variant="ghost" onClick={() => setDetailModalOpen(false)}>
                  Close
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-semibold mb-2">Status</h3>
                {getStatusBadge(selectedRun.status)}
              </div>

              {selectedRun.metrics && selectedRun.metrics.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">Metrics</h3>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Metric</TableHead>
                        <TableHead>Value</TableHead>
                        <TableHead>N</TableHead>
                        <TableHead>Scope</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {selectedRun.metrics.map((metric) => (
                        <TableRow key={metric.id}>
                          <TableCell className="font-medium">{metric.metric_name}</TableCell>
                          <TableCell>{metric.value.toFixed(6)}</TableCell>
                          <TableCell>{metric.n}</TableCell>
                          <TableCell>
                            {metric.scope_type}
                            {metric.scope_id && `: ${metric.scope_id}`}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {selectedRun.error && (
                <div>
                  <h3 className="font-semibold mb-2 text-destructive">Error</h3>
                  <pre className="bg-muted p-4 rounded text-sm overflow-x-auto">
                    {selectedRun.error}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
