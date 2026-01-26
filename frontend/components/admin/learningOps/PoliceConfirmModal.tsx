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
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2, XCircle, Info } from "lucide-react";

interface PoliceConfirmModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actionTitle: string;
  requiredPhrase: string;
  reason: string;
  onReasonChange: (reason: string) => void;
  jsonDiff?: {
    previous: Record<string, unknown>;
    current: Record<string, unknown>;
  };
  onConfirm: () => void | Promise<void>;
  isSubmitting?: boolean;
  variant?: "default" | "destructive";
}

export function PoliceConfirmModal({
  open,
  onOpenChange,
  actionTitle,
  requiredPhrase,
  reason,
  onReasonChange,
  jsonDiff,
  onConfirm,
  isSubmitting = false,
  variant = "default",
}: PoliceConfirmModalProps) {
  const [confirmationPhrase, setConfirmationPhrase] = useState("");

  const phraseMatches = confirmationPhrase.trim().toUpperCase() === requiredPhrase.toUpperCase();
  const canConfirm = phraseMatches && reason.trim().length >= 10 && !isSubmitting;

  const handleConfirm = async () => {
    if (!canConfirm) return;
    await onConfirm();
    setConfirmationPhrase("");
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setConfirmationPhrase("");
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Confirm {actionTitle}</DialogTitle>
          <DialogDescription>
            Review the changes and confirm by typing the required phrase.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Reason */}
          <div className="space-y-2">
            <Label htmlFor="reason">
              Reason <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="reason"
              placeholder="Explain why you are performing this action (minimum 10 characters)..."
              value={reason}
              onChange={(e) => onReasonChange(e.target.value)}
              rows={3}
              disabled={isSubmitting}
              className={reason.length > 0 && reason.length < 10 ? "border-destructive" : ""}
            />
            {reason.length > 0 && reason.length < 10 && (
              <p className="text-sm text-destructive">Reason must be at least 10 characters</p>
            )}
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

          {/* JSON Diff */}
          {jsonDiff && (
            <div className="space-y-4">
              <div>
                <Label className="text-sm font-semibold">Previous Configuration</Label>
                <div className="mt-2 h-32 rounded-md border bg-muted p-3 overflow-auto">
                  <pre className="text-xs">{JSON.stringify(jsonDiff.previous, null, 2)}</pre>
                </div>
              </div>

              <div>
                <Label className="text-sm font-semibold">New Configuration</Label>
                <div className="mt-2 h-32 rounded-md border bg-muted p-3 overflow-auto">
                  <pre className="text-xs">{JSON.stringify(jsonDiff.current, null, 2)}</pre>
                </div>
              </div>
            </div>
          )}

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
            variant={variant}
          >
            {isSubmitting ? "Processing..." : "Confirm & Apply"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
