"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Shield, ShieldCheck, ShieldAlert } from "lucide-react";
import { MFASetupDialog } from "./MFASetupDialog";
import { MFADisableDialog } from "./MFADisableDialog";
import { getMFAStatus } from "@/lib/api/mfaApi";
import { format } from "@/lib/dateUtils";

export function MFACard() {
  const [loading, setLoading] = useState(true);
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [mfaEnabledAt, setMfaEnabledAt] = useState<string | undefined>();
  const [setupDialogOpen, setSetupDialogOpen] = useState(false);
  const [disableDialogOpen, setDisableDialogOpen] = useState(false);

  const loadMFAStatus = async () => {
    setLoading(true);
    try {
      const status = await getMFAStatus();
      setMfaEnabled(status.enabled);
      setMfaEnabledAt(status.enabled_at);
    } catch (error) {
      console.error("Failed to load MFA status:", error);
      // Default to disabled if we can't check
      setMfaEnabled(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMFAStatus();
  }, []);

  const handleSetupSuccess = () => {
    loadMFAStatus();
  };

  const handleDisableSuccess = () => {
    loadMFAStatus();
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-96" />
            </div>
            <Skeleton className="h-10 w-32" />
          </div>
        </CardHeader>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Two-Factor Authentication
                </CardTitle>
                {mfaEnabled ? (
                  <Badge variant="default" className="bg-green-600">
                    <ShieldCheck className="mr-1 h-3 w-3" />
                    Enabled
                  </Badge>
                ) : (
                  <Badge variant="secondary">
                    <ShieldAlert className="mr-1 h-3 w-3" />
                    Not Enabled
                  </Badge>
                )}
              </div>
              <CardDescription>
                {mfaEnabled
                  ? "Your account is protected with two-factor authentication"
                  : "Add an extra layer of security to your account"}
              </CardDescription>
            </div>
            <div>
              {mfaEnabled ? (
                <Button variant="outline" onClick={() => setDisableDialogOpen(true)}>
                  Disable 2FA
                </Button>
              ) : (
                <Button onClick={() => setSetupDialogOpen(true)}>Enable 2FA</Button>
              )}
            </div>
          </div>
        </CardHeader>

        {mfaEnabled && mfaEnabledAt && (
          <CardContent>
            <div className="text-sm text-muted-foreground">
              Enabled on {format(new Date(mfaEnabledAt), "MMMM d, yyyy 'at' h:mm a")}
            </div>
          </CardContent>
        )}

        {mfaEnabled && (
          <CardContent className="pt-0">
            <div className="rounded-lg border border-muted bg-muted/50 p-4">
              <p className="text-sm text-muted-foreground">
                <strong>Important:</strong> If you lose access to your authenticator app, you'll
                need your backup codes to log in. Make sure you've saved them in a safe place.
              </p>
            </div>
          </CardContent>
        )}
      </Card>

      <MFASetupDialog
        open={setupDialogOpen}
        onOpenChange={setSetupDialogOpen}
        onSuccess={handleSetupSuccess}
      />

      <MFADisableDialog
        open={disableDialogOpen}
        onOpenChange={setDisableDialogOpen}
        onSuccess={handleDisableSuccess}
      />
    </>
  );
}
