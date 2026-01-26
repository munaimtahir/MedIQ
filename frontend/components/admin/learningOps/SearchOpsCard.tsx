"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Database, Search, AlertTriangle, CheckCircle2, XCircle, ExternalLink } from "lucide-react";
import { PoliceConfirmModal } from "./PoliceConfirmModal";
import { notify } from "@/lib/notify";
import type { SearchRuntimeStatus } from "@/lib/api/adminLearningOps";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import { formatDistanceToNow } from "@/lib/dateUtils";
import Link from "next/link";

interface SearchOpsCardProps {
  status: SearchRuntimeStatus | null;
  isFrozen: boolean;
  loading?: boolean;
  onRefresh: () => void;
}

export function SearchOpsCard({ status, isFrozen, loading, onRefresh }: SearchOpsCardProps) {
  const [showSwitchToPostgres, setShowSwitchToPostgres] = useState(false);
  const [showSwitchToElasticsearch, setShowSwitchToElasticsearch] = useState(false);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const requestedMode = status?.requested_mode || "postgres";
  const effectiveEngine = status?.effective_engine || "postgres";
  const esReachable = status?.es_reachable || false;
  const esEnabled = status?.enabled || false;
  const lastSwitch = status?.last_switch;
  const readiness = status?.readiness;

  const isDegraded = requestedMode === "elasticsearch" && effectiveEngine === "postgres";
  const isNotReady = requestedMode === "elasticsearch" && readiness && !readiness.ready;

  const handleSwitchToPostgres = async () => {
    setIsSubmitting(true);
    try {
      await adminLearningOpsAPI.switchSearchRuntime({
        mode: "postgres",
        reason,
        confirmation_phrase: "SWITCH SEARCH TO POSTGRES",
      });
      notify.success("Search mode switched", "Search is now using Postgres");
      setShowSwitchToPostgres(false);
      setReason("");
      onRefresh();
    } catch (error) {
      notify.error("Switch failed", error instanceof Error ? error.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSwitchToElasticsearch = async () => {
    setIsSubmitting(true);
    try {
      const result = await adminLearningOpsAPI.switchSearchRuntime({
        mode: "elasticsearch",
        reason,
        confirmation_phrase: "SWITCH SEARCH TO ELASTICSEARCH",
      });
      if (result.warnings && result.warnings.length > 0) {
        notify.warning(
          "Search mode switched with warnings",
          "Elasticsearch is unreachable, will fallback to Postgres",
        );
      } else {
        notify.success("Search mode switched", "Search is now using Elasticsearch");
      }
      setShowSwitchToElasticsearch(false);
      setReason("");
      onRefresh();
    } catch (error) {
      notify.error("Switch failed", error instanceof Error ? error.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Search (Elasticsearch)
          </CardTitle>
          <CardDescription>Admin Questions search engine runtime</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Requested Mode */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Requested mode:</span>
            <Badge variant={requestedMode === "elasticsearch" ? "default" : "secondary"}>
              {requestedMode === "elasticsearch" ? "Elasticsearch" : "Postgres"}
            </Badge>
          </div>

          {/* Effective Engine */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Effective engine:</span>
            <Badge variant={effectiveEngine === "elasticsearch" ? "default" : "secondary"}>
              {effectiveEngine === "elasticsearch" ? "Elasticsearch" : "Postgres"}
            </Badge>
          </div>

          {/* ES Health */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">ES health:</span>
            <div className="flex items-center gap-2">
              {esReachable ? (
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

          {/* ES Enabled */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">ES enabled:</span>
            <Badge variant={esEnabled ? "default" : "outline"}>
              {esEnabled ? "Yes" : "No"}
            </Badge>
          </div>

          {/* Last Switch */}
          {lastSwitch && (
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">
                Last switch: {formatDistanceToNow(new Date(lastSwitch.at), { addSuffix: true })}
              </div>
              <div className="text-xs text-muted-foreground">By: {lastSwitch.by}</div>
              {lastSwitch.reason && (
                <div className="text-xs text-muted-foreground">Reason: {lastSwitch.reason}</div>
              )}
            </div>
          )}

          {/* Readiness Badge */}
          {requestedMode === "elasticsearch" && readiness && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Readiness:</span>
              <Badge
                variant={readiness.ready ? "default" : readiness.blocking_reasons.length > 0 ? "destructive" : "secondary"}
                className={readiness.ready ? "bg-green-600" : ""}
              >
                {readiness.ready ? "READY" : "NOT READY"}
              </Badge>
            </div>
          )}

          {/* Not Ready Warning */}
          {isNotReady && readiness && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-1">
                  <div>Elasticsearch not ready. Blocking reasons:</div>
                  <ul className="list-disc list-inside text-xs space-y-0.5">
                    {readiness.blocking_reasons.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Degraded Warning (fallback) */}
          {isDegraded && !isNotReady && (
            <Alert variant="warning">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Requested Elasticsearch but it's unavailable. Using Postgres fallback.
              </AlertDescription>
            </Alert>
          )}

          {/* Actions */}
          <div className="flex flex-col gap-2 pt-2">
            {requestedMode === "elasticsearch" ? (
              <Button
                variant="outline"
                onClick={() => setShowSwitchToPostgres(true)}
                disabled={isFrozen || loading}
              >
                Switch to Postgres
              </Button>
            ) : (
              <Button
                variant="outline"
                onClick={() => setShowSwitchToElasticsearch(true)}
                disabled={isFrozen || loading || !esEnabled || (readiness && !readiness.ready)}
                title={
                  readiness && !readiness.ready
                    ? `Elasticsearch not ready: ${readiness.blocking_reasons.join("; ")}`
                    : undefined
                }
              >
                Switch to Elasticsearch
              </Button>
            )}
            <Button variant="ghost" size="sm" asChild>
              <Link href="/admin/search">
                View details
                <ExternalLink className="ml-2 h-3 w-3" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Switch to Postgres Modal */}
      <PoliceConfirmModal
        open={showSwitchToPostgres}
        onOpenChange={setShowSwitchToPostgres}
        actionTitle="Switch Search to Postgres"
        requiredPhrase="SWITCH SEARCH TO POSTGRES"
        reason={reason}
        onReasonChange={setReason}
        onConfirm={handleSwitchToPostgres}
        isSubmitting={isSubmitting}
        variant="default"
      />

      {/* Switch to Elasticsearch Modal */}
      <PoliceConfirmModal
        open={showSwitchToElasticsearch}
        onOpenChange={setShowSwitchToElasticsearch}
        actionTitle="Switch Search to Elasticsearch"
        requiredPhrase="SWITCH SEARCH TO ELASTICSEARCH"
        reason={reason}
        onReasonChange={setReason}
        onConfirm={handleSwitchToElasticsearch}
        isSubmitting={isSubmitting}
        variant="default"
      />
    </>
  );
}
