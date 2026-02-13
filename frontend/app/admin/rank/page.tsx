"use client";

import { useState, useCallback, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Eye,
  RefreshCw,
  User,
} from "lucide-react";
import { notify } from "@/lib/notify";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import { useRuntime, useRankStatus } from "@/lib/hooks/useLearningOps";
import { formatDistanceToNow } from "@/lib/dateUtils";
import type { RankStatus, RankRun, RuntimeStatus } from "@/lib/api/adminLearningOps";

interface RankSnapshot {
  id: string;
  user_id: string;
  cohort_key: string;
  snapshot_date: string;
  percentile: number | null;
  band: string | null;
  status: string;
  theta_proxy: number | null;
  insufficient_data_reason?: string;
}

export default function RankOpsPage() {
  const [cohortKey, setCohortKey] = useState("year:1");
  const [runs, setRuns] = useState<RankRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [runsError, setRunsError] = useState<Error | null>(null);
  const [selectedRun, setSelectedRun] = useState<RankRun | null>(null);
  const [showRunDetails, setShowRunDetails] = useState(false);
  const [showActivate, setShowActivate] = useState(false);
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [showShadowRun, setShowShadowRun] = useState(false);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Snapshot explorer
  const [snapshotUserId, setSnapshotUserId] = useState("");
  const [snapshotDays, setSnapshotDays] = useState("30");
  const [snapshots, setSnapshots] = useState<RankSnapshot[]>([]);
  const [snapshotsLoading, setSnapshotsLoading] = useState(false);
  const [snapshotsError, setSnapshotsError] = useState<Error | null>(null);

  const runtimeQuery = useRuntime();
  const rankStatusQuery = useRankStatus(cohortKey);

  const runtime = runtimeQuery.data;
  const status = rankStatusQuery.data;

  const isFrozen = runtime?.config.safe_mode.freeze_updates || false;
  const runtimeOverride = (runtime?.config.overrides.rank as "v0" | "shadow" | "v1") || "shadow";
  const mode = status?.mode || "shadow";
  const eligible = status?.eligible || false;

  // Load runs
  const loadRuns = useCallback(async () => {
    setRunsLoading(true);
    setRunsError(null);
    try {
      const data = await adminLearningOpsAPI.fetchRankRuns({ cohort_key: cohortKey, limit: 50 });
      setRuns(data);
    } catch (err) {
      setRunsError(err instanceof Error ? err : new Error("Failed to load runs"));
    } finally {
      setRunsLoading(false);
    }
  }, [cohortKey]);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const handleRefresh = useCallback(() => {
    runtimeQuery.refetch();
    rankStatusQuery.refetch();
    loadRuns();
  }, [runtimeQuery, rankStatusQuery, loadRuns]);

  const handleActivate = async () => {
    setIsSubmitting(true);
    try {
      await adminLearningOpsAPI.activateRank({
        cohort_key: cohortKey,
        reason,
        confirmation_phrase: "ACTIVATE RANK",
      });
      notify.success("Rank activated", "Rank is now active for analytics");
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
      await adminLearningOpsAPI.deactivateRank({
        reason,
        confirmation_phrase: "DEACTIVATE RANK",
      });
      notify.success("Rank deactivated", "Rank is now in shadow mode");
      setShowDeactivate(false);
      setReason("");
      handleRefresh();
    } catch (error) {
      notify.error("Deactivation failed", error instanceof Error ? error.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRunShadow = async () => {
    setIsSubmitting(true);
    try {
      await adminLearningOpsAPI.createRankRun({
        cohort_key: cohortKey,
      });
      notify.success("Shadow run started", "Rank shadow run has been queued");
      setShowShadowRun(false);
      handleRefresh();
    } catch (error) {
      notify.error("Run failed", error instanceof Error ? error.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleViewRun = async (runId: string) => {
    try {
      const response = await fetch(`/api/admin/rank/runs/${runId}`);
      if (!response.ok) throw new Error("Failed to load run details");
      const data = await response.json();
      setSelectedRun(data.run || data);
      setShowRunDetails(true);
    } catch (err) {
      notify.error("Failed to load run", err instanceof Error ? err.message : "Unknown error");
    }
  };

  const handleLoadSnapshots = async () => {
    if (!snapshotUserId.trim()) {
      notify.error("User ID required", "Please enter a user ID");
      return;
    }
    setSnapshotsLoading(true);
    setSnapshotsError(null);
    try {
      const response = await fetch(
        `/api/admin/rank/snapshots?user_id=${encodeURIComponent(snapshotUserId)}&cohort_key=${encodeURIComponent(cohortKey)}&days=${snapshotDays}`,
      );
      if (!response.ok) throw new Error("Failed to load snapshots");
      const data = await response.json();
      setSnapshots(Array.isArray(data) ? data : data.snapshots || []);
    } catch (err) {
      setSnapshotsError(err instanceof Error ? err : new Error("Failed to load snapshots"));
    } finally {
      setSnapshotsLoading(false);
    }
  };

  const loading = runtimeQuery.loading || rankStatusQuery.loading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Rank Ops</h1>
        <p className="text-muted-foreground">Quantile-based percentile estimates and activation control</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <StatusPill status={runtimeOverride.toUpperCase()} label={`Runtime: ${runtimeOverride}`} />
          <StatusPill status={isFrozen ? "FROZEN" : "ACTIVE"} label={`Freeze: ${isFrozen ? "ON" : "OFF"}`} />
          <div className="flex items-center gap-2">
            <Label htmlFor="cohort-select" className="text-sm">Cohort:</Label>
            <Select value={cohortKey} onValueChange={setCohortKey}>
              <SelectTrigger id="cohort-select" className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="year:1">Year 1</SelectItem>
                <SelectItem value="year:2">Year 2</SelectItem>
                <SelectItem value="year:3">Year 3</SelectItem>
                <SelectItem value="year:4">Year 4</SelectItem>
                <SelectItem value="year:5">Year 5</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Card A: Cohort Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Cohort Overview</CardTitle>
          <CardDescription>Status and metrics for {cohortKey}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="space-y-2">
              <div className="h-4 w-32 animate-pulse rounded bg-muted" />
              <div className="h-4 w-48 animate-pulse rounded bg-muted" />
            </div>
          ) : status ? (
            <>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <span className="text-sm text-muted-foreground">Coverage:</span>
                  <p className="text-lg font-semibold">
                    {status.latest_run?.coverage !== null
                      ? `${((status.latest_run?.coverage ?? 0) * 100).toFixed(1)}%`
                      : "N/A"}
                  </p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Stability:</span>
                  <p className="text-lg font-semibold">
                    {status.latest_run?.stability !== null
                      ? (status.latest_run?.stability ?? 0).toFixed(3)
                      : "N/A"}
                  </p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Last computed:</span>
                  <p className="text-sm">
                    {status.latest_run?.created_at
                      ? formatDistanceToNow(new Date(status.latest_run.created_at), { addSuffix: true })
                      : "Never"}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Eligibility:</span>
                  <div className="flex items-center gap-2">
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
                {status.reasons && status.reasons.length > 0 && (
                  <Alert variant="warning">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription className="text-xs">
                      {status.reasons.join(", ")}
                    </AlertDescription>
                  </Alert>
                )}
              </div>

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
                  onClick={() => setShowShadowRun(true)}
                  disabled={loading || isFrozen}
                >
                  Run Shadow
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => setShowActivate(true)}
                  disabled={loading || isFrozen || !eligible || mode === "v1"}
                >
                  Activate
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setShowDeactivate(true)}
                  disabled={loading || isFrozen || mode !== "v1"}
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
              description="Unable to fetch Rank status. Please try again."
              onAction={handleRefresh}
              variant="card"
            />
          )}
        </CardContent>
      </Card>

      {/* Card B: Recent Runs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Runs</CardTitle>
          <CardDescription>Rank model runs for {cohortKey}</CardDescription>
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
              description="Create a shadow run to get started"
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
                    <TableCell className="font-mono text-sm">{run.model_version}</TableCell>
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
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewRun(run.id)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Card C: Snapshot Explorer */}
      <Card>
        <CardHeader>
          <CardTitle>Snapshot Explorer</CardTitle>
          <CardDescription>View rank snapshots for a specific user</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <div className="flex-1">
              <Label htmlFor="user-id">User ID</Label>
              <Input
                id="user-id"
                value={snapshotUserId}
                onChange={(e) => setSnapshotUserId(e.target.value)}
                placeholder="Enter user ID"
              />
            </div>
            <div className="w-24">
              <Label htmlFor="days">Days</Label>
              <Input
                id="days"
                type="number"
                value={snapshotDays}
                onChange={(e) => setSnapshotDays(e.target.value)}
                min="1"
                max="365"
              />
            </div>
            <div className="flex items-end">
              <Button onClick={handleLoadSnapshots} disabled={snapshotsLoading || !snapshotUserId.trim()}>
                <User className="mr-2 h-4 w-4" />
                Load
              </Button>
            </div>
          </div>

          {snapshotsLoading ? (
            <SkeletonTable rows={3} cols={5} />
          ) : snapshotsError ? (
            <ErrorState
              title="Failed to load snapshots"
              description={snapshotsError.message}
              onAction={handleLoadSnapshots}
              variant="card"
            />
          ) : snapshots.length === 0 && snapshotUserId ? (
            <EmptyState
              title="No snapshots found"
              description="No snapshots available for this user and time period"
              variant="card"
            />
          ) : snapshots.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Percentile</TableHead>
                  <TableHead>Band</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Theta Proxy</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {snapshots.map((snapshot) => (
                  <TableRow key={snapshot.id}>
                    <TableCell>{new Date(snapshot.snapshot_date).toLocaleDateString()}</TableCell>
                    <TableCell>
                      {snapshot.percentile !== null ? `${(snapshot.percentile * 100).toFixed(1)}%` : "N/A"}
                    </TableCell>
                    <TableCell>
                      {snapshot.band ? <Badge variant="outline">{snapshot.band}</Badge> : "N/A"}
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <StatusPill
                          status={snapshot.status === "ok" ? "UP" : "DOWN"}
                          label={snapshot.status}
                        />
                        {snapshot.status === "insufficient_data" && snapshot.insufficient_data_reason && (
                          <p className="text-xs text-muted-foreground">{snapshot.insufficient_data_reason}</p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {snapshot.theta_proxy !== null ? snapshot.theta_proxy.toFixed(3) : "N/A"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}
        </CardContent>
      </Card>

      {/* Card D: Audit Trail */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Trail</CardTitle>
          <CardDescription>Activation and deactivation events</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Coming soon"
            description="Audit trail will be available here"
            variant="card"
          />
        </CardContent>
      </Card>

      {/* Run Details Dialog */}
      <Dialog open={showRunDetails} onOpenChange={setShowRunDetails}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Run Details</DialogTitle>
            <DialogDescription>Detailed information about this rank run</DialogDescription>
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
                  <span className="text-sm font-semibold">Model Version:</span>
                  <p className="font-mono text-sm">{selectedRun.model_version}</p>
                </div>
                <div>
                  <span className="text-sm font-semibold">Started:</span>
                  <p className="text-sm">
                    {selectedRun.started_at ? new Date(selectedRun.started_at).toLocaleString() : "N/A"}
                  </p>
                </div>
                <div>
                  <span className="text-sm font-semibold">Finished:</span>
                  <p className="text-sm">
                    {selectedRun.finished_at ? new Date(selectedRun.finished_at).toLocaleString() : "N/A"}
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

      {/* Shadow Run Confirm */}
      <Dialog open={showShadowRun} onOpenChange={setShowShadowRun}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Run Shadow Rank</DialogTitle>
            <DialogDescription>Create a new shadow run for {cohortKey}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              This will queue a shadow run to compute rank predictions without affecting production.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowShadowRun(false)}>
                Cancel
              </Button>
              <Button onClick={handleRunShadow} disabled={isSubmitting}>
                {isSubmitting ? "Starting..." : "Run Shadow"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Activate Modal */}
      <PoliceConfirmModal
        open={showActivate}
        onOpenChange={setShowActivate}
        actionTitle="Activate Rank"
        requiredPhrase="ACTIVATE RANK"
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
        actionTitle="Deactivate Rank"
        requiredPhrase="DEACTIVATE RANK"
        reason={reason}
        onReasonChange={setReason}
        onConfirm={handleDeactivate}
        isSubmitting={isSubmitting}
        variant="destructive"
      />
    </div>
  );
}
