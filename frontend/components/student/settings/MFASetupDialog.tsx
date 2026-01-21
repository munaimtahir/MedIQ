"use client";

import { useState } from "react";
import Image from "next/image";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Shield, Smartphone, AlertCircle, Copy, Download, Check } from "lucide-react";
import { setupMFA, verifyMFASetup, completeMFASetup } from "@/lib/api/mfaApi";
import { notify } from "@/lib/notify";

interface MFASetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

type Step = "intro" | "scan" | "backup";

export function MFASetupDialog({ open, onOpenChange, onSuccess }: MFASetupDialogProps) {
  const [step, setStep] = useState<Step>("intro");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Setup data
  const [qrCodeUri, setQrCodeUri] = useState<string>("");
  const [secret, setSecret] = useState<string>("");
  const [backupCodes, setBackupCodes] = useState<string[]>([]);

  // User input
  const [totpCode, setTotpCode] = useState("");
  const [verifiedCode, setVerifiedCode] = useState("");
  const [savedCodesConfirmed, setSavedCodesConfirmed] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedCodes, setCopiedCodes] = useState(false);

  const handleClose = () => {
    if (!loading) {
      setStep("intro");
      setTotpCode("");
      setVerifiedCode("");
      setSavedCodesConfirmed(false);
      setError(null);
      setCopiedSecret(false);
      setCopiedCodes(false);
      onOpenChange(false);
    }
  };

  const handleContinue = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await setupMFA();
      setQrCodeUri(response.qr_code_data_uri);
      setSecret(response.secret);
      setBackupCodes(response.backup_codes);
      setStep("scan");
    } catch (err: unknown) {
      setError(err?.message || "Failed to start MFA setup");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!totpCode || totpCode.length !== 6) {
      setError("Please enter a 6-digit code");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await verifyMFASetup(totpCode);
      if (response.valid) {
        setVerifiedCode(totpCode);
        setStep("backup");
      } else {
        setError("Invalid code. Please try again.");
        setTotpCode("");
      }
    } catch (err: unknown) {
      setError(err?.message || "Failed to verify code");
      setTotpCode("");
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!savedCodesConfirmed) {
      setError("Please confirm you've saved your backup codes");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await completeMFASetup(verifiedCode);
      notify.success("Two-factor authentication enabled", "Your account is now more secure");
      handleClose();
      onSuccess();
    } catch (err: unknown) {
      setError(err?.message || "Failed to complete MFA setup");
    } finally {
      setLoading(false);
    }
  };

  const copySecret = () => {
    navigator.clipboard.writeText(secret);
    setCopiedSecret(true);
    notify.success("Copied", "Secret key copied to clipboard");
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  const copyAllCodes = () => {
    const codesText = backupCodes.join("\n");
    navigator.clipboard.writeText(codesText);
    setCopiedCodes(true);
    notify.success("Copied", "Backup codes copied to clipboard");
    setTimeout(() => setCopiedCodes(false), 2000);
  };

  const downloadCodes = () => {
    const codesText = `Two-Factor Authentication Backup Codes\n\nGenerated: ${new Date().toLocaleString()}\n\n${backupCodes.join("\n")}\n\nKeep these codes in a safe place. Each code can only be used once.`;
    const blob = new Blob([codesText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `backup-codes-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    notify.success("Downloaded", "Backup codes saved to file");
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        {step === "intro" && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Enable Two-Factor Authentication
              </DialogTitle>
              <DialogDescription>Add an extra layer of security to your account</DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <p className="text-sm">
                Two-factor authentication (2FA) helps protect your account by requiring a second
                verification step when you log in.
              </p>

              <div className="space-y-2">
                <h4 className="text-sm font-semibold">What you'll need:</h4>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <Smartphone className="mt-0.5 h-4 w-4 flex-shrink-0" />
                    <span>
                      An authenticator app like Google Authenticator, Authy, 1Password, or Microsoft
                      Authenticator
                    </span>
                  </li>
                </ul>
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
              <Button onClick={handleContinue} disabled={loading}>
                {loading ? "Setting up..." : "Continue"}
              </Button>
            </DialogFooter>
          </>
        )}

        {step === "scan" && (
          <>
            <DialogHeader>
              <DialogTitle>Scan QR Code</DialogTitle>
              <DialogDescription>Use your authenticator app to scan this code</DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* QR Code */}
              <div className="flex justify-center rounded-lg bg-white p-4">
                {qrCodeUri && (
                  <Image
                    src={qrCodeUri}
                    alt="MFA QR Code"
                    width={192}
                    height={192}
                    className="h-48 w-48"
                    unoptimized
                  />
                )}
              </div>

              {/* Manual entry option */}
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">
                  Or enter this code manually:
                </Label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 rounded bg-muted px-3 py-2 font-mono text-sm">
                    {secret}
                  </code>
                  <Button variant="outline" size="icon" onClick={copySecret} title="Copy secret">
                    {copiedSecret ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              {/* Verification input */}
              <div className="space-y-2">
                <Label htmlFor="totp-code">Enter the 6-digit code from your app</Label>
                <Input
                  id="totp-code"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder="000000"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                  className="text-center text-lg tracking-widest"
                  autoFocus
                />
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
              <Button onClick={handleVerify} disabled={loading || totpCode.length !== 6}>
                {loading ? "Verifying..." : "Verify"}
              </Button>
            </DialogFooter>
          </>
        )}

        {step === "backup" && (
          <>
            <DialogHeader>
              <DialogTitle>Save Your Backup Codes</DialogTitle>
              <DialogDescription>
                You'll need these codes if you lose access to your authenticator app
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>Important:</strong> Save these codes in a safe place. Each code can only
                  be used once.
                </AlertDescription>
              </Alert>

              {/* Backup codes grid */}
              <div className="grid grid-cols-2 gap-2 rounded-lg bg-muted p-4">
                {backupCodes.map((code, index) => (
                  <code key={index} className="font-mono text-sm">
                    {code}
                  </code>
                ))}
              </div>

              {/* Action buttons */}
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={copyAllCodes} className="flex-1">
                  {copiedCodes ? (
                    <>
                      <Check className="mr-2 h-4 w-4" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy All
                    </>
                  )}
                </Button>
                <Button variant="outline" size="sm" onClick={downloadCodes} className="flex-1">
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
              </div>

              {/* Confirmation checkbox */}
              <div className="flex items-start space-x-2">
                <Checkbox
                  id="saved-codes"
                  checked={savedCodesConfirmed}
                  onCheckedChange={(checked) => setSavedCodesConfirmed(checked as boolean)}
                />
                <Label
                  htmlFor="saved-codes"
                  className="text-sm font-normal leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  I've saved my backup codes in a safe place
                </Label>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </div>

            <DialogFooter>
              <Button
                onClick={handleComplete}
                disabled={loading || !savedCodesConfirmed}
                className="w-full"
              >
                {loading ? "Completing..." : "Complete Setup"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
