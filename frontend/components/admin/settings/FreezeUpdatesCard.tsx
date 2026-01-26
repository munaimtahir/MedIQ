"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useFreezeUpdates } from "@/lib/admin/settings/hooks";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, Clock, User } from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";

export function FreezeUpdatesCard() {
  const { state, loading, error, refetch, toggleFreezeUpdates } = useFreezeUpdates();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [pendingEnabled, setPendingEnabled] = useState(false);
  const [confirmationPhrase, setConfirmationPhrase] = useState("");
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const expectedPhrase = pendingEnabled ? "ENABLE FREEZE UPDATES" : "DISABLE FREEZE UPDATES";
  const isPhraseValid = confirmationPhrase.trim() === expectedPhrase;
  const isReasonValid = reason.trim().length >= 10;
  const canSubmit = isPhraseValid && isReasonValid && !isSubmitting;

  const handleToggleClick = (newEnabled: boolean) => {
    setPendingEnabled(newEnabled);
    setConfirmationPhrase("");
    setReason("");
    setIsDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;

    setIsSubmitting(true);
    try {
      await toggleFreezeUpdates(pendingEnabled, reason.trim(), confirmationPhrase.trim());
      setIsDialogOpen(false);
      setConfirmationPhrase("");
      setReason("");
    } catch {
      // Error already handled in hook
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="mt-2 h-4 w-64" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Freeze Updates</CardTitle>
          <CardDescription>Runtime flag for blocking learning state mutations</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertDescription>Failed to load freeze-updates state: {error.message}</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!state) {
    return null;
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Freeze Updates</CardTitle>
              <CardDescription>
                When enabled, blocks learning state writes (mastery, revision, etc.); decision reads allowed
              </CardDescription>
            </div>
            <Badge variant={state.enabled ? "destructive" : "secondary"}>
              {state.enabled ? "ACTIVE" : "INACTIVE"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="freeze-updates-toggle">Freeze Updates</Label>
              <p className="text-sm text-muted-foreground">
                Blocks mastery updates, queue writes, and other state mutations. Use during audits or safe-mode.
              </p>
            </div>
            <Button
              id="freeze-updates-toggle"
              variant={state.enabled ? "destructive" : "outline"}
              onClick={() => handleToggleClick(!state.enabled)}
              disabled={loading}
            >
              {state.enabled ? "Disable" : "Enable"}
            </Button>
          </div>

          {state.enabled && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Freeze updates is active. Learning state mutations are blocked (423). Session create/answer/submit
                will fail while enabled.
              </AlertDescription>
            </Alert>
          )}

          {state.updated_at && (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="h-4 w-4" />
                <span>
                  Last updated: {formatDistanceToNow(new Date(state.updated_at), { addSuffix: true })}
                </span>
              </div>
              {state.updated_by && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <User className="h-4 w-4" />
                  <span>Updated by: {state.updated_by.email}</span>
                </div>
              )}
              {state.reason && (
                <div className="text-muted-foreground">
                  <span className="font-medium">Reason:</span> {state.reason}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {pendingEnabled ? "Enable Freeze Updates" : "Disable Freeze Updates"}
            </DialogTitle>
            <DialogDescription>
              {pendingEnabled ? (
                <>
                  Enabling freeze updates will block all learning state mutations (mastery, revision queue,
                  etc.). Session answer and submit will return 423. Use for audits or safe-mode.
                </>
              ) : (
                <>
                  Disabling freeze updates will restore learning state writes. Ensure audits or safe-mode
                  are complete.
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                This action requires a typed confirmation phrase and a reason for audit purposes.
              </AlertDescription>
            </Alert>

            <div className="space-y-2">
              <Label htmlFor="freeze-confirmation-phrase">
                Confirmation Phrase <span className="text-destructive">*</span>
              </Label>
              <Input
                id="freeze-confirmation-phrase"
                placeholder={expectedPhrase}
                value={confirmationPhrase}
                onChange={(e) => setConfirmationPhrase(e.target.value)}
                className={confirmationPhrase && !isPhraseValid ? "border-destructive" : ""}
              />
              <p className="text-xs text-muted-foreground">
                Type exactly: <code className="font-mono">{expectedPhrase}</code>
              </p>
              {confirmationPhrase && !isPhraseValid && (
                <p className="text-xs text-destructive">Phrase does not match</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="freeze-reason">
                Reason <span className="text-destructive">*</span>
              </Label>
              <textarea
                id="freeze-reason"
                placeholder="Explain why you are toggling freeze updates (minimum 10 characters)"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
                className={`w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
                  reason && !isReasonValid ? "border-destructive" : ""
                }`}
              />
              <p className="text-xs text-muted-foreground">
                Minimum 10 characters. This will be recorded in the audit log.
              </p>
              {reason && !isReasonValid && (
                <p className="text-xs text-destructive">Reason must be at least 10 characters</p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={!canSubmit}>
              {isSubmitting
                ? "Processing..."
                : pendingEnabled
                  ? "Enable Freeze Updates"
                  : "Disable Freeze Updates"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
