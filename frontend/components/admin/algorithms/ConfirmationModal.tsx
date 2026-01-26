"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { CheckCircle2, XCircle, Info } from "lucide-react";
import {
  getRequiredPhrase,
  isPhraseMatch,
  getRiskChecklist,
  type ActionType,
} from "@/lib/policeMode";

interface ConfirmationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actionType: ActionType;
  targetProfile?: "V1_PRIMARY" | "V0_FALLBACK";
  previousConfig: Record<string, unknown>;
  newConfig: Record<string, unknown>;
  onConfirm: (confirmationPhrase: string, coApproverCode?: string) => void | Promise<void>;
  isSubmitting?: boolean;
  impactMetrics?: {
    activeUsersLast24h?: number;
    sessionsInProgress?: number;
    usersNeedingBridge?: number;
  };
  requireCoApproval?: boolean;
  onCoApprovalChange?: (enabled: boolean) => void;
}

export function ConfirmationModal({
  open,
  onOpenChange,
  actionType,
  targetProfile,
  previousConfig,
  newConfig,
  onConfirm,
  isSubmitting = false,
  impactMetrics,
  requireCoApproval = false,
  onCoApprovalChange,
}: ConfirmationModalProps) {
  const [confirmationPhrase, setConfirmationPhrase] = useState("");
  const [coApproverCode, setCoApproverCode] = useState("");

  const requiredPhrase = getRequiredPhrase({
    actionType,
    targetProfile,
    caseSensitive: false,
  });

  const phraseMatches = isPhraseMatch(confirmationPhrase, requiredPhrase, "case-insensitive");
  const canConfirm = phraseMatches && (!requireCoApproval || coApproverCode.trim().length > 0);

  const handleConfirm = async () => {
    if (!canConfirm) return;
    await onConfirm(confirmationPhrase, requireCoApproval ? coApproverCode : undefined);
    // Reset on success
    setConfirmationPhrase("");
    setCoApproverCode("");
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setConfirmationPhrase("");
      setCoApproverCode("");
      onOpenChange(false);
    }
  };

  const checklist = getRiskChecklist();

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Confirm Action</DialogTitle>
          <DialogDescription>
            Review the changes and confirm by typing the required phrase.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Risk Summary Panel */}
          <div className="rounded-lg border bg-muted/50 p-4 space-y-4">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-muted-foreground" />
              <h4 className="font-semibold text-sm">Risk Summary</h4>
            </div>

            {/* Checklist */}
            <div className="space-y-2">
              {checklist.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />
                  <span>{item.label}</span>
                </div>
              ))}
            </div>

            <Separator />

            {/* Impact Metrics */}
            <div className="space-y-2">
              <h5 className="text-xs font-semibold text-muted-foreground uppercase">Impact Estimate</h5>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {impactMetrics?.activeUsersLast24h !== undefined ? (
                  <div>
                    <span className="text-muted-foreground">Active users (24h):</span>{" "}
                    <span className="font-medium">{impactMetrics.activeUsersLast24h}</span>
                  </div>
                ) : null}
                {impactMetrics?.sessionsInProgress !== undefined ? (
                  <div>
                    <span className="text-muted-foreground">Sessions in progress:</span>{" "}
                    <span className="font-medium">{impactMetrics.sessionsInProgress}</span>
                  </div>
                ) : null}
                {impactMetrics?.usersNeedingBridge !== undefined ? (
                  <div>
                    <span className="text-muted-foreground">Users needing bridge:</span>{" "}
                    <span className="font-medium">{impactMetrics.usersNeedingBridge}</span>
                  </div>
                ) : null}
                {!impactMetrics ||
                (impactMetrics.activeUsersLast24h === undefined &&
                  impactMetrics.sessionsInProgress === undefined &&
                  impactMetrics.usersNeedingBridge === undefined) ? (
                  <div className="text-sm text-muted-foreground">Metrics not available</div>
                ) : null}
              </div>
            </div>
          </div>

          {/* Typed Confirmation */}
          <div className="space-y-2">
            <Label htmlFor="confirmation-phrase">
              Type confirmation phrase <span className="text-destructive">*</span>
            </Label>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Required phrase:</span>
                <code className="px-2 py-1 bg-muted rounded font-mono">{requiredPhrase}</code>
              </div>
              <Input
                id="confirmation-phrase"
                value={confirmationPhrase}
                onChange={(e) => setConfirmationPhrase(e.target.value)}
                placeholder="Type the phrase above..."
                disabled={isSubmitting}
                className={confirmationPhrase && !phraseMatches ? "border-destructive" : ""}
              />
              <div className="flex items-center gap-2">
                {phraseMatches ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <Badge variant="success" className="text-xs">
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

          {/* Optional Two-Person Rule */}
          {onCoApprovalChange && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="co-approval-toggle">Require co-approval</Label>
                <input
                  id="co-approval-toggle"
                  type="checkbox"
                  checked={requireCoApproval}
                  onChange={(e) => onCoApprovalChange(e.target.checked)}
                  disabled={isSubmitting}
                  className="h-4 w-4"
                />
              </div>
              {requireCoApproval && (
                <div className="space-y-2">
                  <Label htmlFor="co-approver-code">
                    Co-approver code <span className="text-muted-foreground text-xs">(optional)</span>
                  </Label>
                  <Input
                    id="co-approver-code"
                    value={coApproverCode}
                    onChange={(e) => setCoApproverCode(e.target.value)}
                    placeholder="Ask another ADMIN to enter their one-time approval code"
                    disabled={isSubmitting}
                  />
                  <p className="text-xs text-muted-foreground">
                    Requires backend support. If not available, this will be logged but not enforced.
                  </p>
                </div>
              )}
            </div>
          )}

          <Separator />

          {/* JSON Diff */}
          <div className="space-y-4">
            <div>
              <Label className="text-sm font-semibold">Previous Configuration</Label>
              <div className="mt-2 h-32 rounded-md border bg-muted p-3 overflow-auto">
                <pre className="text-xs">
                  {JSON.stringify(previousConfig, null, 2)}
                </pre>
              </div>
            </div>

            <div>
              <Label className="text-sm font-semibold">New Configuration</Label>
              <div className="mt-2 h-32 rounded-md border bg-muted p-3 overflow-auto">
                <pre className="text-xs">
                  {JSON.stringify(newConfig, null, 2)}
                </pre>
              </div>
            </div>
          </div>

          {/* Warning */}
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <strong>⚠️ Important:</strong> Changes apply to <strong>new sessions only</strong>.
              In-progress sessions retain their starting profile (session snapshot rule).
            </AlertDescription>
          </Alert>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!canConfirm || isSubmitting}
            variant={actionType === "FREEZE" || actionType === "PROFILE_SWITCH" ? "destructive" : "default"}
          >
            {isSubmitting ? "Processing..." : "Confirm & Apply"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
