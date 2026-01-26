"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { BarChart3, AlertTriangle, CheckCircle2, XCircle, ExternalLink } from "lucide-react";
import { PoliceConfirmModal } from "./PoliceConfirmModal";
import { notify } from "@/lib/notify";
import { stageRankActivate, stageRankDeactivate } from "@/lib/admin/stageActions";
import type { RankStatus } from "@/lib/api/adminLearningOps";
import { adminLearningOpsAPI } from "@/lib/api/adminLearningOps";
import Link from "next/link";

interface RankOpsCardProps {
  status: RankStatus | null;
  cohortKey: string;
  onCohortKeyChange: (key: string) => void;
  isFrozen: boolean;
  loading?: boolean;
  onRefresh: () => void;
}

export function RankOpsCard({
  status,
  cohortKey,
  onCohortKeyChange,
  isFrozen,
  loading,
  onRefresh,
}: RankOpsCardProps) {
  const [showActivate, setShowActivate] = useState(false);
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const mode = status?.mode || "shadow";
  const eligible = status?.eligible || false;
  const coverage = status?.latest_run?.coverage || null;
  const stability = status?.latest_run?.stability || null;

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
      await adminLearningOpsAPI.deactivateRank({
        reason,
        confirmation_phrase: "DEACTIVATE RANK",
      });
      notify.success("Rank deactivated", "Rank is now in shadow mode");
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
    stageRankActivate(cohortKey);
    notify.success("Activation staged", "Review and apply from the Change Review drawer");
  };

  const handleStageDeactivate = () => {
    stageRankDeactivate();
    notify.success("Deactivation staged", "Review and apply from the Change Review drawer");
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Rank Prediction
          </CardTitle>
          <CardDescription>Quantile-based percentile estimates (shadow/offline)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Cohort Selector */}
          <div className="space-y-2">
            <Label htmlFor="cohort-key">Cohort</Label>
            <Select value={cohortKey} onValueChange={onCohortKeyChange}>
              <SelectTrigger id="cohort-key">
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

          {/* Status */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Current mode:</span>
            <Badge variant={mode === "v1" ? "default" : mode === "shadow" ? "secondary" : "outline"}>
              {mode}
            </Badge>
          </div>

          {/* Metrics */}
          {coverage !== null && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Coverage:</span>
              <span className="text-sm font-medium">{(coverage * 100).toFixed(1)}%</span>
            </div>
          )}

          {stability !== null && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Stability:</span>
              <span className="text-sm font-medium">{stability.toFixed(3)}</span>
            </div>
          )}

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
            {status?.reasons && status.reasons.length > 0 && (
              <Alert variant="warning">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="text-xs">
                  {status.reasons.join(", ")}
                </AlertDescription>
              </Alert>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2 pt-2">
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
              <Link href="/admin/rank">
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
    </>
  );
}
