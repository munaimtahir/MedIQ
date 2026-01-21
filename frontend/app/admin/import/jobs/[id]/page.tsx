"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { adminImportApi } from "@/lib/admin/importApi";
import type { ImportJobOut } from "@/lib/types/import";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { ErrorState } from "@/components/status/ErrorState";
import { notify } from "@/lib/notify";
import { ArrowLeft, Download, CheckCircle, XCircle, AlertCircle, FileText } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const STATUS_COLORS = {
  PENDING: "bg-gray-500",
  RUNNING: "bg-blue-500",
  COMPLETED: "bg-green-500",
  FAILED: "bg-red-500",
};

export default function ImportJobPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [job, setJob] = useState<ImportJobOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadJob = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminImportApi.getJob(jobId);
      setJob(data);
    } catch (err) {
      console.error("Failed to load job:", err);
      setError(err instanceof Error ? err : new Error("Failed to load job"));
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    loadJob();
  }, [loadJob]);

  const handleDownloadRejected = async () => {
    if (!job) return;

    try {
      const blob = await adminImportApi.downloadRejectedCsv(jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `job_${jobId}_rejected.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      notify.success("Downloaded", "Rejected rows CSV downloaded");
    } catch (err) {
      notify.error(
        "Download Failed",
        err instanceof Error ? err.message : "Failed to download rejected rows",
      );
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold">Loading...</h1>
        </div>
        <SkeletonTable rows={6} cols={2} />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold">Error</h1>
        </div>
        <ErrorState
          variant="page"
          title="Failed to load job"
          description={error?.message || "Job not found"}
          actionLabel="Retry"
          onAction={loadJob}
        />
      </div>
    );
  }

  const acceptanceRate =
    job.total_rows > 0 ? ((job.accepted_rows / job.total_rows) * 100).toFixed(1) : 0;
  const errorCounts = job.summary_json?.error_counts || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">Import Job Results</h1>
              <Badge className={STATUS_COLORS[job.status]}>{job.status}</Badge>
              {job.dry_run && <Badge variant="outline">DRY RUN</Badge>}
            </div>
            <p className="text-sm text-muted-foreground">Job ID: {job.id}</p>
          </div>
        </div>
        {job.rejected_rows > 0 && (
          <Button onClick={handleDownloadRejected}>
            <Download className="mr-2 h-4 w-4" />
            Download Rejected Rows
          </Button>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Rows</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-muted-foreground" />
              <span className="text-2xl font-bold">{job.total_rows}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Accepted</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="text-2xl font-bold text-green-600">{job.accepted_rows}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Rejected</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-500" />
              <span className="text-2xl font-bold text-red-600">{job.rejected_rows}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Success Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <span className="text-2xl font-bold">{acceptanceRate}%</span>
              <Progress value={Number(acceptanceRate)} className="h-2" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Job Details */}
      <Card>
        <CardHeader>
          <CardTitle>Job Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Filename</p>
              <p className="font-medium">{job.filename}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Schema</p>
              <p className="font-medium">
                {job.schema_name} v{job.schema_version}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Started</p>
              <p className="font-medium">
                {job.started_at
                  ? formatDistanceToNow(new Date(job.started_at), { addSuffix: true })
                  : "—"}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Completed</p>
              <p className="font-medium">
                {job.completed_at
                  ? formatDistanceToNow(new Date(job.completed_at), { addSuffix: true })
                  : "—"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Breakdown */}
      {Object.keys(errorCounts).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Error Breakdown</CardTitle>
            <CardDescription>Number of rows rejected by error type</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(errorCounts).map(([code, count]) => (
                <div key={code} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-yellow-500" />
                    <span className="font-mono text-sm">{code}</span>
                  </div>
                  <Badge variant="outline">{count} rows</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Message */}
      {job.status === "FAILED" && job.error_message && (
        <Card className="border-red-200 bg-red-50 dark:bg-red-950">
          <CardHeader>
            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-500" />
              <CardTitle className="text-red-900 dark:text-red-100">Job Failed</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-red-800 dark:text-red-200">{job.error_message}</p>
          </CardContent>
        </Card>
      )}

      {/* Next Steps */}
      {job.status === "COMPLETED" && !job.dry_run && job.accepted_rows > 0 && (
        <Card className="bg-green-50 dark:bg-green-950">
          <CardHeader>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <CardTitle className="text-base">Import Complete</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm">
              {job.accepted_rows} questions have been imported as <strong>DRAFT</strong> status.
            </p>
            <Button
              variant="outline"
              onClick={() => router.push("/admin/questions?status=DRAFT")}
              className="mt-2"
            >
              View Imported Questions
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
