"use client";

import { useState, useCallback } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { JsonViewer } from "@/components/shared/JsonViewer";
import { StatusPill } from "@/components/shared/StatusPill";
import { useChangeReviewStore, type StagedAction } from "@/store/changeReviewStore";
import { applyChangeBatch, type ApplyProgress } from "@/lib/admin/applyChangeBatch";
import { notify } from "@/lib/notify";
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Trash2,
  ChevronDown,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ChangeReviewDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onApplyComplete?: () => void;
}

const BATCH_CONFIRMATION_PHRASE = "APPLY CHANGES";

export function ChangeReviewDrawer({
  open,
  onOpenChange,
  onApplyComplete,
}: ChangeReviewDrawerProps) {
  const { stagedActions, removeAction, clearAll, hasChanges } = useChangeReviewStore();
  const [reason, setReason] = useState("");
  const [confirmationPhrase, setConfirmationPhrase] = useState("");
  const [isApplying, setIsApplying] = useState(false);
  const [applyProgress, setApplyProgress] = useState<ApplyProgress[]>([]);
  const [applyResult, setApplyResult] = useState<{
    succeeded: Array<{ action: StagedAction; progress: ApplyProgress }>;
    failed: Array<{ action: StagedAction; progress: ApplyProgress }>;
    skipped: Array<{ action: StagedAction; progress: ApplyProgress }>;
    rollbackSuggestions: string[];
  } | null>(null);
  const [expandedActions, setExpandedActions] = useState<Set<string>>(new Set());

  const phraseMatches = confirmationPhrase.trim().toUpperCase() === BATCH_CONFIRMATION_PHRASE.toUpperCase();
  const canApply =
    reason.trim().length >= 10 &&
    phraseMatches &&
    stagedActions.length > 0 &&
    !isApplying;

  const toggleExpanded = (actionId: string) => {
    setExpandedActions((prev) => {
      const next = new Set(prev);
      if (next.has(actionId)) {
        next.delete(actionId);
      } else {
        next.add(actionId);
      }
      return next;
    });
  };

  const handleApply = async () => {
    if (!canApply) return;

    setIsApplying(true);
    setApplyProgress([]);
    setApplyResult(null);

    const progressCallback = (progress: ApplyProgress[]) => {
      setApplyProgress([...progress]);
    };

    try {
      const result = await applyChangeBatch(
        stagedActions,
        reason,
        confirmationPhrase,
        progressCallback,
      );

      setApplyResult(result);

      if (result.failed.length === 0 && result.skipped.length === 0) {
        notify.success("All changes applied", "All staged changes have been applied successfully");
        clearAll();
        setReason("");
        setConfirmationPhrase("");
        onApplyComplete?.();
        setTimeout(() => {
          onOpenChange(false);
        }, 2000);
      } else {
        notify.warning(
          "Partial application",
          `${result.succeeded.length} succeeded, ${result.failed.length} failed, ${result.skipped.length} skipped`,
        );
      }
    } catch (error) {
      notify.error(
        "Apply failed",
        error instanceof Error ? error.message : "Unknown error occurred",
      );
    } finally {
      setIsApplying(false);
    }
  };

  const getRiskBadgeVariant = (risk: "high" | "medium" | "low") => {
    switch (risk) {
      case "high":
        return "destructive";
      case "medium":
        return "default";
      case "low":
        return "secondary";
    }
  };

  const getActionTitle = (action: StagedAction): string => {
    switch (action.type) {
      case "RUNTIME_SWITCH":
        const switchPayload = action.payload as { profile: string };
        return `Switch runtime profile to ${switchPayload.profile}`;
      case "OVERRIDES_APPLY":
        return "Apply module overrides";
      case "FREEZE":
        return "Freeze updates";
      case "UNFREEZE":
        return "Unfreeze updates";
      case "IRT_ACTIVATE":
        return "Activate IRT";
      case "IRT_DEACTIVATE":
        return "Deactivate IRT";
      case "RANK_ACTIVATE":
        const rankPayload = action.payload as { cohort_key?: string };
        return `Activate Rank${rankPayload.cohort_key ? ` (${rankPayload.cohort_key})` : ""}`;
      case "RANK_DEACTIVATE":
        return "Deactivate Rank";
      case "GRAPH_ACTIVATE":
        return "Activate Graph Revision";
      case "GRAPH_DEACTIVATE":
        return "Deactivate Graph Revision";
      default:
        return action.type;
    }
  };

  const getProgressStatus = (actionId: string): ApplyProgress | null => {
    return applyProgress.find((p) => p.actionId === actionId) || null;
  };

  const renderProgressIcon = (status: ApplyProgress["status"]) => {
    switch (status) {
      case "success":
        return <CheckCircle2 className="h-4 w-4 text-green-600" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-destructive" />;
      case "running":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-600" />;
      case "skipped":
        return <Clock className="h-4 w-4 text-muted-foreground" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
        <SheetHeader>
          <div className="flex items-center justify-between">
            <div>
              <SheetTitle>Change Review</SheetTitle>
              <SheetDescription>
                Review and apply staged changes as a single batch operation
              </SheetDescription>
            </div>
            {hasChanges() && (
              <Badge variant="default" className="ml-2">
                {stagedActions.length}
              </Badge>
            )}
          </div>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Actions */}
          {stagedActions.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <p>No changes staged</p>
              <p className="text-sm mt-2">Stage changes from the controls above to review them here</p>
            </div>
          ) : (
            <>
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold">Staged Actions ({stagedActions.length})</h3>
                <Button variant="outline" size="sm" onClick={clearAll} disabled={isApplying}>
                  Clear all
                </Button>
              </div>

              <div className="space-y-3">
                {stagedActions.map((action) => {
                  const progress = getProgressStatus(action.id);
                  const isExpanded = expandedActions.has(action.id);

                  return (
                    <Card key={action.id} className={cn(progress?.status === "failed" && "border-destructive")}>
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              {progress && renderProgressIcon(progress.status)}
                              <CardTitle className="text-base">{getActionTitle(action)}</CardTitle>
                              <Badge variant={getRiskBadgeVariant(action.riskLevel)} className="text-xs">
                                {action.riskLevel}
                              </Badge>
                            </div>
                            <CardDescription className="text-sm">{action.diffSummary}</CardDescription>
                            {progress && (
                              <div className="mt-2 text-xs">
                                {progress.message && (
                                  <p className="text-muted-foreground">{progress.message}</p>
                                )}
                                {progress.error && (
                                  <p className="text-destructive">{progress.error}</p>
                                )}
                              </div>
                            )}
                          </div>
                          <div className="flex gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleExpanded(action.id)}
                            >
                              {isExpanded ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeAction(action.id)}
                              disabled={isApplying}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </CardHeader>
                      {isExpanded && (
                        <CardContent>
                          <JsonViewer data={action.payload} title="Payload" defaultExpanded={false} />
                        </CardContent>
                      )}
                    </Card>
                  );
                })}
              </div>
            </>
          )}

          {/* Apply Section */}
          {stagedActions.length > 0 && (
            <>
              <div className="border-t pt-6 space-y-4">
                <h3 className="text-lg font-semibold">Apply Changes</h3>

                {/* Reason */}
                <div className="space-y-2">
                  <Label htmlFor="batch-reason">
                    Reason <span className="text-destructive">*</span>
                  </Label>
                  <Textarea
                    id="batch-reason"
                    placeholder="Explain why you are applying these changes (minimum 10 characters)..."
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    rows={3}
                    disabled={isApplying}
                    className={reason.length > 0 && reason.length < 10 ? "border-destructive" : ""}
                  />
                  {reason.length > 0 && reason.length < 10 && (
                    <p className="text-sm text-destructive">Reason must be at least 10 characters</p>
                  )}
                </div>

                {/* Confirmation Phrase */}
                <div className="space-y-2">
                  <Label htmlFor="batch-phrase">
                    Type confirmation phrase <span className="text-destructive">*</span>
                  </Label>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>Required phrase:</span>
                      <code className="px-2 py-1 bg-muted rounded font-mono">
                        {BATCH_CONFIRMATION_PHRASE}
                      </code>
                    </div>
                    <Input
                      id="batch-phrase"
                      value={confirmationPhrase}
                      onChange={(e) => setConfirmationPhrase(e.target.value)}
                      placeholder="Type the phrase above..."
                      disabled={isApplying}
                      className={confirmationPhrase && !phraseMatches ? "border-destructive" : ""}
                    />
                    <div className="flex items-center gap-2">
                      {phraseMatches ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                          <Badge variant="default" className="text-xs bg-green-600">
                            Confirmed
                          </Badge>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-4 w-4 text-destructive" />
                          <Badge variant="destructive" className="text-xs">
                            Not confirmed
                          </Badge>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Impact Checklist */}
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription className="text-sm">
                    <strong>Impact reminders:</strong>
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>Applies to new sessions only (session snapshot rule)</li>
                      <li>Rollback is possible via toggles</li>
                      <li>Freeze updates prevents state writes</li>
                    </ul>
                  </AlertDescription>
                </Alert>

                {/* Apply Button */}
                <Button
                  onClick={handleApply}
                  disabled={!canApply}
                  className="w-full"
                  size="lg"
                >
                  {isApplying ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Applying changes...
                    </>
                  ) : (
                    "Apply all changes"
                  )}
                </Button>
              </div>

              {/* Apply Result */}
              {applyResult && (
                <div className="border-t pt-6 space-y-4">
                  <h3 className="text-lg font-semibold">Apply Results</h3>

                  {applyResult.succeeded.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-green-600 mb-2">
                        ✅ Succeeded ({applyResult.succeeded.length})
                      </h4>
                      <ul className="space-y-1 text-sm">
                        {applyResult.succeeded.map(({ action }) => (
                          <li key={action.id} className="text-muted-foreground">
                            {getActionTitle(action)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {applyResult.failed.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-destructive mb-2">
                        ❌ Failed ({applyResult.failed.length})
                      </h4>
                      <ul className="space-y-2 text-sm">
                        {applyResult.failed.map(({ action, progress }) => (
                          <li key={action.id}>
                            <div className="font-medium">{getActionTitle(action)}</div>
                            <div className="text-destructive text-xs">{progress.error}</div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {applyResult.skipped.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-muted-foreground mb-2">
                        ⏭️ Skipped ({applyResult.skipped.length})
                      </h4>
                      <ul className="space-y-1 text-sm">
                        {applyResult.skipped.map(({ action, progress }) => (
                          <li key={action.id} className="text-muted-foreground">
                            {getActionTitle(action)}: {progress.message}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {applyResult.rollbackSuggestions.length > 0 && (
                    <Alert variant="warning">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        <strong>Rollback suggestions:</strong>
                        <ul className="list-disc list-inside mt-2 space-y-1">
                          {applyResult.rollbackSuggestions.map((suggestion, idx) => (
                            <li key={idx}>{suggestion}</li>
                          ))}
                        </ul>
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
