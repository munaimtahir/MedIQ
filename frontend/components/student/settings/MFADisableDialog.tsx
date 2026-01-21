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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertTriangle, AlertCircle } from "lucide-react";
import { disableMFA } from "@/lib/api/mfaApi";
import { notify } from "@/lib/notify";

interface MFADisableDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function MFADisableDialog({ open, onOpenChange, onSuccess }: MFADisableDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totpCode, setTotpCode] = useState("");

  const handleClose = () => {
    if (!loading) {
      setTotpCode("");
      setError(null);
      onOpenChange(false);
    }
  };

  const handleDisable = async () => {
    if (!totpCode || totpCode.length !== 6) {
      setError("Please enter a 6-digit code");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await disableMFA(totpCode);
      notify.success(
        "Two-factor authentication disabled",
        "Your account security settings have been updated",
      );
      handleClose();
      onSuccess();
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to disable MFA. Please check your code and try again."
      );
      setTotpCode("");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && totpCode.length === 6 && !loading) {
      handleDisable();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            Disable Two-Factor Authentication
          </DialogTitle>
          <DialogDescription>
            This will remove two-factor authentication from your account
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>Warning:</strong> Disabling 2FA will make your account less secure. Anyone
              with your password will be able to access your account.
            </AlertDescription>
          </Alert>

          <div className="space-y-2">
            <Label htmlFor="disable-code">Enter your current 6-digit authentication code</Label>
            <Input
              id="disable-code"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              placeholder="000000"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
              onKeyPress={handleKeyPress}
              className="text-center text-lg tracking-widest"
              autoFocus
            />
            <p className="text-xs text-muted-foreground">Or enter one of your backup codes</p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDisable}
            disabled={loading || totpCode.length !== 6}
          >
            {loading ? "Disabling..." : "Disable 2FA"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
