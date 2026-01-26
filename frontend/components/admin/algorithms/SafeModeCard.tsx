"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ConfirmationModal } from "./ConfirmationModal";
import { stageFreeze } from "@/lib/admin/stageActions";
import { notify } from "@/lib/notify";
import { AlertTriangle } from "lucide-react";
import type { RuntimePayload } from "@/lib/admin/algorithms/api";

interface SafeModeCardProps {
  data: RuntimePayload | null;
  loading: boolean;
  onFreeze: (reason: string, confirmationPhrase?: string, coApproverCode?: string) => Promise<void>;
  onUnfreeze: (reason: string, confirmationPhrase?: string, coApproverCode?: string) => Promise<void>;
}

export function SafeModeCard({ data, loading, onFreeze, onUnfreeze }: SafeModeCardProps) {
  const [reason, setReason] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isFrozen = data?.config.safe_mode.freeze_updates ?? false;

  const canToggle = reason.trim().length >= 10 && !isSubmitting;

  const handleToggle = () => {
    setShowConfirm(true);
  };

  const handleConfirm = async (confirmationPhrase: string, coApproverCode?: string) => {
    setIsSubmitting(true);
    try {
      if (isFrozen) {
        await onUnfreeze(reason, confirmationPhrase, coApproverCode);
      } else {
        await onFreeze(reason, confirmationPhrase, coApproverCode);
      }
      setShowConfirm(false);
      setReason("");
    } catch (error) {
      // Error handled by hook
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStage = () => {
    if (reason.trim().length < 10) {
      notify.error("Reason required", "Please provide a reason (minimum 10 characters)");
      return;
    }
    stageFreeze(isFrozen);
    notify.success("Change staged", "Review and apply from the Change Review drawer");
    setReason("");
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Emergency Safe Mode</CardTitle>
          <CardDescription>
            Freeze all learning state updates (read-only mode)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="freeze-toggle">Freeze Updates</Label>
              <p className="text-sm text-muted-foreground">
                When enabled, learning state writes are paused
              </p>
            </div>
            <Switch
              id="freeze-toggle"
              checked={isFrozen}
              onCheckedChange={handleToggle}
              disabled={loading || isSubmitting}
            />
          </div>

          {isFrozen && (
            <Alert variant="warning">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Updates Frozen</AlertTitle>
              <AlertDescription>
                Learning state writes are paused. Students will still practice, but
                mastery/revision updates will not change until unfrozen.
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="freeze-reason">
              Reason <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="freeze-reason"
              placeholder="Explain why you are freezing/unfreezing updates (minimum 10 characters)..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className={reason.length > 0 && reason.length < 10 ? "border-destructive" : ""}
            />
            {reason.length > 0 && reason.length < 10 && (
              <p className="text-sm text-destructive">
                Reason must be at least 10 characters
              </p>
            )}
          </div>

          <div className="flex gap-2">
            <Button
              onClick={handleStage}
              variant="default"
              disabled={!canToggle || isSubmitting}
              className="flex-1"
            >
              Stage {isFrozen ? "unfreeze" : "freeze"}
            </Button>
            <Button
              onClick={handleToggle}
              variant={isFrozen ? "default" : "destructive"}
              disabled={!canToggle || isSubmitting}
              className="flex-1"
            >
              {isSubmitting
                ? "Processing..."
                : isFrozen
                  ? "Unfreeze Now"
                  : "Freeze Now"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <ConfirmationModal
        open={showConfirm}
        onOpenChange={setShowConfirm}
        actionType={isFrozen ? "UNFREEZE" : "FREEZE"}
        previousConfig={{
          safe_mode: {
            freeze_updates: isFrozen,
            prefer_cache: data?.config.safe_mode.prefer_cache ?? true,
          },
        }}
        newConfig={{
          safe_mode: {
            freeze_updates: !isFrozen,
            prefer_cache: data?.config.safe_mode.prefer_cache ?? true,
          },
        }}
        onConfirm={handleConfirm}
        isSubmitting={isSubmitting}
        impactMetrics={undefined} // TODO: Add impact metrics
      />
    </>
  );
}
