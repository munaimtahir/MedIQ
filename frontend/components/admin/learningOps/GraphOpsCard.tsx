"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Network, AlertTriangle, CheckCircle2, XCircle, RefreshCw, ExternalLink } from "lucide-react";
import { PoliceConfirmModal } from "./PoliceConfirmModal";
import { notify } from "@/lib/notify";
import { stageGraphActivate, stageGraphDeactivate } from "@/lib/admin/stageActions";
import type { GraphHealth, RuntimeStatus } from "@/lib/api/adminLearningOps";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import { formatDistanceToNow } from "@/lib/dateUtils";
import Link from "next/link";

interface GraphOpsCardProps {
  health: GraphHealth | null;
  runtime: RuntimeStatus | null;
  isFrozen: boolean;
  loading?: boolean;
  onRefresh: () => void;
}

export function GraphOpsCard({ health, runtime, isFrozen, loading, onRefresh }: GraphOpsCardProps) {
  const [showActivate, setShowActivate] = useState(false);
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [showSyncConfirm, setShowSyncConfirm] = useState(false);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  const neo4jUp = health?.neo4j_available || false;
  const hasCycles = health?.cycle_check.has_cycles || false;
  const nodeCount = health?.graph_stats.node_count || 0;
  const edgeCount = health?.graph_stats.edge_count || 0;
  const lastSync = health?.last_sync;
  const lastSyncTime = lastSync?.finished_at
    ? formatDistanceToNow(new Date(lastSync.finished_at), { addSuffix: true })
    : "Never";

  // Compute eligibility (simplified - should come from backend)
  const eligible = neo4jUp && !hasCycles && edgeCount > 0;
  const mode = (runtime?.config.overrides["graph_revision"] as "v0" | "shadow" | "v1") || "shadow";

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await adminLearningOpsAPI.runGraphSync();
      notify.success("Sync triggered", "Neo4j sync job started");
      setShowSyncConfirm(false);
      onRefresh();
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
      onRefresh();
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
      onRefresh();
    } catch (error) {
      notify.error("Deactivation failed", error instanceof Error ? error.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStageActivate = () => {
    stageGraphActivate();
    notify.success("Activation staged", "Review and apply from the Change Review drawer");
  };

  const handleStageDeactivate = () => {
    stageGraphDeactivate();
    notify.success("Deactivation staged", "Review and apply from the Change Review drawer");
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-5 w-5" />
            Graph-Aware Revision
          </CardTitle>
          <CardDescription>Prerequisite-aware revision planning (shadow/offline)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Neo4j Health */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Neo4j:</span>
            <Badge variant={neo4jUp ? "default" : "destructive"}>{neo4jUp ? "UP" : "DOWN"}</Badge>
          </div>

          {/* Graph Stats */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Nodes:</span>
            <span className="text-sm font-medium">{nodeCount}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Edges:</span>
            <span className="text-sm font-medium">{edgeCount}</span>
          </div>

          {/* Cycle Status */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Cycles:</span>
            <Badge variant={hasCycles ? "destructive" : "default"}>
              {hasCycles ? `${health?.cycle_check.cycle_count || 0} detected` : "None"}
            </Badge>
          </div>

          {/* Last Sync */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Last sync:</span>
            <span className="text-sm text-muted-foreground">{lastSyncTime}</span>
          </div>

          {/* Eligibility */}
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
            {!neo4jUp && (
              <Alert variant="warning">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="text-xs">
                  Neo4j is unavailable. Plans will fall back to baseline.
                </AlertDescription>
              </Alert>
            )}
            {hasCycles && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="text-xs">
                  Cycles detected in prerequisite graph. Activation blocked.
                </AlertDescription>
              </Alert>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSyncConfirm(true)}
              disabled={loading || isSyncing}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Sync Now
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleStageActivate}
              disabled={loading || isFrozen || !eligible || mode === "v1"}
            >
              Stage activate
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={() => setShowActivate(true)}
              disabled={loading || isFrozen || !eligible || mode === "v1"}
            >
              Activate now
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleStageDeactivate}
              disabled={loading || mode !== "v1"}
            >
              Stage deactivate
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowDeactivate(true)}
              disabled={loading || mode !== "v1"}
            >
              Deactivate now
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/admin/graph-revision">
                View details
                <ExternalLink className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Sync Confirm (simple dialog, no police mode) */}
      {showSyncConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card rounded-lg border p-6 max-w-md w-full space-y-4">
            <h3 className="text-lg font-semibold">Sync Neo4j</h3>
            <p className="text-sm text-muted-foreground">
              This will sync prerequisite edges from Postgres to Neo4j. Continue?
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setShowSyncConfirm(false)} disabled={isSyncing}>
                Cancel
              </Button>
              <Button onClick={handleSync} disabled={isSyncing}>
                {isSyncing ? "Syncing..." : "Sync"}
              </Button>
            </div>
          </div>
        </div>
      )}

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
    </>
  );
}
