"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Info, AlertTriangle, Database, Snowflake } from "lucide-react";
import { PoliceConfirmModal } from "@/components/admin/learningOps/PoliceConfirmModal";
import type { WarehouseRuntimeStatus } from "@/lib/api/adminWarehouse";
import { formatDistanceToNow } from "date-fns";

interface WarehouseStatusCardProps {
  data: WarehouseRuntimeStatus | null;
  loading: boolean;
  onSwitchMode: (mode: "disabled" | "shadow" | "active", reason: string, phrase: string) => Promise<void>;
}

const WAREHOUSE_PHRASES = {
  disabled: "SWITCH WAREHOUSE TO DISABLED",
  shadow: "SWITCH WAREHOUSE TO SHADOW",
  active: "SWITCH WAREHOUSE TO ACTIVE",
};

export function WarehouseStatusCard({ data, loading, onSwitchMode }: WarehouseStatusCardProps) {
  const [switchMode, setSwitchMode] = useState<"disabled" | "shadow" | "active" | null>(null);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSwitch = async () => {
    if (!switchMode) return;
    setIsSubmitting(true);
    try {
      await onSwitchMode(switchMode, reason, WAREHOUSE_PHRASES[switchMode]);
      setSwitchMode(null);
      setReason("");
    } catch (error) {
      // Error handled by parent
    } finally {
      setIsSubmitting(false);
    }
  };

  const requestedMode = data?.requested_mode || "disabled";
  const effectiveMode = data?.effective_mode || "disabled";
  const isFrozen = data?.warehouse_freeze || false;
  const readiness = data?.readiness;
  const isReady = readiness?.ready || false;

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Warehouse Status
          </CardTitle>
          <CardDescription>Snowflake export pipeline control</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Current Status */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Requested mode:</span>
              <Badge
                variant={
                  data?.requested_mode === "active"
                    ? "default"
                    : data?.requested_mode === "shadow"
                      ? "secondary"
                      : "outline"
                }
              >
                {data?.requested_mode || "disabled"}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Effective mode:</span>
              <Badge
                variant={
                  data?.effective_mode === "active"
                    ? "default"
                    : data?.effective_mode === "shadow"
                      ? "secondary"
                      : "outline"
                }
              >
                {data?.effective_mode || "disabled"}
              </Badge>
            </div>
            {data?.readiness && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Readiness:</span>
                <Badge variant={data.readiness.ready ? "default" : "destructive"}>
                  {data.readiness.ready ? "READY" : "NOT READY"}
                </Badge>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Freeze status:</span>
              <Badge variant={isFrozen ? "destructive" : "default"}>
                {isFrozen ? "Frozen" : "Active"}
              </Badge>
            </div>
          </div>

          {/* Blocking Reasons */}
          {data?.readiness && !data.readiness.ready && data.readiness.blocking_reasons.length > 0 && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-1">
                  <div className="font-medium">Blocking reasons:</div>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    {data.readiness.blocking_reasons.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Feature Flag Warning */}
          {data?.readiness?.checks?.feature_allow_connect?.ok === false && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                Snowflake connectivity disabled by feature flag (FEATURE_ALLOW_SNOWFLAKE_CONNECT=false).
                Enable this flag to allow Snowflake connections.
              </AlertDescription>
            </Alert>
          )}

          {/* Warning for Active Mode */}
          {currentMode === "active" && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Active mode does not load Snowflake yet; files-only until loader is built.
              </AlertDescription>
            </Alert>
          )}

          {/* Mode Switch Buttons */}
          <div className="space-y-2">
            <div className="flex gap-2 flex-wrap">
              <Button
                variant={currentMode === "disabled" ? "default" : "outline"}
                size="sm"
                onClick={() => setSwitchMode("disabled")}
                disabled={loading || isFrozen}
              >
                Switch to Disabled
              </Button>
              <Button
                variant={currentMode === "shadow" ? "default" : "outline"}
                size="sm"
                onClick={() => setSwitchMode("shadow")}
                disabled={loading || isFrozen}
              >
                Switch to Shadow
              </Button>
              <Button
                variant={currentMode === "active" ? "default" : "outline"}
                size="sm"
                onClick={() => setSwitchMode("active")}
                disabled={loading || isFrozen || !isReady}
                title={
                  !isReady && data?.readiness?.blocking_reasons
                    ? `Cannot switch to active: ${data.readiness.blocking_reasons.join("; ")}`
                    : undefined
                }
              >
                Switch to Active
              </Button>
            </div>
            {isFrozen && (
              <p className="text-xs text-muted-foreground">
                Warehouse is frozen. Unfreeze to change mode.
              </p>
            )}
          </div>

          {/* Last Export Runs Summary */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Recent Export Runs</span>
              <Badge variant="outline">{data?.last_export_runs.length || 0} runs</Badge>
            </div>
            {data?.last_export_runs && data.last_export_runs.length > 0 ? (
              <div className="space-y-1 text-xs">
                {data.last_export_runs.slice(0, 5).map((run) => (
                  <div key={run.run_id} className="flex items-center justify-between">
                    <span className="text-muted-foreground">
                      {run.dataset} ({run.run_type})
                    </span>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          run.status === "shadow_done_files_only"
                            ? "default"
                            : run.status === "failed"
                              ? "destructive"
                              : "outline"
                        }
                        className="text-xs"
                      >
                        {run.status}
                      </Badge>
                      {run.created_at && (
                        <span className="text-muted-foreground">
                          {formatDistanceToNow(new Date(run.created_at))} ago
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No export runs yet</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Switch Mode Confirmation Modal */}
      {switchMode && (
        <PoliceConfirmModal
          open={true}
          onOpenChange={(open) => !open && setSwitchMode(null)}
          actionTitle={`Switch Warehouse to ${switchMode.toUpperCase()}`}
          requiredPhrase={WAREHOUSE_PHRASES[switchMode]}
          reason={reason}
          onReasonChange={setReason}
          onConfirm={handleSwitch}
          isSubmitting={isSubmitting}
          variant={switchMode === "disabled" ? "destructive" : "default"}
        />
      )}
    </>
  );
}
