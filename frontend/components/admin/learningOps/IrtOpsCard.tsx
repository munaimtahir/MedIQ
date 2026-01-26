"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Beaker, AlertTriangle, CheckCircle2, XCircle, ExternalLink } from "lucide-react";
import { PoliceConfirmModal } from "./PoliceConfirmModal";
import { notify } from "@/lib/notify";
import { stageIrtActivate, stageIrtDeactivate } from "@/lib/admin/stageActions";
import type { IrtStatus, IrtRun } from "@/lib/api/adminLearningOps";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import { formatDistanceToNow } from "@/lib/dateUtils";
import Link from "next/link";

interface IrtOpsCardProps {
  status: IrtStatus | null;
  lastRun: IrtRun | null;
  isFrozen: boolean;
  loading?: boolean;
  onRefresh: () => void;
}

export function IrtOpsCard({ status, lastRun, isFrozen, loading, onRefresh }: IrtOpsCardProps) {
  const [showActivate, setShowActivate] = useState(false);
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [showEvaluate, setShowEvaluate] = useState(false);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isActive = status?.flags.active || false;
  const mode = isActive ? "active" : status?.flags.shadow ? "shadow" : "disabled";
  const eligible = status?.latest_decision?.eligible ?? false;
  const lastRunStatus = lastRun?.status || "N/A";
  const lastRunTime = lastRun?.finished_at
    ? formatDistanceToNow(new Date(lastRun.finished_at), { addSuffix: true })
    : "Never";

  const handleEvaluate = async () => {
    if (!lastRun?.id) {
      notify.error("No run available", "Create a calibration run first");
      return;
    }
    try {
      await adminLearningOpsAPI.evaluateIrtEligibility({ run_id: lastRun.id });
      notify.success("Eligibility evaluated", "Check the status for gate results");
      onRefresh();
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
      await adminLearningOpsAPI.deactivateIrt({
        reason,
        confirmation_phrase: "DEACTIVATE IRT",
      });
      notify.success("IRT deactivated", "IRT is now in shadow mode");
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
    if (!lastRun?.id) {
      notify.error("No run available", "Create a calibration run first");
      return;
    }
    stageIrtActivate(lastRun.id, "selection_only", lastRun.model_type || "IRT_2PL");
    notify.success("Activation staged", "Review and apply from the Change Review drawer");
  };

  const handleStageDeactivate = () => {
    stageIrtDeactivate();
    notify.success("Deactivation staged", "Review and apply from the Change Review drawer");
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Beaker className="h-5 w-5" />
            IRT (Item Response Theory)
          </CardTitle>
          <CardDescription>Shadow calibration runs + activation gates</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Status */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Current mode:</span>
            <Badge variant={mode === "active" ? "default" : mode === "shadow" ? "secondary" : "outline"}>
              {mode}
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Last run:</span>
            <div className="flex items-center gap-2">
              <Badge variant={lastRunStatus === "DONE" ? "default" : "secondary"}>{lastRunStatus}</Badge>
              <span className="text-sm text-muted-foreground">{lastRunTime}</span>
            </div>
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
            {status?.latest_decision && !eligible && (
              <Alert variant="warning">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="text-xs">
                  Check gate results for details. Activation requires all gates to pass.
                </AlertDescription>
              </Alert>
            )}
          </div>

          {/* Freeze Warning */}
          {isFrozen && (
            <Alert variant="warning">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                Freeze mode is enabled. Run execution is blocked, but you can still evaluate eligibility.
              </AlertDescription>
            </Alert>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-2 pt-2">
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
              onClick={handleStageActivate}
              disabled={loading || isFrozen || !eligible || isActive}
            >
              Stage activate
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={() => setShowActivate(true)}
              disabled={loading || isFrozen || !eligible || isActive}
            >
              Activate now
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleStageDeactivate}
              disabled={loading || !isActive}
            >
              Stage deactivate
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowDeactivate(true)}
              disabled={loading || !isActive}
            >
              Deactivate now
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/admin/irt">
                View details
                <ExternalLink className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

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
    </>
  );
}
