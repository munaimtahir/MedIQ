"use client";

import { useState, useCallback, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
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
  DialogFooter,
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
  Network,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Plus,
  Edit,
  Trash2,
  User,
  Eye,
} from "lucide-react";
import { notify } from "@/lib/notify";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import { useRuntime, useGraphHealth } from "@/lib/hooks/useLearningOps";
import { formatDistanceToNow } from "@/lib/dateUtils";
import type { GraphHealth, GraphRunMetrics, RuntimeStatus } from "@/lib/api/adminLearningOps";

interface PrereqEdge {
  id: string;
  from_theme_id: number;
  to_theme_id: number;
  from_theme_name?: string;
  to_theme_name?: string;
  weight: number;
  source: string;
  active: boolean;
}

interface ShadowPlan {
  user_id: string;
  plan_date: string;
  plan_json: Record<string, unknown>;
}

export default function GraphRevisionOpsPage() {
  const [health, setHealth] = useState<GraphHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState<Error | null>(null);
  const [edges, setEdges] = useState<PrereqEdge[]>([]);
  const [edgesLoading, setEdgesLoading] = useState(true);
  const [edgesError, setEdgesError] = useState<Error | null>(null);
  const [runMetrics, setRunMetrics] = useState<GraphRunMetrics | null>(null);
  const [runMetricsLoading, setRunMetricsLoading] = useState(false);
  const [showSyncConfirm, setShowSyncConfirm] = useState(false);
  const [showActivate, setShowActivate] = useState(false);
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [showAddEdge, setShowAddEdge] = useState(false);
  const [showEditEdge, setShowEditEdge] = useState(false);
  const [selectedEdge, setSelectedEdge] = useState<PrereqEdge | null>(null);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  // Shadow plan explorer
  const [planUserId, setPlanUserId] = useState("");
  const [planDays, setPlanDays] = useState("30");
  const [shadowPlans, setShadowPlans] = useState<ShadowPlan[]>([]);
  const [plansLoading, setPlansLoading] = useState(false);
  const [plansError, setPlansError] = useState<Error | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<ShadowPlan | null>(null);
  const [showPlanDetails, setShowPlanDetails] = useState(false);

  // Edge form
  const [edgeForm, setEdgeForm] = useState({
    from_theme_id: "",
    to_theme_id: "",
    weight: "1.0",
    source: "manual",
  });

  const runtimeQuery = useRuntime();
  const graphHealthQuery = useGraphHealth();

  const runtime = runtimeQuery.data;
  const graphHealth = graphHealthQuery.data;

  const isFrozen = runtime?.config.safe_mode.freeze_updates || false;
  const runtimeOverride = (runtime?.config.overrides.graph_revision as "v0" | "shadow" | "v1") || "shadow";

  // Load health
  const loadHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await adminLearningOpsAPI.fetchGraphHealth();
      setHealth(data);
    } catch (err) {
      setHealthError(err instanceof Error ? err : new Error("Failed to load health"));
    } finally {
      setHealthLoading(false);
    }
  }, []);

  // Load edges
  const loadEdges = useCallback(async () => {
    setEdgesLoading(true);
    setEdgesError(null);
    try {
      const response = await fetch("/api/admin/graph-revision/edges");
      if (!response.ok) throw new Error("Failed to load edges");
      const data = await response.json();
      setEdges(Array.isArray(data) ? data : data.edges || []);
    } catch (err) {
      setEdgesError(err instanceof Error ? err : new Error("Failed to load edges"));
    } finally {
      setEdgesLoading(false);
    }
  }, []);

  // Load run metrics
  const loadRunMetrics = useCallback(async () => {
    setRunMetricsLoading(true);
    try {
      const data = await adminLearningOpsAPI.fetchGraphRunMetrics(30);
      setRunMetrics(data);
    } catch (err) {
      console.error("Failed to load run metrics:", err);
    } finally {
      setRunMetricsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
    loadEdges();
    loadRunMetrics();
  }, [loadHealth, loadEdges, loadRunMetrics]);

  const handleRefresh = useCallback(() => {
    runtimeQuery.refetch();
    graphHealthQuery.refetch();
    loadHealth();
    loadEdges();
    loadRunMetrics();
  }, [runtimeQuery, graphHealthQuery, loadHealth, loadEdges, loadRunMetrics]);

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await adminLearningOpsAPI.runGraphSync();
      notify.success("Sync triggered", "Neo4j sync job started");
      setShowSyncConfirm(false);
      handleRefresh();
    } catch (error) {
      notify.error("Sync failed", error instanceof Error ? error.message : "Unknown error");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleActivate = async () => {
    setIsSubmitting(true);
    try {
      await adminLearningOpsAPI.activateGraph({
        reason,
        confirmation_phrase: "ACTIVATE GRAPH REVISION",
      });
      notify.success("Graph revision activated", "Graph revision is now active");
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
      await adminLearningOpsAPI.deactivateGraph({
        reason,
        confirmation_phrase: "DEACTIVATE GRAPH REVISION",
      });
      notify.success("Graph revision deactivated", "Graph revision is now in shadow mode");
      setShowDeactivate(false);
      setReason("");
      handleRefresh();
    } catch (error) {
      notify.error("Deactivation failed", error instanceof Error ? error.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddEdge = async () => {
    if (!edgeForm.from_theme_id || !edgeForm.to_theme_id) {
      notify.error("Validation error", "From and To theme IDs are required");
      return;
    }
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/admin/graph-revision/edges", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_theme_id: parseInt(edgeForm.from_theme_id),
          to_theme_id: parseInt(edgeForm.to_theme_id),
          weight: parseFloat(edgeForm.weight),
          source: edgeForm.source,
        }),
      });
      if (!response.ok) throw new Error("Failed to create edge");
      notify.success("Edge created", "Prerequisite edge has been added");
      setShowAddEdge(false);
      setEdgeForm({ from_theme_id: "", to_theme_id: "", weight: "1.0", source: "manual" });
      loadEdges();
    } catch (error) {
      notify.error("Failed to create edge", error instanceof Error ? error.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDisableEdge = async (edgeId: string) => {
    if (!confirm("Are you sure you want to disable this edge?")) return;
    try {
      const response = await fetch(`/api/admin/graph-revision/edges/${edgeId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Failed to disable edge");
      notify.success("Edge disabled", "Prerequisite edge has been disabled");
      loadEdges();
    } catch (error) {
      notify.error("Failed to disable edge", error instanceof Error ? error.message : "Unknown error");
    }
  };

  const handleLoadShadowPlans = async () => {
    if (!planUserId.trim()) {
      notify.error("User ID required", "Please enter a user ID");
      return;
    }
    setPlansLoading(true);
    setPlansError(null);
    try {
      const response = await fetch(
        `/api/admin/graph-revision/shadow-plans?user_id=${encodeURIComponent(planUserId)}&days=${planDays}`,
      );
      if (!response.ok) throw new Error("Failed to load shadow plans");
      const data = await response.json();
      setShadowPlans(Array.isArray(data) ? data : data.plans || []);
    } catch (err) {
      setPlansError(err instanceof Error ? err : new Error("Failed to load shadow plans"));
    } finally {
      setPlansLoading(false);
    }
  };

  const neo4jUp = health?.neo4j_available || graphHealth?.neo4j_available || false;
  const nodeCount = health?.graph_stats.node_count || graphHealth?.graph_stats.node_count || 0;
  const edgeCount = health?.graph_stats.edge_count || graphHealth?.graph_stats.edge_count || 0;
  const hasCycles = health?.cycle_check.has_cycles || graphHealth?.cycle_check.has_cycles || false;
  const eligible = neo4jUp && !hasCycles && edgeCount > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Graph Revision Ops</h1>
        <p className="text-muted-foreground">Prerequisite-aware revision planning and activation control</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <StatusPill status={runtimeOverride.toUpperCase()} label={`Runtime: ${runtimeOverride}`} />
          <StatusPill status={neo4jUp ? "UP" : "DOWN"} label={`Neo4j: ${neo4jUp ? "UP" : "DOWN"}`} />
          <StatusPill status={isFrozen ? "FROZEN" : "ACTIVE"} label={`Freeze: ${isFrozen ? "ON" : "OFF"}`} />
          {health?.last_sync?.finished_at && (
            <StatusPill
              status="UP"
              label={`Last sync: ${formatDistanceToNow(new Date(health.last_sync.finished_at), { addSuffix: true })}`}
            />
          )}
        </div>
      </div>

      {/* Card A: Health & Integrity */}
      <Card>
        <CardHeader>
          <CardTitle>Health & Integrity</CardTitle>
          <CardDescription>Neo4j connectivity and graph statistics</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {healthLoading ? (
            <div className="space-y-2">
              <div className="h-4 w-32 animate-pulse rounded bg-muted" />
              <div className="h-4 w-48 animate-pulse rounded bg-muted" />
            </div>
          ) : healthError ? (
            <ErrorState
              title="Failed to load health"
              description={healthError.message}
              onAction={loadHealth}
              variant="card"
            />
          ) : health ? (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm text-muted-foreground">Neo4j:</span>
                  <div className="mt-1">
                    <StatusPill status={neo4jUp ? "UP" : "DOWN"} />
                  </div>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Node count:</span>
                  <p className="text-lg font-semibold">{nodeCount}</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Edge count:</span>
                  <p className="text-lg font-semibold">{edgeCount}</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Cycles:</span>
                  <div className="mt-1">
                    <StatusPill status={hasCycles ? "DOWN" : "UP"} label={hasCycles ? "Detected" : "None"} />
                  </div>
                </div>
              </div>

              {!neo4jUp && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>Neo4j is unavailable. Plans will fall back to baseline.</AlertDescription>
                </Alert>
              )}

              {hasCycles && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    Cycles detected in prerequisite graph. Activation blocked.
                  </AlertDescription>
                </Alert>
              )}

              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowSyncConfirm(true)}
                  disabled={healthLoading || isSyncing || isFrozen}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Sync Now
                </Button>
                {isFrozen && (
                  <span className="text-xs text-muted-foreground self-center">
                    Sync disabled: freeze_updates is enabled
                  </span>
                )}
              </div>
            </>
          ) : (
            <ErrorState
              title="Failed to load health"
              description="Unable to fetch graph health. Please try again."
              onAction={loadHealth}
              variant="card"
            />
          )}
        </CardContent>
      </Card>

      {/* Card B: Edge Manager */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Edge Manager</CardTitle>
              <CardDescription>Manage prerequisite edges</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAddEdge(true)}
              disabled={isFrozen}
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Edge
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {edgesLoading ? (
            <SkeletonTable rows={5} cols={6} />
          ) : edgesError ? (
            <ErrorState
              title="Failed to load edges"
              description={edgesError.message}
              onAction={loadEdges}
              variant="card"
            />
          ) : edges.length === 0 ? (
            <EmptyState
              title="No edges found"
              description="Add prerequisite edges to get started"
              variant="card"
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>From Theme</TableHead>
                  <TableHead>To Theme</TableHead>
                  <TableHead>Weight</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {edges.map((edge) => (
                  <TableRow key={edge.id}>
                    <TableCell>
                      {edge.from_theme_name || `Theme ${edge.from_theme_id}`}
                    </TableCell>
                    <TableCell>
                      {edge.to_theme_name || `Theme ${edge.to_theme_id}`}
                    </TableCell>
                    <TableCell>{edge.weight}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{edge.source}</Badge>
                    </TableCell>
                    <TableCell>
                      <StatusPill status={edge.active ? "ACTIVE" : "DISABLED"} />
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDisableEdge(edge.id)}
                          disabled={isFrozen || !edge.active}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Card C: Shadow Plans + Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Shadow Plans & Metrics</CardTitle>
          <CardDescription>Recent run metrics and per-user shadow plans</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Run Metrics */}
          <div>
            <h3 className="mb-2 text-sm font-semibold">Recent Run Metrics</h3>
            {runMetricsLoading ? (
              <SkeletonTable rows={3} cols={4} />
            ) : runMetrics && runMetrics.runs.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Mode</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Metrics</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runMetrics.runs.slice(0, 5).map((run) => (
                    <TableRow key={run.id}>
                      <TableCell>{new Date(run.run_date).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{run.mode}</Badge>
                      </TableCell>
                      <TableCell>
                        <StatusPill status={run.status === "DONE" ? "UP" : "SHADOW"} label={run.status} />
                      </TableCell>
                      <TableCell>
                        {run.metrics ? (
                          <span className="text-xs text-muted-foreground">
                            {Object.keys(run.metrics).length} metrics
                          </span>
                        ) : (
                          "N/A"
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyState title="No metrics available" variant="inline" />
            )}
          </div>

          {/* Shadow Plan Explorer */}
          <div>
            <h3 className="mb-2 text-sm font-semibold">Shadow Plan Explorer</h3>
            <div className="mb-4 flex gap-2">
              <div className="flex-1">
                <Label htmlFor="plan-user-id">User ID</Label>
                <Input
                  id="plan-user-id"
                  value={planUserId}
                  onChange={(e) => setPlanUserId(e.target.value)}
                  placeholder="Enter user ID"
                />
              </div>
              <div className="w-24">
                <Label htmlFor="plan-days">Days</Label>
                <Input
                  id="plan-days"
                  type="number"
                  value={planDays}
                  onChange={(e) => setPlanDays(e.target.value)}
                  min="1"
                  max="365"
                />
              </div>
              <div className="flex items-end">
                <Button onClick={handleLoadShadowPlans} disabled={plansLoading || !planUserId.trim()}>
                  <User className="mr-2 h-4 w-4" />
                  Load
                </Button>
              </div>
            </div>

            {plansLoading ? (
              <SkeletonTable rows={3} cols={3} />
            ) : plansError ? (
              <ErrorState
                title="Failed to load plans"
                description={plansError.message}
                onAction={handleLoadShadowPlans}
                variant="card"
              />
            ) : shadowPlans.length === 0 && planUserId ? (
              <EmptyState
                title="No plans found"
                description="No shadow plans available for this user and time period"
                variant="card"
              />
            ) : shadowPlans.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>User ID</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {shadowPlans.map((plan) => (
                    <TableRow key={`${plan.user_id}-${plan.plan_date}`}>
                      <TableCell>{new Date(plan.plan_date).toLocaleDateString()}</TableCell>
                      <TableCell className="font-mono text-sm">{plan.user_id}</TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedPlan(plan);
                            setShowPlanDetails(true);
                          }}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {/* Card D: Activation Control */}
      <Card>
        <CardHeader>
          <CardTitle>Activation Control</CardTitle>
          <CardDescription>Eligibility and activation status</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
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
            {!eligible && (
              <Alert variant="warning">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  {!neo4jUp && "Neo4j is unavailable. "}
                  {hasCycles && "Cycles detected in graph. "}
                  {edgeCount === 0 && "No prerequisite edges found. "}
                  Activation requires all checks to pass.
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
              variant="default"
              size="sm"
              onClick={() => setShowActivate(true)}
              disabled={healthLoading || isFrozen || !eligible || runtimeOverride === "v1"}
            >
              Activate
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowDeactivate(true)}
              disabled={healthLoading || isFrozen || runtimeOverride !== "v1"}
            >
              Deactivate
            </Button>
            {isFrozen && (
              <span className="text-xs text-muted-foreground self-center">
                Actions disabled: freeze_updates is enabled
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Sync Confirm */}
      <Dialog open={showSyncConfirm} onOpenChange={setShowSyncConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sync Neo4j</DialogTitle>
            <DialogDescription>Sync prerequisite edges from Postgres to Neo4j</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              This will sync all active prerequisite edges from Postgres to Neo4j. Continue?
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowSyncConfirm(false)} disabled={isSyncing}>
                Cancel
              </Button>
              <Button onClick={handleSync} disabled={isSyncing}>
                {isSyncing ? "Syncing..." : "Sync"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Add Edge Dialog */}
      <Dialog open={showAddEdge} onOpenChange={setShowAddEdge}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Prerequisite Edge</DialogTitle>
            <DialogDescription>Create a new prerequisite relationship</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="from-theme">From Theme ID</Label>
              <Input
                id="from-theme"
                type="number"
                value={edgeForm.from_theme_id}
                onChange={(e) => setEdgeForm({ ...edgeForm, from_theme_id: e.target.value })}
                placeholder="123"
              />
            </div>
            <div>
              <Label htmlFor="to-theme">To Theme ID</Label>
              <Input
                id="to-theme"
                type="number"
                value={edgeForm.to_theme_id}
                onChange={(e) => setEdgeForm({ ...edgeForm, to_theme_id: e.target.value })}
                placeholder="456"
              />
            </div>
            <div>
              <Label htmlFor="weight">Weight</Label>
              <Input
                id="weight"
                type="number"
                step="0.1"
                value={edgeForm.weight}
                onChange={(e) => setEdgeForm({ ...edgeForm, weight: e.target.value })}
                placeholder="1.0"
              />
            </div>
            <div>
              <Label htmlFor="source">Source</Label>
              <Input
                id="source"
                value={edgeForm.source}
                onChange={(e) => setEdgeForm({ ...edgeForm, source: e.target.value })}
                placeholder="manual"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddEdge(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddEdge} disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Shadow Plan Details */}
      <Dialog open={showPlanDetails} onOpenChange={setShowPlanDetails}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Shadow Plan Details</DialogTitle>
            <DialogDescription>
              Plan for user {selectedPlan?.user_id} on {selectedPlan?.plan_date}
            </DialogDescription>
          </DialogHeader>
          {selectedPlan && (
            <JsonViewer data={selectedPlan.plan_json} title="Plan JSON" defaultExpanded />
          )}
        </DialogContent>
      </Dialog>

      {/* Activate Modal */}
      <PoliceConfirmModal
        open={showActivate}
        onOpenChange={setShowActivate}
        actionTitle="Activate Graph Revision"
        requiredPhrase="ACTIVATE GRAPH REVISION"
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
        actionTitle="Deactivate Graph Revision"
        requiredPhrase="DEACTIVATE GRAPH REVISION"
        reason={reason}
        onReasonChange={setReason}
        onConfirm={handleDeactivate}
        isSubmitting={isSubmitting}
        variant="destructive"
      />
    </div>
  );
}
