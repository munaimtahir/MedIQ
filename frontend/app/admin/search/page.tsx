"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { ErrorState } from "@/components/status/ErrorState";
import { SearchOpsCard } from "@/components/admin/learningOps/SearchOpsCard";
import { useSearchRuntime } from "@/lib/hooks/useLearningOps";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import { Database, Search, AlertTriangle, CheckCircle2, XCircle, RefreshCw } from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";

export default function SearchOpsPage() {
  const searchRuntimeQuery = useSearchRuntime();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await searchRuntimeQuery.refetch();
    } finally {
      setIsRefreshing(false);
    }
  };

  const status = searchRuntimeQuery.data;
  const loading = searchRuntimeQuery.loading || isRefreshing;
  const error = searchRuntimeQuery.error;
  const isFrozen = false; // Search runtime is independent of freeze_updates

  if (loading && !status) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Search Operations</h1>
            <p className="text-muted-foreground">Elasticsearch runtime and indexing status</p>
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
            <h1 className="text-3xl font-bold">Search Operations</h1>
            <p className="text-muted-foreground">Elasticsearch runtime and indexing status</p>
          </div>
        </div>
        <ErrorState
          variant="card"
          title="Failed to load search status"
          description={error.message || "An error occurred while loading search status."}
          actionLabel="Retry"
          onAction={handleRefresh}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Search Operations</h1>
          <p className="text-muted-foreground">Elasticsearch runtime and indexing status</p>
        </div>
        <Button variant="outline" onClick={handleRefresh} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Runtime Status Card */}
      <SearchOpsCard
        status={status}
        isFrozen={isFrozen}
        loading={loading}
        onRefresh={handleRefresh}
      />

      {/* Additional Status Cards */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Engine Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Engine Status
            </CardTitle>
            <CardDescription>Current search engine configuration</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Requested mode:</span>
              <Badge variant={status?.requested_mode === "elasticsearch" ? "default" : "secondary"}>
                {status?.requested_mode === "elasticsearch" ? "Elasticsearch" : "Postgres"}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Effective engine:</span>
              <Badge variant={status?.effective_engine === "elasticsearch" ? "default" : "secondary"}>
                {status?.effective_engine === "elasticsearch" ? "Elasticsearch" : "Postgres"}
              </Badge>
            </div>
            {status?.requested_mode === "elasticsearch" && status?.effective_engine === "postgres" && (
              <Alert variant="warning">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Requested Elasticsearch but it's unavailable. Using Postgres fallback.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Elasticsearch Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Elasticsearch Health
            </CardTitle>
            <CardDescription>Connection and availability status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Enabled:</span>
              <Badge variant={status?.enabled ? "default" : "outline"}>
                {status?.enabled ? "Yes" : "No"}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Reachable:</span>
              <div className="flex items-center gap-2">
                {status?.es_reachable ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <Badge variant="default" className="bg-green-600">UP</Badge>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-destructive" />
                    <Badge variant="destructive">DOWN</Badge>
                  </>
                )}
              </div>
            </div>
            {!status?.enabled && (
              <Alert>
                <AlertDescription>
                  Elasticsearch is disabled in environment configuration.
                </AlertDescription>
              </Alert>
            )}
            {status?.enabled && !status?.es_reachable && (
              <Alert variant="warning">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Elasticsearch is enabled but currently unreachable. Search will fallback to Postgres.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Readiness Checklist */}
      {status?.readiness && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className={`h-5 w-5 ${status.readiness.ready ? "text-green-600" : "text-destructive"}`} />
              Elasticsearch Readiness
            </CardTitle>
            <CardDescription>
              All checks must pass for Elasticsearch to be used (shadow gate)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Overall Status:</span>
              <Badge
                variant={status.readiness.ready ? "default" : "destructive"}
                className={status.readiness.ready ? "bg-green-600" : ""}
              >
                {status.readiness.ready ? "READY" : "NOT READY"}
              </Badge>
            </div>

            {status.readiness.blocking_reasons.length > 0 && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-1">
                    <div className="font-medium">Blocking Reasons:</div>
                    <ul className="list-disc list-inside text-sm space-y-0.5">
                      {status.readiness.blocking_reasons.map((reason, idx) => (
                        <li key={idx}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            <div className="space-y-3">
              <div className="text-sm font-medium">Readiness Checks:</div>
              {Object.entries(status.readiness.checks).map(([checkName, check]) => (
                <div key={checkName} className="flex items-start justify-between border-b pb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      {check.ok ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-destructive flex-shrink-0" />
                      )}
                      <span className="text-sm font-medium capitalize">
                        {checkName.replace(/_/g, " ")}
                      </span>
                    </div>
                    {Object.keys(check.details).length > 0 && (
                      <div className="ml-6 mt-1 text-xs text-muted-foreground">
                        {Object.entries(check.details).map(([key, value]) => (
                          <div key={key}>
                            {key}: {String(value)}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <Badge variant={check.ok ? "default" : "destructive"} className={check.ok ? "bg-green-600" : ""}>
                    {check.ok ? "PASS" : "FAIL"}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Last Switch Info */}
      {status?.last_switch && (
        <Card>
          <CardHeader>
            <CardTitle>Last Switch</CardTitle>
            <CardDescription>Most recent search engine mode change</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="text-sm">
              <span className="text-muted-foreground">When: </span>
              {formatDistanceToNow(new Date(status.last_switch.at), { addSuffix: true })}
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">By: </span>
              {status.last_switch.by}
            </div>
            {status.last_switch.reason && (
              <div className="text-sm">
                <span className="text-muted-foreground">Reason: </span>
                {status.last_switch.reason}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
