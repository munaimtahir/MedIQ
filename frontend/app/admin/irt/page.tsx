"use client";

import { useState, useCallback, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PoliceConfirmModal } from "@/components/admin/learningOps/PoliceConfirmModal";
import { JsonViewer } from "@/components/shared/JsonViewer";
import { StatusPill } from "@/components/shared/StatusPill";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import {
  Beaker,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Eye,
  RefreshCw,
  Download,
  ExternalLink,
} from "lucide-react";
import { notify } from "@/lib/notify";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import { useRuntime, useIrtStatus, useIrtRuns } from "@/lib/hooks/useLearningOps";
import { formatDistanceToNow } from "@/lib/dateUtils";
import type { IrtStatus, IrtRun, RuntimeStatus } from "@/lib/api/adminLearningOps";

export default function IrtOpsPage() {
  const [selectedRun, setSelectedRun] = useState<IrtRun | null>(null);
  const [showRunDetails, setShowRunDetails] = useState(false);
  const [showActivate, setShowActivate] = useState(false);
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [showEvaluate, setShowEvaluate] = useState(false);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runs, setRuns] = useState<IrtRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [runsError, setRunsError] = useState<Error | null>(null);

  const runtimeQuery = useRuntime();
  const irtStatusQuery = useIrtStatus();
  const irtRunsQuery = useIrtRuns();

  const runtime = runtimeQuery.data;
  const status = irtStatusQuery.data;
  const lastRun = irtRunsQuery.data?.[0] || null;

  const isFrozen = runtime?.config.safe_mode.freeze_updates || false;
  const runtimeOverride = (runtime?.config.overrides.difficulty as "v0" | "shadow" | "v1") || "shadow";
  const isActive = status?.flags.active || false;
  const eligible = status?.latest_decision?.eligible ?? false;

  // Load all runs for the table
  const loadRuns = useCallback(async () => {
    setRunsLoading(true);
    setRunsError(null);
    try {
      const data = await adminLearningOpsAPI.fetchIrtRuns({ limit: 50 });
      setRuns(data);
    } catch (err) {
      setRunsError(err instanceof Error ? err : new Error("Failed to load runs"));
    } finally {
      setRunsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const handleRefresh = useCallback(() => {
    runtimeQuery.refetch();
    irtStatusQuery.refetch();
    irtRunsQuery.refetch();
    loadRuns();
  }, [runtimeQuery, irtStatusQuery, irtRunsQuery, loadRuns]);

  const handleEvaluate = async () => {
    if (!lastRun?.id) {
      notify.error("No run available", "Create a calibration run first");
      return;
    }
    try {
      await adminLearningOpsAPI.evaluateIrtEligibility({ run_id: lastRun.id });
      notify.success("Eligibility evaluated", "Check the status for gate results");
      handleRefresh();
    } catch (error) {
      notify.error("Evaluation failed", error instanceof Error ? error.message : "Unknown error");
    }
  };

  const handleActivate = async () => {
    if (!lastRun?.id) {
      notify.error("No run available", "Create a calibration run first");
      return;
    }
    setIsSubmitting(true);
    try {
      await adminLearningOpsAPI.activateIrt({
        run_id: lastRun.id,
        scope: "selection_only",
        model_type: lastRun.model_type || "IRT_2PL",
        reason,
        confirmation_phrase: "ACTIVATE IRT",
      });
      notify.success("IRT activated", "IRT is now active for student-facing operations");
      setShowActivate(false);
      setReason("");
      handleRefresh();
    } catch (error) {
      notify.error("Activation failed", error instanceof Error ? error.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeactivate = async () => {
    setIsSubmitting(true);
    try {
      await adminLearningOpsAPI.deactivateIrt({
        reason,
        confirmation_phrase: "DEACTIVATE IRT",
      });
      notify.success("IRT deactivated", "IRT is now in shadow mode");
      setShowDeactivate(false);
      setReason("");
      handleRefresh();
    } catch (error) {
      notify.error("Deactivation failed", error instanceof Error ? error.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleViewRun = async (runId: string) => {
    try {
      const response = await fetch(`/api/admin/irt/runs/${runId}`);
      if (!response.ok) throw new Error("Failed to load run details");
      const data = await response.json();
      setSelectedRun(data.run || data);
      setShowRunDetails(true);
    } catch (err) {
      notify.error("Failed to load run", err instanceof Error ? err.message : "Unknown error");
    }
  };

  const loading = runtimeQuery.loading || irtStatusQuery.loading || irtRunsQuery.loading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">IRT Ops</h1>
        <p className="text-muted-foreground">Shadow calibration runs, eligibility, activation control</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <StatusPill status={runtimeOverride.toUpperCase()} label={`Runtime: ${runtimeOverride}`} />
          <StatusPill status={isActive ? "ACTIVE" : "SHADOW"} />
          <StatusPill status={isFrozen ? "FROZEN" : "ACTIVE"} label={`Freeze: ${isFrozen ? "ON" : "OFF"}`} />
          {lastRun && (
            <StatusPill
              status={lastRun.status === "DONE" ? "UP" : "DOWN"}
              label={`Last run: ${lastRun.status}`}
            />
          )}
        </div>
      </div>

      {/* Card A: Current Status */}
      <Card>
        <CardHeader>
          <CardTitle>Current Status</CardTitle>
          <CardDescription>IRT activation status and eligibility</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="space-y-2">
              <div className="h-4 w-32 animate-pulse rounded bg-muted" />
              <div className="h-4 w-48 animate-pulse rounded bg-muted" />
            </div>
          ) : status ? (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm text-muted-foreground">Last run ID:</span>
                  <p className="font-mono text-sm">{status.latest_decision.run_id || "N/A"}</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Last run time:</span>
                  <p className="text-sm">
                    {status.latest_decision.created_at
                      ? formatDistanceToNow(new Date(status.latest_decision.created_at), { addSuffix: true })
                      : "Never"}
                  </p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Status:</span>
                  <div className="mt-1">
                    <StatusPill status={isActive ? "ACTIVE" : "SHADOW"} />
                  </div>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Eligibility:</span>
                  <div className="mt-1 flex items-center gap-2">
                    {eligible ? (
                      <>
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                        <Badge variant="default" className="bg-green-600">Eligible</Badge>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-4 w-4 text-destructive" />
                        <Badge variant="destructive">Not eligible</Badge>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {status.latest_decision && !eligible && (
                <Alert variant="warning">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    Activation requires all eligibility gates to pass. Check gate results for details.
                  </AlertDescription>
                </Alert>
              )}

              {isFrozen && (
                <Alert variant="warning">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    Freeze mode is enabled. Activation/deactivation actions are disabled.
                  </AlertDescription>
                </Alert>
              )}

              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleEvaluate}
                  disabled={loading || !lastRun?.id}
                >
                  Evaluate Eligibility
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => setShowActivate(true)}
                  disabled={loading || isFrozen || !eligible || isActive}
                >
                  Activate
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setShowDeactivate(true)}
                  disabled={loading || isFrozen || !isActive}
                >
                  Deactivate
                </Button>
                {isFrozen && (
                  <span className="text-xs text-muted-foreground self-center">
                    Actions disabled: freeze_updates is enabled
                  </span>
                )}
              </div>
            </>
          ) : (
            <ErrorState
              title="Failed to load status"
              description="Unable to fetch IRT status. Please try again."
              onAction={handleRefresh}
              variant="card"
            />
          )}
        </CardContent>
      </Card>

      {/* Card B: Calibration Runs */}
      <Card>
        <CardHeader>
          <CardTitle>Calibration Runs</CardTitle>
          <CardDescription>History of IRT calibration runs</CardDescription>
        </CardHeader>
        <CardContent>
          {runsLoading ? (
            <SkeletonTable rows={5} cols={5} />
          ) : runsError ? (
            <ErrorState
              title="Failed to load runs"
              description={runsError.message}
              onAction={loadRuns}
              variant="card"
            />
          ) : runs.length === 0 ? (
            <EmptyState
              title="No runs found"
              description="Create a calibration run to get started"
              variant="card"
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Started</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Metrics</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={run.id}>
                    <TableCell>
                      {run.started_at
                        ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true })
                        : "Not started"}
                    </TableCell>
                    <TableCell>
                      <StatusPill
                        status={run.status === "DONE" ? "UP" : run.status === "FAILED" ? "DOWN" : "SHADOW"}
                        label={run.status}
                      />
                    </TableCell>
                    <TableCell className="font-mono text-sm">{run.model_type}</TableCell>
                    <TableCell>
                      {run.metrics ? (
                        <span className="text-xs text-muted-foreground">
                          {Object.keys(run.metrics).length} metrics
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">N/A</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewRun(run.id)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        {run.metrics && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const blob = new Blob([JSON.stringify(run.metrics, null, 2)], {
                                type: "application/json",
                              });
                              const url = URL.createObjectURL(blob);
                              const a = document.createElement("a");
                              a.href = url;
                              a.download = `irt-run-${run.id}-metrics.json`;
                              a.click();
                            }}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Card C: Compare to Elo (Placeholder) */}
      <Card>
        <CardHeader>
          <CardTitle>Compare to Elo</CardTitle>
          <CardDescription>Correlation between IRT difficulty and Elo difficulty</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Coming soon"
            description="Comparison metrics will be available here"
            variant="card"
          />
        </CardContent>
      </Card>

      {/* Card D: Audit Trail */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Trail</CardTitle>
          <CardDescription>Activation and deactivation events</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <SkeletonTable rows={3} cols={4} />
          ) : status?.last_events && status.last_events.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Reason</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {status.last_events.map((event, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <Badge variant={event.event_type === "activate" ? "default" : "destructive"}>
                        {event.event_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{event.created_by_user_id}</TableCell>
                    <TableCell>
                      {formatDistanceToNow(new Date(event.created_at), { addSuffix: true })}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {event.reason || "N/A"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyState title="No events found" variant="card" />
          )}
        </CardContent>
      </Card>

      {/* Run Details Dialog */}
      <Dialog open={showRunDetails} onOpenChange={setShowRunDetails}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Run Details</DialogTitle>
            <DialogDescription>Detailed information about this calibration run</DialogDescription>
          </DialogHeader>
          {selectedRun && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm font-semibold">Status:</span>
                  <div className="mt-1">
                    <StatusPill status={selectedRun.status} />
                  </div>
                </div>
                <div>
                  <span className="text-sm font-semibold">Model Type:</span>
                  <p className="font-mono text-sm">{selectedRun.model_type}</p>
                </div>
                <div>
                  <span className="text-sm font-semibold">Started:</span>
                  <p className="text-sm">
                    {selectedRun.started_at
                      ? new Date(selectedRun.started_at).toLocaleString()
                      : "N/A"}
                  </p>
                </div>
                <div>
                  <span className="text-sm font-semibold">Finished:</span>
                  <p className="text-sm">
                    {selectedRun.finished_at
                      ? new Date(selectedRun.finished_at).toLocaleString()
                      : "N/A"}
                  </p>
                </div>
              </div>

              {selectedRun.error && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    <pre className="whitespace-pre-wrap text-xs">{selectedRun.error}</pre>
                  </AlertDescription>
                </Alert>
              )}

              {selectedRun.metrics && (
                <JsonViewer data={selectedRun.metrics} title="Metrics" defaultExpanded />
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Activate Modal */}
      <PoliceConfirmModal
        open={showActivate}
        onOpenChange={setShowActivate}
        actionTitle="Activate IRT"
        requiredPhrase="ACTIVATE IRT"
        reason={reason}
        onReasonChange={setReason}
        onConfirm={handleActivate}
        isSubmitting={isSubmitting}
        variant="default"
      />

      {/* Deactivate Modal */}
      <PoliceConfirmModal
        open={showDeactivate}
        onOpenChange={setShowDeactivate}
        actionTitle="Deactivate IRT"
        requiredPhrase="DEACTIVATE IRT"
        reason={reason}
        onReasonChange={setReason}
        onConfirm={handleDeactivate}
        isSubmitting={isSubmitting}
        variant="destructive"
      />
    </div>
  );
}
